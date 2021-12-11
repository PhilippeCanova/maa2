import datetime, time
from unittest.mock import patch

from django.test import TestCase
from django.test import LiveServerTestCase, RequestFactory
from django.contrib.auth.models import User, Group, Permission

from configurateur.models import AutorisedMAAs, Region, Station, ConfigMAA

# Create your tests here.
class ConfigurateurTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        """ Utlisé pour une utilisation commune à toutes les fonctions test de cette classe 
            mais lancé une seule fois """
        from maa_django.apps.core.management.commands.initiate import Initiate
        super().setUpClass()
        init = Initiate()
        init.create()

    def retrieve_infos_changement_heure_station(self, oaci):
        """ Récupère les informations de changement d'heure d'une station """
        from configurateur.models import Station
        station = Station.objects.get(oaci=oaci)
        return station.date_pivot, station.ouverture, station.fermeture

    @patch("configurateur.utils.retrieve_utcnow")
    def testChangeDatePivot(self, mock_retrieve_utcnow):
        from configurateur.utils import retrieve_pivot, chek_and_change_pivot_date
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
        date_pivot, ouverture, fermeture = self.retrieve_infos_changement_heure_station('LFAQ')
        self.assertEqual(date_pivot, datetime.datetime(2021,10,31,1,0,0,0))
        self.assertEqual(ouverture, datetime.time(6,0,0))
        self.assertEqual(fermeture, datetime.time(17,15,0))

        # Deuxième cas, juste avant le changement d'heure, pas de changement d'heure par rapport à la config de la base qui est sur l'heure d'été
        # Donc doit retrouver les heures ouverture et fermeture d'été
        mock_retrieve_utcnow.return_value = datetime.datetime(2021,10,31,1,0,0,0) # Simule la date de lancement
        chek_and_change_pivot_date()
        date_pivot, ouverture, fermeture = self.retrieve_infos_changement_heure_station('LFAQ')
        self.assertEqual(date_pivot, datetime.datetime(2021,10,31,1,0,0))
        self.assertEqual(ouverture, datetime.time(6,0,0))
        self.assertEqual(fermeture, datetime.time(17,15,0))

        # Troisième cas, on passe la date pivot pour le changement en heure d'hiver 
        # Donc doit retrouver les heures ouverture et fermeture d'hiver
        mock_retrieve_utcnow.return_value = datetime.datetime(2021,10,31,1,5,0,0) # Simule la date de lancement
        chek_and_change_pivot_date()
        date_pivot, ouverture, fermeture = self.retrieve_infos_changement_heure_station('LFAQ')
        self.assertEqual(date_pivot, datetime.datetime(2022,3,27,1,0,0))
        self.assertEqual(ouverture, datetime.time(7,0,0))
        self.assertEqual(fermeture, datetime.time(18,15,0))

        # Quatrième cas, on change d'année, pas de changements, on reste en heure d'hiver 
        # Donc doit retrouver les heures ouverture et fermeture d'hiver
        mock_retrieve_utcnow.return_value = datetime.datetime(2022,1,2,0,0,0,0) # Simule la date de lancement
        chek_and_change_pivot_date()
        date_pivot, ouverture, fermeture = self.retrieve_infos_changement_heure_station('LFAQ')
        self.assertEqual(date_pivot, datetime.datetime(2022,3,27,1,0,0))
        self.assertEqual(ouverture, datetime.time(7,0,0))
        self.assertEqual(fermeture, datetime.time(18,15,0))

        # Cinquième cas, on change repasse en heure d'été car on passe le change d'heure de mars
        # Donc doit retrouver les heures ouverture et fermeture d'été
        mock_retrieve_utcnow.return_value = datetime.datetime(2022,3,27,1,5,0,0) # Simule la date de lancement
        chek_and_change_pivot_date()
        date_pivot, ouverture, fermeture = self.retrieve_infos_changement_heure_station('LFAQ')
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
        init.create_region()
        init.create_group_and_permissions()
        init.create_users()
        init.create_stations()
        init.create_full_configmaa()
        
    def test_import_for_test(self):
        """ Test une itialisation complète à partir des données de test (box_test) """

        #Check régions
        self.assertEqual(len(Region.objects.all()), 3)

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
        

        





