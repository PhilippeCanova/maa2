from datetime import datetime, time, timedelta
from html import escape

from django.http.response import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.views.generic import View
from django.views.decorators.cache import cache_page

from django.utils.decorators import method_decorator

from analyseur.models import EnvoiMAA
from analyseur.production import create_maa_manuel, create_cnl_maa_manuel
from configurateur.models import Station, AutorisedMAAs, ConfigMAA
from maa_django.decorators import basicauth, has_perm_expair


from rest_framework.authentication import BasicAuthentication


# Create your views here.
#maa-conf/maa_config.php?action=set_maa&station=LFPG&type_maa=TS&seuil=1&date_debut=2021-08-21%2012:30:00&date_fin=2021-08-21%2020:30:00&fcst=FCST

def check_utcnow():
    return datetime.utcnow()


class SetManuelMAA(View):
    """ Ne gère pas que les maa manuel, il prend en compte toutes les requêtes maa_config.php historiques """
    ENTETE_XML = """<?xml version="1.0" encoding="UTF-8"?>"""

    USAGES = {
        'set_maa': {
            'usage': "maa_config.php?action=set_maa&station=LFRN&type_maa=VENT&seuil=10&date_debut=2016-05-12 13:59:00&date_fin=2016-05-12 25:59:00&message=supplement libre du previ&fcst=FCST|OBS|OBSANDFCST|",
            'description': """Tous les parametres sont obligatoires, cette fonction permet de forcer l'envoi d'un maa manuel. Le parametre format peut prendre la valeur json ou xml (xml par défaut).""",
        },
        'unset_maa': {
            'usage': "maa_config.php?action=unset_maa&station=LFRN&type_maa=VENT&seuil=10",
            'description': """Tous les parametres sont obligatoires. Cette fonction permet de forcer manuellement le cancel d'un maa en cours. Le parametre format peut prendre la valeur json ou xml (xml par défaut).""",
        },
        'get_historique_maa':{
            'usage':"maa_config.php?action=get_historique_maa&stations=LFPG&profondeur=48&format=xml|json",
            "description": "Le parametre stations peut etre vide ou absent dans ce cas l'ensemble des stations sera renvoyé, si il est précisé il peut contenir plusieurs indicatifs de station séparés par une virgule. Le parametre profondeur precise le rendu de l'historique en heures, il n'est pas obligatoire, par défaut il est positionné à 48 h. Le parametre format peut prendre la valeur json ou xml (xml par défaut).",
        },
        'get_config_stations':{
            'usage':"maa_config.php?action=get_config_stations&stations=LFPG&format=xml|json",
            "description": "Le parametre stations peut etre vide ou absent dans ce cas l'ensemble des stations sera renvoyé, si il est précisé il peut contenir plusieurs indicatifs de station séparés par une virgule. Le parametre format peut prendre la valeur json ou xml (xml par défaut).",
        },
    }

    FORMAT_DATE = "%Y-%m-%d %H:%M:%S"

    def formate_xml(self, status, message_status, message='', encoding="UTF-8"):
        chaine = []
        chaine.append(SetManuelMAA.ENTETE_XML)
        chaine.append('<{} date="{}" status="{}">'.format(self.action, datetime.utcnow(), status))
        chaine.append('<message_status><![CDATA[{}]]></message_status>'.format(message_status))
        chaine.append('<usage><![CDATA[{}]]></usage>'.format(SetManuelMAA.USAGES[self.action]['usage']))
        chaine.append('<usage_description><![CDATA[{}]]></usage_description>'.format(SetManuelMAA.USAGES[self.action]['description']))
        
        if isinstance(message, dict):
            chaine.append('<message>')
            chaine.append('<entete><![CDATA[{}]]></entete>'.format(message['entete']))
            chaine.append('<corps_message><![CDATA[{}]]></corps_message>'.format(message['corps_message']))
            chaine.append('</message>')
        chaine.append('</{}>'.format(self.action))
        
        return "\n".join(chaine)

    def formate_reponse(self, status, message_status, message='', encoding="UTF-8"):
        """ Permet de retourner la réponse en fonction du format choisi (json ou xml """

        reponse = {
            "action":self.action,
            "date": datetime.utcnow(), 
            'status':status.upper(),
            "message_status": "{}".format(message_status),
            "usage": SetManuelMAA.USAGES[self.action]['usage'],
            "usage_description": SetManuelMAA.USAGES[self.action]['description'],
            "message": message,
        }

        if status == 'ok':
            if self.format == "json":
                return JsonResponse(reponse)
            else:
                return HttpResponse(self.formate_xml('ok', message_status, message), content_type='text/xml')
        else:
            if self.format == "json":
                return JsonResponse(reponse)
            else:
                return HttpResponseBadRequest(self.formate_xml('ko', message_status, message), content_type='text/xml')

    def set_response_error(self, erreur):
        """ Formate la réponse souhaitée """
        return self.formate_reponse("ko", erreur)

    def set_response_ok(self, envoi):
        """ Formate la réponse souhaitée lorsque le MAA est pris en charge """
        entete = envoi.configmaa.station.entete + " " + datetime.strftime(envoi.date_envoi, "%H%M%S")
        message = {
            "entete": "{}".format(entete),
            "corps_message": "{}".format(envoi.message),
        }
        return self.formate_reponse("ok", "Votre maa manuel a été envoyé.", message)

    def check_param_get_required(self, liste_params, request):
        """ Fonction permettant de vérifier la présence de paramètres requis dans la requête GET passée
            La liste_params contient les clé params

            Retourne l'objet HttpResponse approprié en cas d'erreur ou True si tout passe.
        """
        for cle in liste_params:
            param = request.GET.get(cle, None)
            if param is None:
                return self.set_response_error("Le paramètre {} est requis.".format(cle))
        return True       
        
    def check_format_date(self, liste_params, request, format):
        """ Fonction permettant de vérifier si le format attendu des dates est conforme
            La liste_params contient les clé params

            Retourne l'objet HttpResponse approprié en cas d'erreur ou True si tout passe.
        """
        try: 
            for cle in liste_params:
                date = request.GET.get(cle, None)
                date = datetime.strptime(date, format)
        except Exception as e:
            erreur = "Le format de date attendu est {}.".format(format)
            return self.set_response_error(erreur)

        return True    

    def check_station_ouvert(self, oaci, DATE_NOW):
        """ Permet de vérifier si à l'heure de soumission du maa manuel, la station assure le suivi des MAA 
            Réponse une instance de Station si bon, sinon erreur
        """
        # Check de l'heure d'ouverture de la station
        NOW = DATE_NOW.time()
        try: 
            station = Station.objects.get(oaci = oaci)
            if station.ouverture != time(0,0) and station.ouverture != time(23,59):
                # La station connaît une période de fermeture, on voit si la date actuelle est dans le créneau d'ouverture
                if NOW < station.ouverture or NOW > station.fermeture:
                    return self.set_response_error("La station {} est fermée à {}.".format(oaci, NOW))
        except Exception as e:
            erreur = "La station {} n'est pas reconnue ou n'est pas en capacité d'assurer la production à {}.".format(oaci, NOW)
            return self.set_response_error(erreur)

        return station

    def check_type_maa(self, station, request):
        """ Permet de vérifier si les informations passées pour décrire le type de maa sont valables 
            et conforme aux attendes de la station
        """
        type_maa = request.GET.get('type_maa')
        try: 
            is_occurrence = AutorisedMAAs.get_instance(type_maa)
            if is_occurrence is None:
                return self.set_response_error("Ce type de maa n'est pas reconnu.".format(type_maa))
            is_occurrence = is_occurrence.occurrence
            
            if is_occurrence:
                configmaa = ConfigMAA.objects.get(station__oaci = station.oaci, type_maa=type_maa)
            else:
                seuil = request.GET.get('seuil', None)
                if seuil is None:
                    return self.set_response_error("Un seuil est requis pour ce type de MAA.")
                try:
                        configmaa = ConfigMAA.objects.get(station__oaci = station.oaci, type_maa=type_maa, seuil=seuil)
                except:
                        return self.set_response_error("Ce type de MAA {}-{} n'est pas reconnu pour la station {}.".format(type_maa, seuil, station.oaci))
        except Exception as e:
            return self.set_response_error("Le type de maa {} n'est pas reconnu pour la station {}.".format(type_maa, station.oaci))
        return configmaa

    @has_perm_expair
    def set_manual(self, request):
        """ Gère la soumission d'un maa manuel """
        self.format = request.GET.get('format', 'xml')

        # Check la présence des champs requis 
        valide = self.check_param_get_required(['action', 'station', 'type_maa', 'date_debut', 'date_fin', 'fcst'], request)

        if valide != True:
            return valide

        # Check format date
        valide = self.check_format_date(['date_debut', 'date_fin'], request, SetManuelMAA.FORMAT_DATE)
        if valide != True:
            return valide
        
        # Check station ouverte
        DATE_NOW = check_utcnow()
        station = self.check_station_ouvert(request.GET.get('station'), DATE_NOW)
        if not isinstance(station, Station):
            return station

        # Check la reconnaissance du type de MAA
        configmaa = self.check_type_maa(station, request)
        if not isinstance(configmaa, ConfigMAA):
            return configmaa

        # Check si début dans la période du scan
        limite_debut = DATE_NOW + timedelta(hours=configmaa.scan)
        debut = datetime.strptime(request.GET.get('date_debut'), SetManuelMAA.FORMAT_DATE)
        fin = datetime.strptime(request.GET.get('date_fin'), SetManuelMAA.FORMAT_DATE)
        if debut > limite_debut or debut < DATE_NOW - timedelta(minutes=30):
            return self.set_response_error("Pour respecter la configuration de la station {oaci} la date de début du maa doit se situer entre {now} et {limite}.".format(
                oaci = station.oaci, now = DATE_NOW, limite = limite_debut))
        
        # Check sur la date de fin
        #Pour respecter la configuration de la station $station la date de fin du maa doit se situer entre " . $ma_date_debut->format ( "Y-m-d H:i:s" ) . " et " . $date_max_fin_maa->format ( "Y-m-d H:i:s" ) . 
        limite_fin = debut + timedelta(hours = configmaa.profondeur)
        if fin > limite_fin or fin < debut :
            return self.set_response_error("Pour respecter la configuration de la station {oaci} la date de fin du maa doit se situer entre {now} et {limite}.".format(
                oaci = station.oaci, now = limite_debut, limite = limite_fin))
        
        # Check le paramètre FCST
        fcst = request.GET.get('fcst')
        if fcst[:3] != 'OBS' and fcst[:3] != 'FCS':
            return self.set_response_error("Le paramètre fcst doit prendre l'une des valeurs suivantes : {}.".format(AutorisedMAAs.AUTORISED_FCST))

        # Génère le EnvoiMAA lié à une soumission auto en mode "to_create" pour prise en charge ultérieure
        try:
            log = "Création d'un MAA manuel pour la station {} saisi le {}".format(configmaa.station.oaci, datetime.utcnow())
            envoi = create_maa_manuel(log, configmaa, DATE_NOW, debut, fin, fcst, request.GET.get('supplement', None))
            #TODO: vérifier la prise en charge de fcst en tant que chaîne de caractère dans le PDF
            # Tout s'est déroulé correctement, on retourne l'acquitement avec le message brute
            return self.set_response_ok(envoi)
        except SystemError as e:
            #TODO: faire remonter dans un log système
            return self.set_response_error("La création du MAA a échoué. Veuillez contacter l'administrateur applicatif.")
  
    @has_perm_expair
    def unset_manual(self, request):
        """ Gère la soumission d'une annualtion de maa manuel 
            ex: action=unset_maa&station=LFPG&type_maa=TS&seuil=1&date_reprise=2021-08-21%2012:30:00
        """
        self.format = request.GET.get('format', 'xml')

        # Check la présence des champs requis 
        valide = self.check_param_get_required(['action', 'station', 'type_maa'], request)
        if valide != True:
            return valide

        # Check station ouverte
        DATE_NOW = check_utcnow()
        station = self.check_station_ouvert(request.GET.get('station'), DATE_NOW)
        if not isinstance(station, Station):
            return station

        # Check la reconnaissance du type de MAA
        configmaa = self.check_type_maa(station, request)
        if not isinstance(configmaa, ConfigMAA):
            return configmaa
        
        # Check s'il y a une MAA de ce type à canceller
        maa_en_cours = EnvoiMAA.objects.current_maas_by_type(station.oaci, configmaa.type_maa, DATE_NOW, seuil= configmaa.seuil)
        
        if maa_en_cours is None:
            return self.set_response_error("Pas de maa en cours de type {}-{} pour la station {}.".format(configmaa.type_maa, configmaa.seuil, station.oaci))


        # Génère le EnvoiMAA lié à une annualtion auto en mode "to_create" pour prise en charge ultérieure
        try:
            log = "Annulation manuelle d'un MAA. Heure de saisie : {}".format(datetime.utcnow())
            envoi = create_cnl_maa_manuel(log, configmaa, DATE_NOW, maa_en_cours)
            print('Annulation enregistrée', envoi)
            # Tout s'est déroulé correctement, on retourne l'acquitement avec le message brute
            return self.set_response_ok(envoi)
        except SystemError as e:
            #TODO: faire remonter dans un log système
            return self.set_response_error("L'annulation du MAA a échoué. Veuillez contacter l'administrateur applicatif.")

    @method_decorator(cache_page(60 * 1), name='dispatch')
    def get_historique_maa(self, request):
        """
            Retourne l'ensemble des MAA envoyés sur les dernières heures pour un ensemble de stations
            maa-conf/maa_config.php?action=get_historique_maa&stations=LFPG
        """

        # Check la présence des champs requis 
        valide = self.check_param_get_required(['action'], request)
        if valide != True:
            return valide
        
        UTC_NOW = check_utcnow()

        profondeur = 48 #TODO: il faudrait un meileeur contrôle des valeurs passées
        try: 
            profondeur= int(request.GET.get('profondeur', 48))
        except:
            pass

        stations = request.GET.get('stations', None)
        if stations is None:
            stations = [oaci for (oaci,) in Station.objects.all().values_list('oaci')]
        else:
            stations = request.GET.get('stations').split(',')
        data = []
        for station in stations:
            data.append({
                'station': Station.objects.get(oaci=station), #TODO: attention gérer l'erreur si la station n'existe pas
                'maas': EnvoiMAA.objects.history_maas(profondeur, UTC_NOW, [station])
            })
        
        format = request.GET.get('format', 'xml')
        if format == 'xml':
            reponse = render(
                request,
                'analyseur/get_historique_maa.html',
                context= {
                    'heure_creation': datetime.strftime(UTC_NOW, "%Y-%m-%d %H:%M:%S"),
                    'profondeur': profondeur,
                    'stations': data,
                }
            )
            return HttpResponse(reponse, content_type='text/xml')
        else:
            json = []
            for donnee in data:
                maas = []
                for maa in donnee['maas']:
                    maas.append({
                        #'station': maa.configmaa.station.oaci,
                        'date_envoi': maa.date_envoi,
                        'date_debut': maa.date_debut,
                        'date_fin': maa.date_fin,
                        'numero': maa.numero,
                        'type': maa.configmaa.type_maa,
                        'seuil': maa.configmaa.seuil,
                        })
                json.append({
                    'station': donnee['station'].oaci,
                    'maas': maas,
                })
            return JsonResponse(json, safe=False)

    @method_decorator(cache_page(60 * 1), name='dispatch')
    def get_config_stations(self, request):
        """
            Retourne l'ensemble des configurations d'une station, des maa configurés sur cette station et des maa en cours pour cette station
            maa_config.php?action=get_config_stations&stations=LFPG&format=xml|json
        """
        # Check la présence des champs requis 
        valide = self.check_param_get_required(['action'], request)
        if valide != True:
            return valide
        
        UTC_NOW = check_utcnow()

        stations = request.GET.get('stations', None)
        if stations is None:
            stations = [oaci for (oaci,) in Station.objects.all().values_list('oaci')]
        else:
            stations = request.GET.get('stations').split(',')
        data = []

        type_maa = request.GET.get('type_maa',  None)

        for station in stations:
            #current_maas_by_type(oaci, type_maa, heure= datetime.utcnow(), seuil=None)
            configs = []
            maas = []
            queryset = ConfigMAA.objects.filter(station__oaci = station)
            
            if type_maa is not None: # Ne considère que les configmaa d'un certain type
                queryset = queryset.filter(type_maa=type_maa)

            if len(queryset) == 0:
                continue # La station n'est pas reconnue, on ne la traite pas
            for config in queryset:
                configs.append(config)
                maa = EnvoiMAA.current_maas_by_type(station, config.type_maa, UTC_NOW, config.seuil)
                if maa is not None:
                    maas.append(maa)

            data.append({
                'station': Station.objects.get(oaci=station), #TODO: gérer l'erreur si la station n'existe pas 
                'configs': configs,
                'maas': maas,
            })
        
        format = request.GET.get('format', 'xml')
        if format == 'xml':
            reponse = render(
                request,
                'analyseur/get_config_stations.html',
                context= {
                    'heure_creation': UTC_NOW,
                    'datas': data,
                }
            )
            return HttpResponse(reponse, content_type='text/xml')
        else:
            json = []
            for donnee in data:
                maas = []
                for maa in donnee['maas']:
                    maas.append({
                        #'station': maa.configmaa.station.oaci,
                        'date_envoi': maa.date_envoi,
                        'date_debut': maa.date_debut,
                        'date_fin': maa.date_fin,
                        'numero': maa.numero,
                        'type': maa.configmaa.type_maa,
                        'seuil': maa.configmaa.seuil,
                        })
                json.append({
                    'station': donnee['station'].oaci,
                    'maas': maas,
                })
            return JsonResponse(json, safe=False)

    #TODO: gérer le maa_en_cours
    def get(self, request):
        self.format = 'xml'
        self.action = request.GET.get('action',None)

        if self.action =='set_maa':
            return self.set_manual(request)
        elif self.action =='unset_maa':
            return self.unset_manual(request)
        elif self.action =='get_historique_maa': 
            return self.get_historique_maa(request)
        elif self.action =='get_config_stations':
            return self.get_config_stations(request)
            
        
        return self.set_response_error('Le service demandé n\'existe pas.')

