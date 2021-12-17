import datetime, time

from unittest.mock import patch
from pathlib import Path

from django.test import TestCase
from django.test import LiveServerTestCase, RequestFactory
from django.contrib.auth.models import User, Group, Permission
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings

from analyseur.commons import define_open_airport
from configurateur.models import AutorisedMAAs, Region, Station, ConfigMAA
from configurateur.initiate_toolbox.initiate_db_tools import Initiate
from configurateur.utils import retrieve_pivot, chek_and_change_pivot_date
from donneur.commons import provide_manager
from producteur.commons import analyse_1mn
from analyseur.commons import EnvoiMAA
from analyseur.commons import analyse_15mn

# Create your tests here.
class ConfigurateurTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        """ Utlisé pour une utilisation commune à toutes les fonctions test de cette classe 
            mais lancé une seule fois """
        super().setUpClass()
        init = Initiate()
        init.create_all_base_test()

    def retrieve_infos_changement_heure_station(self, oaci):
        """ Récupère les informations de changement d'heure d'une station """
        station = Station.objects.get(oaci=oaci)
        return station.date_pivot, station.ouverture, station.fermeture

    @patch("configurateur.utils.retrieve_utcnow")
    def testChangeDatePivot(self, mock_retrieve_utcnow):
        """ Test le changement d'heure des stations qui est lancé à chaque cycle de 15mn """
        mock_retrieve_utcnow.return_value = datetime.datetime(2021,11,5,0,0,0,0) # Simule la date de lancement
        pivot1 = retrieve_pivot(2021, 4)
        pivot2 = retrieve_pivot(2021, 11)
        pivot3 = retrieve_pivot(2022, 4)

        # Vérifie le bon calcul de date de changement d'heure
        self.assertEqual(pivot1, datetime.datetime(2021,3,28,1,0,0))
        self.assertEqual(pivot2, datetime.datetime(2021,10,31,1,0,0))
        self.assertEqual(pivot3, datetime.datetime(2022,3,27,1,0,0))

        # Premier cas, pas de changement d'heure par rapport à la config de la base qui est sur l'heure d'été
        # Donc doit retrouver les heures ouverture et fermeture d'été
        mock_retrieve_utcnow.return_value = datetime.datetime(2021,6,5,0,0,0) # Simule la date de lancement
        chek_and_change_pivot_date()
        date_pivot, ouverture, fermeture = self.retrieve_infos_changement_heure_station('EEEE')
        self.assertEqual(date_pivot, datetime.datetime(2021,10,31,1,0,0,0))
        self.assertEqual(ouverture, datetime.time(6,0,0))
        self.assertEqual(fermeture, datetime.time(17,15,0))

        # Deuxième cas, juste avant le changement d'heure, pas de changement d'heure par rapport à la config de la base qui est sur l'heure d'été
        # Donc doit retrouver les heures ouverture et fermeture d'été
        mock_retrieve_utcnow.return_value = datetime.datetime(2021,10,31,1,0,0,0) # Simule la date de lancement
        chek_and_change_pivot_date()
        date_pivot, ouverture, fermeture = self.retrieve_infos_changement_heure_station('EEEE')
        self.assertEqual(date_pivot, datetime.datetime(2021,10,31,1,0,0))
        self.assertEqual(ouverture, datetime.time(6,0,0))
        self.assertEqual(fermeture, datetime.time(17,15,0))

        # Troisième cas, on passe la date pivot pour le changement en heure d'hiver 
        # Donc doit retrouver les heures ouverture et fermeture d'hiver
        mock_retrieve_utcnow.return_value = datetime.datetime(2021,10,31,1,5,0,0) # Simule la date de lancement
        chek_and_change_pivot_date()
        date_pivot, ouverture, fermeture = self.retrieve_infos_changement_heure_station('EEEE')
        self.assertEqual(date_pivot, datetime.datetime(2022,3,27,1,0,0))
        self.assertEqual(ouverture, datetime.time(7,0,0))
        self.assertEqual(fermeture, datetime.time(18,15,0))

        # Quatrième cas, on change d'année, pas de changements, on reste en heure d'hiver 
        # Donc doit retrouver les heures ouverture et fermeture d'hiver
        mock_retrieve_utcnow.return_value = datetime.datetime(2022,1,2,0,0,0,0) # Simule la date de lancement
        chek_and_change_pivot_date()
        date_pivot, ouverture, fermeture = self.retrieve_infos_changement_heure_station('EEEE')
        self.assertEqual(date_pivot, datetime.datetime(2022,3,27,1,0,0))
        self.assertEqual(ouverture, datetime.time(7,0,0))
        self.assertEqual(fermeture, datetime.time(18,15,0))

        # Cinquième cas, on change repasse en heure d'été car on passe le change d'heure de mars
        # Donc doit retrouver les heures ouverture et fermeture d'été
        mock_retrieve_utcnow.return_value = datetime.datetime(2022,3,27,1,5,0,0) # Simule la date de lancement
        chek_and_change_pivot_date()
        date_pivot, ouverture, fermeture = self.retrieve_infos_changement_heure_station('EEEE')
        self.assertEqual(date_pivot, datetime.datetime(2022,10,30,1,0,0))
        self.assertEqual(ouverture, datetime.time(6,0,0))
        self.assertEqual(fermeture, datetime.time(17,15,0))
        
class InitiateurTestCase(TestCase):
    """ Cette classe test va permettre de tester l'initialisation des données via la toolbox """
    
    @classmethod
    def setUpClass(cls):
        """  """
        from configurateur.initiate_toolbox.initiate_db_tools import Initiate
        super().setUpClass()
        init = Initiate()
        init.create_all_base_test()
        
    def test_import_for_test(self):
        """ Test une itialisation complète à partir des données de test (box_test) """

        #Check régions
        self.assertEqual(len(Region.objects.all()), 5)

        # Check Groupes
        self.assertEqual(len(Group.objects.all()), 4)

        # Check utilisateurs
        self.assertEqual(len(User.objects.all()), 4)

        # Check configmaa
        self.assertEqual(len(ConfigMAA.objects.filter(station__oaci = "AAAA")), len(AutorisedMAAs.autorised)) 
        configmaa = ConfigMAA.objects.get(station__oaci = "AAAA", type_maa= 'TS')
        self.assertEqual(configmaa.pause, 2) 
        self.assertEqual(configmaa.scan, 3)
        self.assertEqual(configmaa.profondeur, 12)  
        
# Create your tests here.
class RejeuSituation_TestCase(StaticLiveServerTestCase, TestCase ):
    @classmethod
    def setUpClass(cls):
        """ Utlisé pour une utilisation commune à toutes les fonctions test de cette clasee 
            mais lancé une seule fois """

        # Insertion en base des données initiales. Permet d'avoir une liste des stations aéro
        from configurateur.initiate_toolbox.initiate_db_tools import Initiate
        super().setUpClass()
        repertoire = Path(__file__).parent
        init = Initiate(repertoire = repertoire.joinpath("TC1"))
        init.create_all_base_test(with_real_configmaa = True)

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

    @patch("donneur.commons.request_data_cdp")
    def test_TC1_FMCZ(self, mock_request_data_cdp):
        """
            TC permettant de tester le cas FMCZ avec une analyse à 14:35 et une production de MAA de 14 à 14TU !
        """
        num_TC = '1'
        mock_request_data_cdp.side_effect=[
            self.get_data_tc(num_TC,'cdpaero'),
            self.get_data_tc(num_TC,'cdph'), 
            self.get_data_tc(num_TC,'cdpq'), 
            self.get_data_tc(num_TC,'cdphom'), 
            self.get_data_tc(num_TC,'cdpqom'),  
        ]

        heure_analyse= datetime.datetime(2021,12,14,14,35)

        # S'assure qu'il n'y a pas de MAA FMCZ déjà en cours 
        self.assertEqual(len(EnvoiMAA.objects.filter(configmaa__station__oaci = 'FMCZ')), 0)

        analyse_15mn(heure_analyse) # Doit trouver le MAA

        # S'assure qu'après l'analyse, il n'y a toujours pas de MAA FMCZ 
        # (car déjà terminé à l'heure de l'analyse)
        self.assertEqual(len(EnvoiMAA.objects.filter(configmaa__station__oaci = 'FMCZ')), 0)
        
    @patch("donneur.commons.request_data_cdp")
    def test_TC1_LFRH(self, mock_request_data_cdp):
        """
            TC permettant de tester le cas LFRH avec une analyse à 14:35 et une production de MAA de 14 à 14TU !
        """
        num_TC = '1'
        mock_request_data_cdp.side_effect=[
            self.get_data_tc(num_TC,'cdpaero'),
            self.get_data_tc(num_TC,'cdph'), 
            self.get_data_tc(num_TC,'cdpq'), 
            self.get_data_tc(num_TC,'cdphom'), 
            self.get_data_tc(num_TC,'cdpqom'),  
        ]

        heure_analyse= datetime.datetime(2021,12,15,9,45)

        # S'assure qu'il y a déjà un MAA LFRH FG déjà en cours de 09 à 10TU
        conf_maa = ConfigMAA.objects.get(station__oaci = 'LFRH', type_maa= 'FG')
        envoi = EnvoiMAA.objects.create(
            configmaa = conf_maa,
            date_envoi = datetime.datetime(2021,12,15,7,45),
            date_debut = datetime.datetime(2021,12,15,9,0),
            date_fin = datetime.datetime(2021,12,15,10,0),
            numero = 1,
            fcst="FCST",
            status = 'to_create',
            message = "Cors message",
            context_TAF = "context TaF",
            log = "Ici, les logs de création",
            message_mail = 'Corps du mail',
            message_sms = "message SMS",
        )
        envoi.save()
        envois = EnvoiMAA.objects.filter(configmaa__station__oaci = 'LFRH')
        print("envois LFRH avant analyse")
        print(envois)
        self.assertEqual(len(envois), 1)

        # maa_en_cours = EnvoiMAA.current_maas_by_type('LFRH', conf_maa.type_maa, heure_analyse, conf_maa.seuil)
        analyse_15mn(heure_analyse)

        # Malgré la présence d'un maa dans les fichiers cdp, pas de génération d'un nouveau maa car l'autre est encore en cours
        envois = EnvoiMAA.objects.filter(configmaa__station__oaci = 'LFRH')
        print("envois LFRH après analyse")
        print(envois)
        self.assertEqual(len(envois), 1)

    @patch("donneur.commons.request_data_cdp")
    def test_TC1_LFRB(self, mock_request_data_cdp):
        """
            TC permettant de tester le cas LFRB avec un déclenchement en oper de MAA Tmin du 170200/170700
            En réalité les températures entre 02 et 05 sont supérieur à 5 degrés. Mais en oper v1, ces températures
            sont arrondies à 5 degrés. 
            Ici, on n'a un déclenchement que sur la période 5-7TU. 
        """
        num_TC = '1'
        mock_request_data_cdp.side_effect=[
            self.get_data_tc(num_TC,'cdpaero'),
            self.get_data_tc(num_TC,'cdph'), 
            self.get_data_tc(num_TC,'cdpq'), 
            self.get_data_tc(num_TC,'cdphom'), 
            self.get_data_tc(num_TC,'cdpqom'),  
        ]
        
        #TODO: vérifier la bonne interogation des données Q en oper

        heure_analyse= datetime.datetime(2021,12,16,18,25)

        # S'assure qu'il n'y a pas déjà un MAA LFRB TMIN déjà en cours
        self.assertEqual(len(EnvoiMAA.objects.filter(configmaa__station__oaci = 'LFRB', configmaa__type_maa = 'TMIN', configmaa__seuil = 5.0)), 0)

        # S'assure qu'il y a bien une config TMIN à 5 degrés pour LFRB
        config = ConfigMAA.objects.get(station__oaci = 'LFRB', type_maa = 'TMIN', seuil = 5.0)
        
        analyse_15mn(heure_analyse)
        
        # S'assure que le MAA TMIN 5.0 a bien été trouvé durant l'analyse
        envois = EnvoiMAA.objects.filter(configmaa__station__oaci = 'LFRB', configmaa__type_maa = 'TMIN', configmaa__seuil = 5.0)
        self.assertEqual(len(envois), 1)

    @patch("donneur.commons.request_data_cdp")
    def test_TC1_LFQQ(self, mock_request_data_cdp):
        """
            Le 17/12, vers 10h36, production en oper v1 d'un MAA FG de 10:36 à 22TU pour LFQQ. 
            En test, MAA de 10TU à 21TU => pourquoi 10TU ? pourquoi 21TU
            Correction faite pour prendre comme date de début le max de heure_analyse - heure début
            Correction faite pour faire la recherche de la fin jusqu'à l'heure reseau_analyse + profondeur incluse 
        """
        num_TC = '1'
        mock_request_data_cdp.side_effect=[
            self.get_data_tc(num_TC,'cdpaero'),
            self.get_data_tc(num_TC,'cdph'), 
            self.get_data_tc(num_TC,'cdpq'), 
            self.get_data_tc(num_TC,'cdphom'), 
            self.get_data_tc(num_TC,'cdpqom'),  
        ]
        
        #TODO: vérifier la bonne interogation des données Q en oper

        heure_analyse= datetime.datetime(2021,12,17,10,36)

        # S'assure qu'il n'y a pas déjà un MAA LFQQ de FG déjà en cours
        self.assertEqual(len(EnvoiMAA.objects.filter(configmaa__station__oaci = 'LFQQ', configmaa__type_maa = 'FG')), 0)

        # S'assure qu'il y a bien une config FG pour LFQQ
        config = ConfigMAA.objects.get(station__oaci = 'LFQQ', type_maa = 'FG')
        
        analyse_15mn(heure_analyse)
        
        # S'assure que le MAA FG a bien été trouvé durant l'analyse
        envois = EnvoiMAA.objects.filter(configmaa__station__oaci = 'LFQQ', configmaa__type_maa = 'FG')
        self.assertEqual(len(envois), 1)

        #Vérifier les heures de début et de fin
        envoi = envois[0]
        self.assertEqual(envoi.date_debut, datetime.datetime(2021,12,17,10,36,0))
        self.assertEqual(envoi.date_fin, datetime.datetime(2021,12,17,22,0,0))
        
        

        





