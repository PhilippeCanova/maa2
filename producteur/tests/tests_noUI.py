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


from analyseur.models import EnvoiMAA
from analyseur.commons import define_open_airport
from analyseur.production import create_maa_auto
from donneur.commons import AeroDataStations, CDPDataStations, ManagerData
from donneur.commons import provide_manager
from producteur.pdf_tools import create_MAA_pdf_from_envoimaa
from producteur.commons import check_production
from configurateur.models import Station, ConfigMAA


# Create your tests here.
class MessageMAA_TestCase(StaticLiveServerTestCase, TestCase ):
    @classmethod
    def setUpClass(cls):
        """ Utlisé pour une utilisation commune à toutes les fonctions test de cette clasee 
            mais lancé une seule fois """

        # Insertion en base des données initiales. Permet d'avoir une liste des stations aéro
        from configurateur.initiate_toolbox.initiate_db_tools import Initiate
        super().setUpClass()
        init = Initiate()
        init.create_all_base_test()

    def setUp(self):
        """ Executée à chaque lancement d'une fonction test_ de cette classe 
            TODO: enelever ensuite si pas utilisée.
        """
        settings.RUNNING_SERVER = self.live_server_url

    def get_stations(self):
        """ Permet de générer un tableau avec les infos des stations nécessaire au lancement des extractions """
        stations_objects = Station.objects.all() #TODO: voir éventuellement d'utiliser values_list
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

    def create_configmaa(self, oaci, type_maa, debut, fin, seuil=None):
        """ Permet de simulter un maa en cours de type TS pour une station oaci 
            en fixant les heures d'envoi, de début et de fin.

            Renvoie l'instant de l'envoi.
        """
        
        station = Station.objects.get(oaci = oaci)
        station.retention = 1
        station.reconduction = 3
        station.repousse = 3
        station.save()
        
        conf_maa = ConfigMAA.objects.get(station__oaci = oaci, type_maa= type_maa)
        conf_maa.seuil = seuil
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

        attendus = {
            'TS':"Des orages sont prévus durant la période de validité.",
            'HVY_TS': "Des orages violents sont prévus durant la période de validité.",
            'SQ' :"Du grain est prévu durant la période de validité.",
            'FG' :"Du brouillard est prévu durant la période de validité.",
            'DENSE_FG' :"Du brouillard dense est prévu durant la période de validité.",
            'SN' :"De la neige est prévue durant la période de validité.",
            'HVY_SN':"De la neige forte est prévue durant la période de validité.",
            'FZDZ' :"De la bruine verglaçante est prévue durant la période de validité.",
            'HVY_FZDZ':"De la bruine verglaçante forte est prévue durant la période de validité.",
            'VENT_MOY' :"Un vent moyen >= 10kt est prévu durant la période de validité.",
            'VENT' :"Des vent max ou rafales >= 10kt sont prévus durant la période de validité.",
            'VEHICLE_RIME' :"De la gelée blanche véhicule est prévue durant la période de validité.",
            'TMIN' :"Une température <= 10°C est prévue durant la période de validité.",
            'TMAX' :"Une température >= 10°C est prévue durant la période de validité.",
            'TOXCHEM':"Des produits chimiques toxiques sont prévus durant la période de validité.",
            'TC' :"Des cyclones tropicaux sont prévus durant la période de validité.",
            'DU' :"Des vents de poussiere sont prévus durant la période de validité.",
            'DS' :"Des tempêtes de poussiere sont prévues durant la période de validité.",
            'SS' :"Des tempêtes de sable sont prévues durant la période de validité.",
            'RIME' :"Des gelées blanches sont prévues durant la période de validité.",
            'RR1' :"Des cumuls de précipitations >= 10mm/1h sont prévus durant la période de validité.",
            'RR3' :"Des cumuls de précipitations >= 10mm/3h sont prévus durant la période de validité.",
            'RR6' :"Des cumuls de précipitations >= 10mm/6h sont prévus durant la période de validité.",
            'RR12' :"Des cumuls de précipitations >= 10mm/12h sont prévus durant la période de validité.",
            'RR24' :"Des cumuls de précipitations >= 10mm/24h sont prévus durant la période de validité.",
            'GR' :"De la grêle est prévue durant la période de validité.",
            'HVY_GR' :"De la grêle forte est prévue durant la période de validité.",
            'FWOID' :"De la Tempé <0°C sans dépot de glace au sol est prévue durant la période de validité.",
            'FWID' :"De la Tempé <0°C avec dépot de glace au sol est prévue durant la période de validité.",
            'ICE_DEPOSIT' :"Des dépots de glace sont prévus durant la période de validité.",
            'FZFG' :"Du brouillard givrant est prévu durant la période de validité.",
            'SNRA' :"Des pluies et neiges mélées sont prévues durant la période de validité.",
            'HVY_SNRA' :"Des pluies et neiges mélées fortes sont prévues durant la période de validité.",
            'FZRA' :"De la pluie verglaçante est prévue durant la période de validité.",
            'HVY_FZRA' :"Des pluies verglaçantes fortes sont prévues durant la période de validité.",
            'SA' :"Des tempêtes de sable sont prévues durant la période de validité.",
            'VA' :"Des cendres volcaniques sont prévues durant la période de validité.",
            'SEA':"Des coups de mer sont prévus durant la période de validité.",
            'INV_TEMPE' :"Des inversions de température sont prévues durant la période de validité.",
            'BLSN' :"Du poudrin de glace est prévu durant la période de validité.",
            'TSUNAMI' :"Des tsunamis sont prévus durant la période de validité.",
            'HVY_SWELL' :"Des fortes houles sont prévues durant la période de validité.",
        }

        maas = AutorisedMAAs.autorised
        for key, value in maas.items():
            fcst = "FCST"
            at = datetime(2021,11,12,10,3)
            seuil = None
            if not value.occurrence:
                seuil = 10
            
            recu = value.get_description(fcst, seuil, at)
            self.assertEqual(recu, attendus[key])

    @patch("donneur.commons.request_data_cdp")
    def test_production_MAA_description_longue(self, mock_request_data_cdp):
        # Récupération des données via les SA CDP simulés par le TC1
        num_TC = '1'
        mock_request_data_cdp.side_effect=[
            self.get_data_tc(num_TC,'cdpaero'),
            self.get_data_tc(num_TC,'cdph'), 
            self.get_data_tc(num_TC,'cdpq'), 
            self.get_data_tc(num_TC,'cdphom'), 
            self.get_data_tc(num_TC,'cdpqom'),  
        ]

        heure_analyse=datetime(2021,11,11,5,15)
        stations = define_open_airport(heure_analyse)
        manager_cdp = provide_manager(stations)
        configmaa = self.create_configmaa("LFAQ", "DU" , datetime(2021,11,11,5), datetime(2021,11,11,15))
        create_maa_auto("", manager_cdp, configmaa, heure_analyse, datetime(2021,11,11,5), datetime(2021,11,11,15), 1 ,1)

    def test_production_pdf_avec_vent(self):
        """ Permet de tester la création d'un MAA (et export PDF) sur un MAA VENT avec graphique """
        from analyseur.production import definie_numero_maa, create_description_cnl, create_raw_message_cnl

        DATE_NOW = datetime.utcnow()
        configmaa = self.create_configmaa("LFMN", "VENT", datetime.utcnow(), datetime.utcnow(), 10)
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
        ff = [0.1,0.1,8,6,9,12,15,10,18,25,18,10,15,12,5,3,0.1,0.1,6,9,8,6,4,9]
        fx = [0.1,0.1,8,6,9,15,20,15,25,30,30,20,15,12,5,3,0.1,0.1,6,9,8,6,4,9]
        DD = [30,30,30,60,90,200,210,220,200,270,270,250,200,180,30,30,30,20,20,40,30,40,50,90]
        for i in range(0, 24):
            data.append( (datetime.strftime(date_start + timedelta(hours=i),"%Y-%m-%d %H:%M:%S"), (ff[i], fx[i], DD[i]))  )
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
        check_production()

        repertoire = Path(settings.BASE_DIR, 'media', 'uploads', str(DATE_NOW.year), str(DATE_NOW.month), str(DATE_NOW.day))
        p = Path(repertoire)
        seuil = envoi.configmaa.seuil
        if seuil is not None:
            seuil = str(float(seuil))
        name = "MAA_{}_{}_{}_{}".format(
                    envoi.configmaa.station.oaci, 
                    envoi.configmaa.type_maa, 
                    seuil,
                    datetime.strftime(envoi.date_envoi, "%Y-%m-%d_%H%M%S"),
                    )
        trouve = len(list(p.glob(name + '*.pdf')))
        self.assertGreaterEqual(trouve, 1)
 
    def test_production_pdf_avec_temperature(self):
        """ Permet de tester la création d'un MAA (et export PDF) sur un MAA TMIN avec graphique """
        from analyseur.production import definie_numero_maa, create_description_cnl, create_raw_message_cnl

        DATE_NOW = datetime.utcnow()
        configmaa = self.create_configmaa("LFMN", "TMIN", datetime.utcnow(), datetime.utcnow(),-1)
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
        check_production()
        
        repertoire = Path(settings.BASE_DIR, 'media', 'uploads', str(DATE_NOW.year), str(DATE_NOW.month), str(DATE_NOW.day))
        p = Path(repertoire)
        seuil = envoi.configmaa.seuil
        if seuil is not None:
            seuil = str(float(seuil))
        name = "MAA_{}_{}_{}_{}".format(
                    envoi.configmaa.station.oaci, 
                    envoi.configmaa.type_maa, 
                    seuil,
                    datetime.strftime(envoi.date_envoi, "%Y-%m-%d_%H%M%S"),
                    )
        trouve = len(list(p.glob(name + '*.pdf')))
        self.assertGreaterEqual(trouve, 1)




