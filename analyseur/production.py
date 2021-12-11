""" 
    Ce module permet de réunir les outils de production des MAA (autos ou manuels), c'est à dire le PDF, les corps de mail, les messages brutes...
"""
from datetime import datetime, time, timedelta
import os, json
from pathlib import Path
import tempfile
import asyncio

from django.core.files.temp import NamedTemporaryFile
from django.core.files import File
from django.urls import reverse

from analyseur.models import EnvoiMAA

from configurateur.models import AutorisedMAAs

def definie_numero_maa(oaci, date):
    """ Permet de définir le numéro du nouveau MAA 
        Ce numéro est incrémenté de 1 à chaque MAA au cours d'une journée. Compteur remis à zéro à 00TU. 
        Il n'est pas dépendant du type de maa. 1 MAA TS + 1 MAA VENT => 3 pour le nouveau
    """
    last = EnvoiMAA.objects.last_MAA(oaci, date)
    if last is None:
        return 1
    return last.numero + 1

def define_mail_content():
    """ Fonction pour formater le contenu d'un mail """
    #TODO: finir le corps du mail
    return "Corps du mail"

def define_fcst(provider, production, debut, configmaa):
    """ Permet de définir si le MAA auto doit être considéré commme un MAA FCST (prévu) ou OBS. 
        Cela se détermine en fonction de l'heure de début et de l'heure du TAF associé si paramètre issu du TAF

        cf spec DP-11 :
        Lors d'une analyse à l'heure ronde H plus quelques minutes, si un test déclenchant est repéré à l'heure H 
        et que le TAF ayant donné lieu à ce test a été émis après l'heure H (comparaison stricte, pas égale), 
        on suppose qu'on est en présence d'un TAF amendé. Le MAA prend alors le qualificatif de MAA observé avec la mention "OBS"

        A ce stade, debut correspond effectivement à l'heure du premier test déclenchant, donc peut être l'heure ronde précédent l'heure actu.
    """
    fcst = "FCST"

    if debut < production:
        # Le premier test déclenchant est déjà passé, il faut regarder d'où vient l'info. 
        declenche, origine = provider.questionne_cdp(configmaa.station.oaci, debut, configmaa.type_maa, configmaa.seuil)
        if origine is not None:
            # C'est bien le TAF qui est à l'origine du déclenchement
            if origine > debut:
                fcst = "OBS"
    return fcst

def decoupe_supplement(trunk):
    """ permet de morcelé le bloc supplément en tronçons de 70 caractères au plus 
        retourne le nouveau trunk et la chaîne restante (None si plus rien)
    """ 
    nouveau= trunk.strip()
    restant = None
    if len(trunk) > 70:
        pos = trunk.find('\n')
        if pos >= 0 and pos <=70:
            return trunk[:pos].strip(), trunk[pos+1:].strip()  

        pos = trunk.rfind(" ", 0, 70)
        if pos == -1: # Pas d'espace, on coupe arbitrairement
            nouveau = trunk[:70]
            restant = trunk[70:].strip()
        else:
            nouveau = trunk[:pos]
            restant = trunk[pos:].strip()
        if len(restant.strip()) == 0:
            restant = None
    return nouveau.strip(), restant

def adapte_supplement(supplement):
    """ Pour être sûr de ne pas avoir de problème avec le format TAC et Transmet, les suppléments de prévision
        sont coupés et mis sur plusieurs lignes pour que chaque ligne ne dépasse pas 70 caractères 
        Au max, on tolère 3 lignes au plus. Si des caractère \n sont déjà dans la chaîne, il génère eux-même une ligne
        Tous les caractères sont capitalisés. 

        Le retour est un chaîne de cractères avec les \n au bon endroit.    
    """
    reponse = []
    supplement = supplement.upper()
    ligne = 0
    while len(reponse) < 3 and supplement is not None:
        nouveau, supplement = decoupe_supplement(supplement)
        reponse.append(nouveau)
    return "\n".join(reponse)

def create_raw_message(configmaa, numero, date_debut, date_fin, fcst, supplement=None, valeur_neige=None):
    """ Permet de synthétiser un message MAA brute qui sera envoyé à Transmet (entre autre)
        Pour les MAA de neige, on peut ajouter une valeur extrême.
        Un complément de prévision (via les MAA manuel) peut être également ajouté. (TODO: voir à quel endroit on le formate)
    """
    # Entete du message
    message = "{} AD WRNG {} VALID {}/{}\n".format( configmaa.station.oaci, numero, \
                                                    datetime.strftime(date_debut,"%d%H%M"), \
                                                    datetime.strftime(date_fin,"%d%H%M"))

    # Description du phénomène
    #TODO: on doit pouvoir définir ces création de message dans les objets AutorisedMAA pour plus d'encapsulation
    if configmaa.type_maa in ['VENT', 'VENT_MOY']:
        #TODO: prendre en charge les maa de vent moy
        unit_kmh = configmaa.station.wind_unit == 'kmh'
        unit = 'KT'
        value = configmaa.seuil
        type_vent = "WSPD MAX"
        if configmaa.type_maa == 'VENT_MOY':
            type_vent = "AVERAGE WSPD"
        if unit_kmh:
            unit = 'KM/H'
            value = round ( (value * 1.852), 0 )
        message = message + "SFC {} >= {} {}".format(type_vent, value, unit)
    elif configmaa.type_maa == "TMIN":
        message = message + "TEMPE <= {} DEG C".format(configmaa.seuil)
    elif configmaa.type_maa == "TMAX":
        message = message + "TEMPE >= {} DEG C".format(configmaa.seuil)
    elif configmaa.type_maa in ['RR1', 'RR3', 'RR6', 'RR12', 'RR24']:
        cumul = "MM/H"
        if configmaa.type_maa == 'RR3': cumul = "MM/3H"
        elif configmaa.type_maa == 'RR6': cumul = "MM/6H"
        elif configmaa.type_maa == 'RR12': cumul = "MM/12H"
        elif configmaa.type_maa == 'RR24': cumul = "MM/24H"
        message = message + "HVY RA >= {} {}".format(configmaa.seuil, cumul)
    elif configmaa.type_maa == "SN":
        message = message + configmaa.type_maa
        if valeur_neige is not None:
            neige = float(valeur_neige)
            if neige < 1: message = message + " [<1 CM]"
            elif neige < 3: message = message + " [1 AND 3 CM]"
            elif neige < 6: message = message + " [3 AND 6 CM]"
            elif neige < 10: message = message + " [6 AND 10 CM]"
            elif neige < 15: message = message + " [10 AND 15 CM]"
            else : message = message + " [>15 CM]"
    elif configmaa.type_maa == "FWID":
        message = message + "FROST WITH NATURAL ICE DEPOSIT"
    elif configmaa.type_maa == "FWOID":
        message = message + "FROST WITHOUT NATURAL ICE DEPOSIT"
    elif configmaa.type_maa == "TOXCHEM":
        message = message + "TOX CHEM"
    elif configmaa.type_maa in ["ICE_DEPOSIT", "VEHICLE_RIME"]:
        message = message + configmaa.type_maa.replace('_', ' ') 
    else:
        message = message + configmaa.type_maa
    message = message + " {}".format(fcst)

    # Ajout d'un supplément (quand manuel)
    if supplement is not None:
        message = message + "\n{}".format(adapte_supplement(supplement))

    # Indication de fermeture du service
    if configmaa.station.ouverture != time(0,0) or configmaa.station.fermeture != time(23,59):
        message = message + "\nNO WARNING BETWEEN {} AND {}".format(  time.strftime(configmaa.station.fermeture, "%H:%M"), \
                                                                    time.strftime(configmaa.station.ouverture, "%H:%M")) 

    message = message + "="
    return message

def create_raw_message_cnl(numero, maa_precedent):
    """ Permet de synthétiser un message MAA brute qui sera envoyé à Transmet (entre autre)
        Exemple: LFOT AD WRNG 1 VALID 221000/221600 CNL AD WRNG 1 221000/221600 =
    """
    # Entete du message
    message = "{} AD WRNG {} VALID {}/{}\n".format( maa_precedent.configmaa.station.oaci, numero, \
                                            datetime.strftime(maa_precedent.date_debut,"%d%H%M"), \
                                            datetime.strftime(maa_precedent.date_fin,"%d%H%M"))

    # Description du phénomène
    message = message + "CNL AD WRNG {} {}/{}\n".format(  maa_precedent.numero, \
                                                                datetime.strftime(maa_precedent.date_debut,"%d%H%M"), \
                                                                datetime.strftime(maa_precedent.date_fin,"%d%H%M"))

    #TODO: dans le code de Stéphane, il y a un $raison inséré ici => voir ce que représente ce raison

    # Indication de fermeture du service
    if maa_precedent.configmaa.station.ouverture != time(0,0) or maa_precedent.configmaa.station.fermeture != time(23,59):
        message = message + "NO WARNING BETWEEN {} AND {}\n".format(  time.strftime(maa_precedent.configmaa.station.fermeture, "%H:%M"), \
                                                                    time.strftime(maa_precedent.configmaa.station.ouverture, "%H:%M")) 

    message = message + "="
    return message

def get_data_atmo(provider, envoi):
    """ Fonction permettant d'extraire et formater les données utilisables dans le créateur de PDF
        pour l'ajout du tableau de fin de page

        Pour le vent, pour chaque échéance, il faut : 
            (échéance, (vent mean, vent max, direction)) # vent max peut être nul
            Si données pas dispos, le tuple peut être None

        Pour les température, pour chaque échéance, il faut :
            (échéance, t) # vent max peut être nul
            Si données pas dispo t vaut None
    """
    type_maa = envoi.configmaa.type_maa
    heure_production = envoi.date_envoi
    oaci = envoi.configmaa.station.oaci
    echeances = [heure_production + timedelta(hours=i) for i in range(0,24)]
    data = []
    if type_maa in ['VENT_MOY', 'VENT']:
        # On récupère et formate des données de vent.
        for echeance in echeances:
            data.append(echeance, provider.get_vent(oaci, echeance))
        
    if type_maa in ['TMIN', 'TMAX']:
        # On récupère et formate des données de température
        for echeance in echeances:
            data.append(echeance, provider.get_tempe(oaci, echeance))

def create_description(configmaa, fcst):
    """ Permet de générer le texte qui va être mis dans le PDF pour décrire le phénomène """
    # La partie spécifique aux différents MAA doit pouvoir se mettre dans l'objet AutorisedMAA
    typemaa = configmaa.type_maa
    maa = AutorisedMAAs.get_instance(typemaa)
    at = None
    if maa is None:
        return ''
    
    if typemaa in ['VENT_MOY', 'VENT']:
        unite, seuil = configmaa.get_seuil_unit()
        return maa.get_description(fcst, int(seuil), at, force_unit=unite)
    
    else:
        return maa.get_description(fcst, None, at)

def create_description_cnl(maa_precedent):
        """ Détermine le message qui annonce quel MAA a été annulé 
            Ex de message : Annulation du maa numéro 1 valable du 22 à 10:00 au 22 à 16:00 UTC.
        """
        debut = datetime.strftime(maa_precedent.date_debut, "%d à %H:%M")
        fin = datetime.strftime(maa_precedent.date_fin, "%d à %H:%M")
        label = "Annulation du MAA numéro {} valable du {} au {} UTC.".format(maa_precedent.numero, debut, fin)
        return label

def create_data_vent(provider, configmaa, heure_production):
    """ Permet de collecter les données de vent nécessaires pour la création du graphique du PDF
        Evidemment, cela n'a d'intérêt que pour les MAA de type vent. Sinon retourne juste ''
    """
    if configmaa.type_maa not in ['VENT', 'VENT_MOY']:
        return ''

    data= []
    # (echeance, (ff,fx,dd))
    oaci = configmaa.station.oaci
    for i in range(0, 24):
        echeance = heure_production + timedelta(hours=i)
        vents = provider.get_vent(oaci, echeance)
        data.append( (datetime.strftime(echeance,"%Y-%m-%d %H:%M:%S"), vents )  )
    data= json.dumps(data)
    return data

def create_data_tempe(provider, configmaa, heure_production):
    """ Permet de collecter les données de température nécessaires pour la création du graphique du PDF
        Evidemment, cela n'a d'intérêt que pour les MAA de type Tempé. Sinon retourne juste ''
    """
    if configmaa.type_maa not in ['TMAX', 'TMIN']:
        return ''
        
    data= []
    # (echeance, (ff,fx,dd))
    oaci = configmaa.station.oaci
    for i in range(0, 24):
        echeance = heure_production + timedelta(hours=i)
        tempe = provider.get_tempe(oaci, echeance)
        data.append( (datetime.strftime(echeance,"%Y-%m-%d %H:%M:%S"), tempe) )
    data= json.dumps(data)
    return data

#TODO: les 4 fonction ci-dessous mériteraient d'être refactorisées
def create_maa_auto(log, provider, configmaa, heure_production, date_debut, date_fin, num_groupe=1, total_groupe=1):
    """ Fonction prenant en charge la création d'un MAA auto à partir des données transmis par l'analyse 15mn 

    Comme c'est une production automatique, on va générer directement le PDF est indiquer un status = ti_send.
    """
    oaci = configmaa.station.oaci

    # Récupère le context TAF
    context_TAF = provider.get_context_TAF(oaci)
    context_CDP = provider.get_context_CDP(oaci)
    
    # Détermine le numéro du MAA.
    numero = definie_numero_maa(oaci, heure_production)

    # Rédige le message brute
    fcst = define_fcst(provider, heure_production, date_debut, configmaa) 
    
    # Formate les messages
    description = create_description(configmaa, fcst)
    message_brute = create_raw_message(configmaa, numero, date_debut, date_fin, fcst)
    message_sms = "METEO-FRANCE MAA {}".format(message_brute.replace("\n", " "))
    message_mail = define_mail_content()
    
    data_vent = create_data_vent(provider, configmaa, heure_production)
    data_tempe = create_data_tempe(provider, configmaa, heure_production)

    # Crée l'instance d'envoiMAA
    try:
        envoi = EnvoiMAA.objects.create(
            configmaa = configmaa,
            date_envoi = heure_production, 
            date_debut = date_debut,
            date_fin = date_fin,
            numero = numero,
            message = message_brute,
            description_maa = description,
            fcst = fcst, #TODO: gérer les bonnes valeurs,
            status = 'to_create',
            context_TAF = context_TAF, 
            context_CDPH = context_CDP,
            context_CDPQ = "",
            log = log,
            message_mail = message_mail,
            message_sms = message_sms,
            entete_transmet = configmaa.station.entete + " " + datetime.strftime(heure_production, "%d%H%M"),
            data_vent = data_vent,
            data_tempe = data_tempe,
        )

        """pdf_temp = None
        try:
            envoi, pdf_temp = create_MAA_pdf_from_envoimaa(envoi)

        except Exception as e:
            log = log + "\n" + "{}: Impossible de créer le PDF pour le MAA.".format(datetime.utcnow())
            log = log + "\n" + "{} - {} - {} - {}".format(configmaa, date_debut, date_fin, numero)
            log = log + "\n" + str(e)            
            pdf = None
            print(log)

        envoi.status = ('to_send', 'Nouveau')
        envoi.log = log"""
        envoi.save()
        #if pdf_temp: os.remove(pdf_temp)
        
    except Exception as e:
        log = "\n" + "{}: Création de l'objet EnvoiMAA impossible.".format(datetime.utcnow())
        log = "\n" + "{} - {} - {} - {}".format(configmaa, date_debut, date_fin, numero)
        print(log)


    #import pdb
    #pdb.set_trace()

def create_cnl_maa_auto(log, provider, configmaa, heure_production, num_groupe, total_groupe, maa_annule):
    """ Suite une analyse 15mn, déclenche la production d'un cancel """
    
    oaci = configmaa.station.oaci

    # Récupère le context TAF
    context_TAF = provider.get_context_TAF(oaci)
    context_CDP = provider.get_context_CDP(oaci)
    
    # Détermine le numéro du MAA.
    numero = definie_numero_maa(oaci, heure_production)

    # Formate les messages
    description = create_description_cnl(maa_annule)
    message_brute = create_raw_message_cnl(numero, maa_annule)
    message_sms = "METEO-FRANCE MAA {}".format(message_brute.replace("\n", " "))
    
    message_mail = define_mail_content()

    # Crée l'instance d'envoiMAA
    try:
        envoi = EnvoiMAA.objects.create(
            configmaa = configmaa,
            date_envoi = heure_production, 
            date_debut = heure_production, 
            date_fin = heure_production, 
            numero = numero,
            message = message_brute,
            description_maa = description,
            fcst = False,
            status = 'to_create',
            cancel=True,
            context_TAF = context_TAF, 
            context_CDPH = context_CDP,
            context_CDPQ = "",
            log = log,
            message_mail = message_mail,
            message_sms = message_sms,
            entete_transmet = configmaa.station.entete + " " + datetime.strftime(heure_production, "%d%H%M")
        )

        """pdf_temp = None
        try:
            envoi, pdf_temp = create_MAA_pdf_from_envoimaa(envoi)
        except Exception as e:
            log = log + "\n" + "{}: Impossible de créer le PDF pour l'annulation de MAA.".format(datetime.utcnow())
            log = log + "\n" + "{} - {}".format(configmaa, numero)
            log = log + "\n" + str(e)            
            pdf = None
            print(log)

        envoi.status = 'to_send'
        envoi.log = log"""
        envoi.save()
        #if pdf_temp: os.remove(pdf_temp)
        
    except Exception as e:
        log = "\n" + "{}: Création de l'objet EnvoiMAA impossible.".format(datetime.utcnow())
        log = "\n" + "{} - {}".format(configmaa, numero)
        print(log)

def create_cnl_maa_manuel(log, configmaa, DATE_NOW, maa_en_cours):
    """ Permet de prendre en charge la demande d'annulation d'un maa 
        configmaa est le type de maa en question
        DATE_NOW est l'heure de prise en charge
        maa_en_cours est une instance EnvoiMAA qui correspond au MAA qu'on annule
    """
    oaci = configmaa.station.oaci

    # Récupère le context TAF
    context_TAF = ""
    context_CDP = ""
    
    # Détermine le numéro du MAA.
    numero = definie_numero_maa(oaci, DATE_NOW)

    # Formate les messages
    description = create_description_cnl(maa_en_cours)
    message_brute = create_raw_message_cnl(numero, maa_en_cours)
    message_sms = "METEO-FRANCE MAA {}".format(message_brute.replace("\n", " "))
    
    message_mail = define_mail_content()

    # Crée l'instance d'envoiMAA
    try:
        envoi = EnvoiMAA.objects.create(
            configmaa = configmaa,
            date_envoi = DATE_NOW, 
            date_debut = DATE_NOW, 
            date_fin = DATE_NOW, 
            numero = numero,
            message = message_brute,
            description_maa = description,
            fcst = False,
            status = 'to_create',
            context_TAF = context_TAF, 
            cancel = True,
            context_CDPH = context_CDP,
            context_CDPQ = "",
            log = log,
            message_mail = message_mail,
            message_sms = message_sms,
            entete_transmet = configmaa.station.entete + " " + datetime.strftime(DATE_NOW, "%d%H%M")
        )

        """pdf_temp = None
        try:
            envoi, pdf_temp = create_MAA_pdf_from_envoimaa(envoi)

        except Exception as e:
            log = log + "\n" + "{}: Impossible de créer le PDF pour l'annulation de MAA.".format(datetime.utcnow())
            log = log + "\n" + "{} - {}".format(configmaa, numero)
            log = log + "\n" + str(e)            
            pdf = None
            print(log)
            raise SystemError("Impossible de créer le PDF pour l'annulation du MAA suivant : {} à {}".format(configmaa, datetime.utcnow()))

        envoi.status = 'to_send'
        envoi.log = log"""
        envoi.save()
        #if pdf_temp: os.remove(pdf_temp)
        return envoi

    except Exception as e:
        log = "\n" + "{}: Création de l'objet EnvoiMAA impossible.".format(datetime.utcnow())
        log = "\n" + "{} - {}".format(configmaa, numero)
        print(log)
        raise SystemError("Impossible d'annuler manuellement le MAA suivant : {} à {}".format(configmaa, datetime.utcnow()))
    
def create_maa_manuel(log, configmaa, date_envoi, debut, fin, fcst, supplement=None):
    """ Permet d'ajouter une instance de EnvoiMAA suite à la demande d'un set_maa (manuel) 
        L'implémentation est à minima. Elle sera complétée par un cron recherchant les états to_create
    """
    #TODO: ne pas oublier de voir comment le supplément est passé
    try:
        numero = definie_numero_maa(configmaa.station.oaci, date_envoi)
        description = create_description(configmaa, fcst)
        envoi = EnvoiMAA.objects.create(
                configmaa = configmaa,
                date_envoi = date_envoi,
                date_debut = debut, 
                date_fin = fin,
                fcst = fcst,
                numero= numero,
                description_maa = description, 
                message = create_raw_message(configmaa, numero, debut, fin, fcst, supplement),
                #at = models.DateTimeField(null=True, blank=True)
                status = 'to_create',
                log = "MAA manuel généré le {}.".format(datetime.utcnow()),
                num_groupe = 1,
                total_groupe = 1,
                entete_transmet = configmaa.station.entete + " " + datetime.strftime(date_envoi, "%d%H%M")
            )

        envoi.save()

        """pdf_temp = None
        try:
            envoi, pdf_temp = create_MAA_pdf_from_envoimaa(envoi)

        except Exception as e:
            log = log + "\n" + "{}: Impossible de créer le PDF pour le MAA.".format(datetime.utcnow())
            log = log + "\n" + "{} - {} - {} - {}".format(configmaa, debut, fin, numero)
            log = log + "\n" + str(e)            
            pdf_temp = None
            print(log)

        envoi.status = 'to_send'
        envoi.log = log"""
        envoi.save()
        #if pdf_temp: os.remove(pdf_temp)
        return envoi

    except Exception as e:
        #TODO: générer un log système le cas échéant
        print(e)
        raise SystemError("Impossible de créer en base le MAA manuel suivant : {} à {}".format(configmaa, datetime.utcnow()))

