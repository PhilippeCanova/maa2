from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
import json
import os
import random
import asyncio, urllib3
from urllib3.packages.six import assertCountEqual

from django.shortcuts import resolve_url
from django.urls import reverse, resolve
from django.core.files import File
from django.test import TestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings


from configurateur.models import Station, ConfigMAA
from analyseur.models import EnvoiMAA
from donneur.commons import AeroDataStations, CDPDataStations, ManagerData
from producteur.pdf_tools import create_MAA_pdf_from_envoimaa

# Create your tests here.
class MessageMAA_TestCase(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        """ Utlisé pour une utilisation commune à toutes les fonctions test de cette clasee 
            mais lancé une seule fois """

        # Insertion en base des données initiales. Permet d'avoir une liste des stations aéro
        from maa_django.apps.core.management.commands.initiate import Initiate
        super().setUpClass()
        init = Initiate()
        init.delete()
        init.create()

    def setUp(self):
        """ Executée à chaque lancement d'une fonction test_ de cette classe 
            TODO: enelever ensuite si pas utilisée.
        """
        settings.RUNNING_SERVER = self.live_server_url

    def tearDown(self):
        """ Executée après chaque lancement d'une fonction test_ de cette classe 
            TODO: enelever ensuite si pas utilisée.
        """
        #TODO: faire en sorte de nettoyer les fichiers créés
        pass

    def get_stations(self):
        """ Permet de générer un tableau avec les infos des stations nécessaire au lancement des extractions """
        stations_objects = Station.objects.all()
        stations = []
        for station in stations_objects:
            stations.append(( station.oaci, station.inseepp, station.outremer ))
        return stations

    def get_data_tc(self, num_TC, fichier): 
        """ Récupère les données aéro et cdp du cas de TC cité """
        repertoire = Path(__file__).parent.joinpath('TC'+num_TC)
        if not repertoire.exists():
            raise FileExistsError("Le répertoire {} n'existe pas".format(repertoire) )

        fichier = repertoire.joinpath(fichier + '.csv')
        if not fichier.exists():
            raise FileExistsError("Le ficheir {} n'existe pas".format(fichier) )
        
        with open(fichier, 'r') as ficin:
            return ficin.read()
        
        raise KeyError("Imposible de trouver le fichier {} du TC{}".format(fichier, numTC))

    def create_configmaa(self, oaci, type_maa, debut, fin):
        """ Permet de simulter un maa en cours de type TS pour une station oaci 
            en fixant les heures d'envoi, de début et de fin.

            Renvoie l'instant de l'envoi.
        """
        
        station = Station.objects.get(oaci = oaci)
        station.retention = 1
        station.reconduction = 3
        station.repousse = 3
        station.save()
        
        conf_maa = ConfigMAA.objects.get(station__oaci = oaci, type_maa= 'TS')
        conf_maa.seuil = None
        conf_maa.scan = 12
        conf_maa.auto = True
        conf_maa.save()
        return conf_maa
    
    def create_envoimaa(self, config, heure_envoi, debut, fin, fcst="FCST"):
        from analyseur.production import create_description
        description = create_description(config, fcst)
        envoi = EnvoiMAA.objects.create(
            configmaa = config,
            date_envoi = heure_envoi,
            date_debut = debut,
            date_fin = fin,
            numero = 1,
            description_maa = description,
            fcst="FCST",
            status = 'to_send',
            message = "Cors message",
            context_TAF = "context TaF",
            log = "Ici, les logs de création",
            message_mail = 'Corps du mail',
            message_sms = "message SMS",
        )
        envoi.save()
        return envoi

    def test_message_descriptif(self):
        """ permet, en lecture simple sur console, de vérifier la syntaxe des descriptions des MAA (pour fichier PDF)"""
        from configurateur.models import AutorisedMAAs

        maas = AutorisedMAAs.autorised
        for key, value in maas.items():
            fcst = "FCST"
            at = datetime(2021,11,12,10,3)
            seuil = None
            if not value.occurrence:
                seuil = 10
            print (key, "Féminin: ", value.decription_genre_féminin, " singulier: ", value.description_singulier)
            print (value.get_description(fcst, seuil, at))
            print ()

    @patch("donneur.commons.request_data_cdp")
    def test_production_MAA_description_longue(self, mock_request_data_cdp):
        # Récupération des données via les SA CDP simulés par le TC1
        num_TC = '1'
        mock_request_data_cdp.side_effect=[
            self.get_data_tc(num_TC,'cdpaero'),
            self.get_data_tc(num_TC,'cdph'), 
            self.get_data_tc(num_TC,'cdpq'), 
            #self.get_data_tc(num_TC,'cdphom'), 
            #self.get_data_tc(num_TC,'cdpqom'),  
        ]

        from analyseur.commons import define_open_airport
        from donneur.commons import provide_manager
        from analyseur.production import create_maa_auto
        heure_analyse=datetime(2021,11,11,5,15)
        stations = define_open_airport(heure_analyse)
        manager_cdp = provide_manager(stations)
        configmaa = self.create_configmaa("LFAQ", "DU" , datetime(2021,11,11,5), datetime(2021,11,11,15))
        create_maa_auto("", manager_cdp, configmaa, heure_analyse, datetime(2021,11,11,5), datetime(2021,11,11,15), 1 ,1)

    def test_production_pdf_avec_vent(self):
        """ Permet de tester la création d'un MAA (et export PDF) sur un MAA VENT avec graphique """
        from analyseur.production import definie_numero_maa, create_description_cnl, create_raw_message_cnl

        DATE_NOW = datetime.utcnow()
        configmaa = self.create_configmaa("LFMN", "VENT", datetime.utcnow(), datetime.utcnow())
        maa_en_cours = self.create_envoimaa(configmaa, DATE_NOW, DATE_NOW, DATE_NOW, "FCST")
        
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
        
        message_mail = ""
        log = "Création un MAA effectif pour les tests de vent"

        # Crée l'instance d'envoiMAA
        data= []
        # (echeance, (ff,fx,dd))
        date_start = datetime(2021,11,26,10,0,0)
        for i in range(0, 24):
            data.append( (datetime.strftime(date_start + timedelta(hours=i),"%Y-%m-%d %H:%M:%S"), ( 10, 15, 300))  )
        data= json.dumps(data)

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
                entete_transmet = configmaa.station.entete + " " + datetime.strftime(DATE_NOW, "%d%H%M"),
                data_vent = data,
            )
        envoi.save()
    
        pdf_temp = None
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
        envoi.log = log
        envoi.save()
        if pdf_temp: os.remove(pdf_temp)
        
    def test_production_pdf_avec_temperature(self):
        """ Permet de tester la création d'un MAA (et export PDF) sur un MAA TMIN avec graphique """
        from analyseur.production import definie_numero_maa, create_description_cnl, create_raw_message_cnl

        DATE_NOW = datetime.utcnow()
        configmaa = self.create_configmaa("LFMN", "TMIN", datetime.utcnow(), datetime.utcnow())
        maa_en_cours = self.create_envoimaa(configmaa, DATE_NOW, DATE_NOW, DATE_NOW, "FCST")
        
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
        
        message_mail = ""
        log = "Création un MAA effectif pour les tests de température"

        # Crée l'instance d'envoiMAA
        data= []
        # (echeance, (ff,fx,dd))
        date_start = datetime(2021,11,26,10,0,0)
        for i in range(0, 24):
            data.append( (datetime.strftime(date_start + timedelta(hours=i),"%Y-%m-%d %H:%M:%S"), random.randrange(-3, 5)) )
        data= json.dumps(data)

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
                cancel = False,
                context_CDPH = context_CDP,
                context_CDPQ = "",
                log = log,
                message_mail = message_mail,
                message_sms = message_sms,
                entete_transmet = configmaa.station.entete + " " + datetime.strftime(DATE_NOW, "%d%H%M"),
                data_tempe = data,
            )
        envoi.save()
        

        pdf_temp = None
        try:
            envoi, pdf_temp = create_MAA_pdf_from_envoimaa(envoi)

        except Exception as e:
                log = log + "\n" + "{}: Impossible de créer le PDF pour l'annulation de MAA.".format(datetime.utcnow())
                log = log + "\n" + "{} - {}".format(configmaa, numero)
                log = log + "\n" + str(e)            
                pdf = None
                print(log)
                raise SystemError("Impossible de créer le PDF pour l'annulation du MAA suivant : {} à {}".format(configmaa, datetime.utcnow()))

        envoi.status = ('to_send', 'Nouveau')
        envoi.log = log
        envoi.save()
        if pdf_temp: os.remove(pdf_temp)
        




