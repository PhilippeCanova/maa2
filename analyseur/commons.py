"""
    Module permettant de rassembler les fonctions nécessaires pour la recherche des MAA potentiels et la livraison de ceux-ci. 

    A chaque analyse de 15 mn, il faut :
        - récupérer les stations actives et leur configuration
        - lancer une récupération des données
        - définir sur quelles stations il faut faire l'analyse (arrêt de certaines surveillance la nuit)
        - définir les MAA potentiels
        - récupérer les MAA en cours de validité
        - le cas échéant, générer un nouveau MAA  
"""
from datetime import datetime, time, timedelta

from mflog import get_logger

from configurateur.models import Station, ConfigMAA
from analyseur.models import EnvoiMAA
from configurateur.utils import chek_and_change_pivot_date
from analyseur.models import EnvoiMAA
from analyseur.production import create_maa_auto, create_cnl_maa_auto
from donneur.commons import provide_manager


def define_open_airport(NOW):
    """ Définit les stations sur lesquelles la production est actuellement assurée (injustement appelées ouvertes) 
        Retourne le queryset de ces stations.
    """
    # Cet arrondi assure que les stations fermant à 23:59 (donc non fermant) soit bien considérée ouverte
    heure = datetime.time(NOW).replace(second=0).replace(microsecond=0) 
    
    stations = Station.objects.filter(active = True).filter(ouverture__lte = heure).filter(fermeture__gte = heure)
    
    return stations

def define_start_laptime(heure_analyse, configmaa):
    """ Recherche la période durant laquelle on autorise le départ d'un éventuel MAA. 
        Cette période dépend de l'heure d'analyse et du paramètre scan du configmaa.

        Retourne une liste de datetime par pas de 1h dans la période de recherche.
    """
    # arrondi à l'heure précédente
    reseau_analyse = heure_analyse.replace(minute = 0).replace(second=0).replace(microsecond=0) 

    # Paramètre dépendant de la config (généralement 12h)
    scan = configmaa.scan

    reseaux_recherche = []
    for i in range(0, scan+1):
        reseaux_recherche.append( reseau_analyse + timedelta(hours=i) )

    return reseaux_recherche

def recherche_debut_maa(assembleur, oaci, periode_debut, configmaa):
    """ Sur la période acceptable de début MAA, on cherche s'il y a une heure déclenchante pour le type de MAA donné 
        Retourne le datetime du premier déclenchement ou None si rien trouvé.
    """

    for echeance in periode_debut:

        """if oaci == 'LFRN' and configmaa.type_maa == 'TS':
            print('test question: ', echeance, configmaa.type_maa, configmaa.seuil)
            print(assembleur.question_declenche(oaci, echeance, configmaa.type_maa, configmaa.seuil))
            print(assembleur.aero.stations['LFRN'].ordered_echeances[0], assembleur.aero.stations['LFRN'].ordered_echeances[-1])
            print()"""

        """if oaci == 'LFRK' and configmaa.type_maa == 'TMIN':
            print(echeance, configmaa.seuil, oaci, assembleur.question_declenche(oaci, echeance, configmaa.type_maa, configmaa.seuil))
            print(assembleur.get_tempe(oaci, echeance))"""

        if assembleur.question_declenche(oaci, echeance, configmaa.type_maa, configmaa.seuil):
            return echeance
    return None

def delai_retention_depasse(heure_actuelle, envoimaa):
    """ Permet de définir si le délai légal de rétention d'un maa envoyé est déjà dépassé 
        Cette limite dépend de la station (et du paramètre retention)
        Retourne True si le délai est dépassé.
    """
    retention = envoimaa.configmaa.station.retention
    return heure_actuelle > envoimaa.date_envoi + timedelta(hours = retention)

def bientot_fini(heure_actuelle, envoimaa):
    """ Retourne True si le maa passé "envoimaa" se termine dans moins d'une heure """
    return heure_actuelle > envoimaa.date_fin - timedelta(hours=1)

def recherche_fin_maa(assembleur, oaci, heure_debut_declenche, configmaa):
    """ On a trouvé une heure de début de maa dans la période acceptable.
        On cherche à présent une heure de fin dans l'intervalle autorisé.
        Au maximum, le MAA s'arrête à heure début + profondeur (paramètre lié à la confi maa)
        S'il y a une interruption de plus de {Pause} heures, on considère le MAA terminé
        Retourne cette heure, ou à défaut au moins l'heure de début 
    """
    heure_fin_max = heure_debut_declenche + timedelta(hours=configmaa.profondeur)
    echeances = [ heure_debut_declenche + timedelta(hours=i) for i in range(0, configmaa.profondeur)]
    pause = 0
    for echeance in echeances:
        if assembleur.question_declenche(oaci, echeance, configmaa.type_maa, configmaa.seuil):
            pause = 0
        else:
            pause = pause + 1
            if pause > configmaa.pause:
                break
    return echeance - timedelta(hours=pause)

def analyse_15mn(heure_analyse=datetime.utcnow()):

    # Met à jour les heures d'ouverture et de fermeture
    logger = get_logger("analyse_15mn")
    logger.info(f"Vérification du changement d'heure...")
    chek_and_change_pivot_date() 

    # Récupère un queryset des stations en cours de production
    logger.info(f"Récupération des stations à traiter...")
    stations = define_open_airport(heure_analyse)

    logger.info(f"Chargement des données sur le SA CDP...")
    manager_cdp = provide_manager(stations)

    # Parmi les stations en cours d'exploitation, détermine les MAA automatique à analyser
    for station in stations:
        # Récupère les Config de MAA auto à tester.
        configmaa_to_check = ConfigMAA.objects.filter(station__oaci = station.oaci).filter(auto = True)
        
        # Lorsque plusieurs MAA sont envoyés pour une même station, il faut y insérer un numéro d'ordre.
        # Donc on met en place un conteneur spécifique à la station et lorsque tous les types ont été balayés
        # On fait un envoi groupé en fin
        # Le groupe est du type : [ {log:str, 'configmaa':configmaa, 'creation': booleen (si flase, c'est un cnl) 
        #                           'debut': heure_debut_declenche, 'fin': heure_fin_potentielle}]
        groupe_envoi = []

        for configmaa in configmaa_to_check:
            # Récupère le MAA déjà en cours s'il y en a un
            maa_en_cours = EnvoiMAA.current_maas_by_type(station.oaci, configmaa.type_maa, heure_analyse, configmaa.seuil)

            # Période de recherche du début d'un éventuel MAA
            periode_debut = define_start_laptime(heure_analyse, configmaa)

            heure_debut_declenche = recherche_debut_maa(manager_cdp, station.oaci, periode_debut, configmaa)

            if heure_debut_declenche is None:
                # Pas de MAA en vue
                # S'il y a un MAA en cours, qu'on a passé la limite de rétention, et qu'il finit dans plus d'une heure, on doit le cancellé
                # sinon on ne fait rien"""

                if maa_en_cours is not None and delai_retention_depasse(heure_analyse, maa_en_cours):
                    if not bientot_fini(heure_analyse, maa_en_cours):
                        log = "Génère un cas 5 (annulation pour {} effet immédiat".format(station.oaci)
                        logger.info(log)
                        groupe_envoi.append({'log':log, 'configmaa':configmaa, 'creation': False, 
                                             'debut': None, 'fin': None, 'maa_annule': maa_en_cours})
                        

                # Plus rien à faire si pas de MAA en vue, donc on peut passer à la boucle suivante
                continue

            # A ce stade, il y a un MAA potentiel à venir (car heure de déclenchement). 
            # Il faut déterminer à sa date de fin de validité potentielle
            heure_fin_potentielle = recherche_fin_maa(manager_cdp, station.oaci, heure_debut_declenche, configmaa)
            #TODO: tester la recherche potentielle d'heure de fin. 

            """if station.oaci == 'LFRH' and configmaa.type_maa == 'FG':
                print("debut declenche", heure_debut_declenche)
                print("fin declenche", heure_fin_potentielle)"""
                

            if maa_en_cours is None:
                # S'il n'y avait pas de MAA en cours et que le nouveau se termine avant l'heure d'analyse, le 
                # phénomène est obsoluète, on laisse tombé. 
                if heure_fin_potentielle < heure_analyse:
                    continue

                # Pas de MAA en cours, donc mais ici, on a un MAA en vue, donc il faut le générer :
                log = "Génère un MAA pour {} de type {}/{} de {} à {}\n".format(station.oaci, configmaa.type_maa, configmaa.seuil, heure_debut_declenche, heure_fin_potentielle)
                log = log + "Il n'y avait pas d'autres MAA en cours.\n"
                logger.info(log)
                groupe_envoi.append({'log':log, 'configmaa':configmaa, 'creation': True, 'debut': heure_debut_declenche, 'fin': heure_fin_potentielle})
                continue
            
            # On a donc maintenant un MAA en cours et un MAA potentiel. On va faire une suite de tests permettant
            # de savoir s'il y a opportunité d'envoyer un nouveau MAA. (cf spec DP-8)
            # Nomenclature : 
            # test1 = debut_new < debut_old
            # test2 = NOW > limite de rétention
            # test3 = fin_new <= fin_old
            # test4 = NOW < debut_old
            # test5 = debut_new > debut_old + repousse
            # test6 = debut_new > NOW + repousse
            # test7 = fin_new <= fin_old - repousse
            # test8 = debut_new > fin_old
            # test9 = fin_new <= fin_old + repousse
            # test10 = NOW >= fin-old - reconduction
            retention = station.retention
            repousse = station.repousse
            reconduction = station.reconduction

            test1 = heure_debut_declenche < maa_en_cours.date_debut
            test2 = heure_analyse > (maa_en_cours.date_envoi + timedelta(hours = retention))
            test3 = heure_fin_potentielle <= maa_en_cours.date_fin
            test4 = heure_analyse < maa_en_cours.date_debut
            test5 = heure_debut_declenche > (maa_en_cours.date_debut + timedelta(hours = repousse))
            test6 = heure_debut_declenche > (heure_analyse + timedelta(hours = repousse))
            test7 = heure_fin_potentielle <= ( maa_en_cours.date_fin - timedelta(hours = repousse))
            test8 = heure_debut_declenche > maa_en_cours.date_fin
            #test9 = heure_fin_potentielle <= (maa_en_cours.date_fin + timedelta(hours = repousse))
            test10 = heure_analyse >= (maa_en_cours.date_fin - timedelta(hours = reconduction))

            if not test1 and test2 and test3 and test4 and test5:
                log = "Génère un cas 1-1 pour {} de type {}/{} de {} à {}\n".format(station.oaci, configmaa.type_maa, configmaa.seuil, heure_debut_declenche, heure_fin_potentielle)
                logger.info(log)
                groupe_envoi.append({'log':log, 'configmaa':configmaa, 'creation': True, 'debut': heure_debut_declenche, 'fin': heure_fin_potentielle})
            elif not test1 and test2 and test3 and not test4 and test6:
                log = "Génère un cas 1-2 pour {} de type {}/{} de {} à {}\n".format(station.oaci, configmaa.type_maa, configmaa.seuil, heure_debut_declenche, heure_fin_potentielle)
                logger.info(log)
                groupe_envoi.append({'log':log, 'configmaa':configmaa, 'creation': True, 'debut': heure_debut_declenche, 'fin': heure_fin_potentielle})
            elif not test1 and test2 and test3 and not test4 and not test6 and test7:
                log = "Génère un cas 1-3 pour {} de type {}/{} de {} à {}\n".format(station.oaci, configmaa.type_maa, configmaa.seuil, heure_debut_declenche, heure_fin_potentielle)
                logger.info(log)
                groupe_envoi.append({'log':log, 'configmaa':configmaa, 'creation': True, 'debut': heure_debut_declenche, 'fin': heure_fin_potentielle})
            elif test1:
                log =  "Génère un cas 2 pour {} de type {}/{} de {} à {}\n".format(station.oaci, configmaa.type_maa, configmaa.seuil, heure_debut_declenche, heure_fin_potentielle)
                logger.info(log)
                groupe_envoi.append({'log':log, 'configmaa':configmaa, 'creation': True, 'debut': heure_debut_declenche, 'fin': heure_fin_potentielle})
            elif not test1 and test2 and not test3 and test4 and not test8:
                log = "Génère un cas 3-1 pour {} de type {}/{} de {} à {}\n".format(station.oaci, configmaa.type_maa, configmaa.seuil, heure_debut_declenche, heure_fin_potentielle)
                logger.info(log)
                groupe_envoi.append({'log':log, 'configmaa':configmaa, 'creation': True, 'debut': heure_debut_declenche, 'fin': heure_fin_potentielle})
            elif not test1 and test2 and not test3 and not test4 and test6 and not test8 and not test10:
                log = "Génère un cas 3-2 pour {} de type {}/{} de {} à {}\n".format(station.oaci, configmaa.type_maa, configmaa.seuil, heure_debut_declenche, heure_fin_potentielle)
                logger.info(log)
                groupe_envoi.append({'log':log, 'configmaa':configmaa, 'creation': True, 'debut': heure_debut_declenche, 'fin': heure_fin_potentielle})
            elif not test1 and test2 and not test3 and not test4 and not test8 and test10:
                log = "Génère un cas 3-3 pour {} de type {}/{} de {} à {}\n".format(station.oaci, configmaa.type_maa, configmaa.seuil, heure_debut_declenche, heure_fin_potentielle)
                logger.info(log)
                groupe_envoi.append({'log':log, 'configmaa':configmaa, 'creation': True, 'debut': heure_debut_declenche, 'fin': heure_fin_potentielle})
            elif not test1 and test2 and not test3 and test8 :
                log = "Génère un cas 4 pour {} de type {}/{} de {} à {}\n".format(station.oaci, configmaa.type_maa, configmaa.seuil, heure_debut_declenche, heure_fin_potentielle)
                logger.info(log)
                groupe_envoi.append({'log':log, 'configmaa':configmaa, 'creation': True, 'debut': heure_debut_declenche, 'fin': heure_fin_potentielle})

        total = len(groupe_envoi)
        for ind, envoi in enumerate(groupe_envoi):
            if not envoi['creation']:
                create_cnl_maa_auto(envoi['log'], manager_cdp, envoi['configmaa'], heure_analyse, ind+1, total, envoi['maa_annule'])
            else:
                create_maa_auto(envoi['log'], manager_cdp, envoi['configmaa'], heure_analyse, envoi['debut'], envoi['fin'], ind+1, total)
            
            


    

    



