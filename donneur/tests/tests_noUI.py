from pathlib import Path
from unittest.mock import patch
from datetime import datetime


from django.test import TestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings


from donneur.commons import retrieveDatasAero
from donneur.commons import retrieveDatasCDPH_metropole
from donneur.commons import retrieveDatasCDPH_om
from donneur.commons import AeroDataStations, CDPDataStations, ManagerData

from analyseur.commons import define_open_airport, provide_manager
from analyseur.production import create_data_vent, create_maa_auto

from configurateur.models import ConfigMAA, Station
from configurateur.initiate_toolbox.initiate_db_tools import Initiate

class RetrieveData_TestCase(TestCase, StaticLiveServerTestCase):

    @classmethod
    def setUpTestData(cls):
        # Insertion en base des données initiales. Permet d'avoir une liste des stations aéro
        init = Initiate() # Par défaut charge la base de test ficitve
        init.create_all_base_test()

    def setUp(self):
        """ Executée à chaque lancement d'une fonction test_ de cette classe 
        """
        super().setUp()
        settings.RUNNING_SERVER = self.live_server_url

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
        
        raise KeyError("Imposible de trouver le fichier {} du TC{}".format(fichier, num_TC))

    @patch("donneur.commons.request_data_cdp")
    def test_retrieve_datas(self, mock_request_data_cdp):
            """ Test l'importation des données issues du cdp aéro 
                On ne se concentre pas sur les données, juste le nombre de lignes insérées
            """

            # Test une récupération des données via les SA CDP simulés par le TC1
            mock_request_data_cdp.side_effect=[
                self.get_data_tc('1','cdpaero'), 
            ]
            aeros = retrieveDatasAero([     ('LFPG', '9552761', False), 
                                            ('LFPO', '9405461', False),
                                            ('TFFR', '9710101', True),
                                            ('LFSB', '6829761', False),])
            
            datas = AeroDataStations()
            datas.load_datas(aeros)

            # récupère une ligne d'info
            TFFR = datas.getStation('TFFR')
            self.assertEqual(len(TFFR.echeances), 1)
            
            LFPO = datas.getStation('LFPO')
            self.assertEqual(len(LFPO.echeances), 1)

            LFPG = datas.getStation('LFPG')
            self.assertEqual(len(LFPG.echeances), 1)
            
            LFSB = datas.getStation('LFSB')
            self.assertEqual(len(LFSB.echeances), 0)

    @patch("donneur.commons.request_data_cdp")
    def test_report_becmg_tempo(self, mock_request_data_cdp):
            """ Test si le report des becmg tempo... sont bien pris en compte 
                Voir le readme.txt pour plus de détails
            """
        
            # Test une récupération des données via les SA CDP simulés par le TC1
            num_TC = '2'
            mock_request_data_cdp.side_effect=[
                self.get_data_tc(num_TC,'cdpaero'), 
            ]

            stations = Station.objects.all().values_list('oaci', 'inseepp', 'outremer')
            
            aeros = retrieveDatasAero(stations)
            datas = AeroDataStations()
            datas.load_datas(aeros)

            # récupère une ligne d'info
            station = datas.getStation('DDDD')
            echeances = [datetime(2021,11,12,6,0,0),datetime(2021,11,12,7,0,0),datetime(2021,11,12,8,0,0),datetime(2021,11,12,9,0,0),]
            ww  = [ station.echeances[echeance].get_WW() for echeance in echeances]
            self.assertEqual([['RADZ'],['RADZ'],['RADZ'],['RADZ']], ww) # Test TEMPO N/M => report WW à M inclus

            echeances = [datetime(2021,11,12,10,0,0),datetime(2021,11,12,11,0,0),datetime(2021,11,12,12,0,0)]
            ww  = [ station.echeances[echeance].get_WW() for echeance in echeances]
            self.assertEqual([['SHRA'],['SHRA'],['SHRA'],], ww) # Test PROB40 TEMPO N/M => report WW à M inclus
            
            station = datas.getStation('EEEE')
            echeances = [datetime(2021,11,12,20,0,0),datetime(2021,11,12,21,0,0),datetime(2021,11,12,22,0,0)]
            ww  = [ station.echeances[echeance].get_WW() for echeance in echeances]
            self.assertEqual([['FG'],['FG'],['FG'],], ww) # Test BECMG N/M => WW dès N 
            
            station = datas.getStation('FFFF')
            echeances = [datetime(2021,11,12,19,0,0)]
            ww  = [ station.echeances[echeance].get_WW() for echeance in echeances]
            self.assertEqual([['FG','FZFG','RADZ']], ww) # Test Si FZFG => ajoute FG (cf LFBI)

            station = datas.getStation('GGGG')
            echeances = [datetime(2021,11,12,20,0,0)]
            ww  = [ station.echeances[echeance].get_WW() for echeance in echeances]
            self.assertEqual([['BR', 'GR','GS']], ww) # Test Si GR => ajoute GS (cf LFCR)

            station = datas.getStation('EEEE')
            echeances = [datetime(2021,11,12,11,0,0),datetime(2021,11,12,12,0,0)]
            ww  = [ station.echeances[echeance].VVmin for echeance in echeances]
            self.assertEqual([400, 10000], ww) # Test visi BECMG N/M => report phéno précédent jusqu'à M inclus (cf LFBE)

            station = datas.getStation('HHHH')
            echeances = [ datetime(2021,11,12,6,0,0),datetime(2021,11,12,7,0,0),datetime(2021,11,12,8,0,0), datetime(2021,11,12,9,0,0)]
            ww  = [ station.echeances[echeance].VVmin for echeance in echeances]
            self.assertEqual([150, 150, 150, 400], ww) # Test visi TEMPO N/M => report de la visi jusqu'à M inclus (cl LFOB)

            station = datas.getStation('IIII')
            echeances = [ datetime(2021,11,12,6,0,0),datetime(2021,11,12,7,0,0),datetime(2021,11,12,8,0,0), datetime(2021,11,12,9,0,0), datetime(2021,11,12,10,0,0)]
            ww  = [ station.echeances[echeance].VVmin for echeance in echeances]
            self.assertEqual([1500, 1500, 1500, 1500, 3000], ww) # Test visi PROB40 TEMPO N/M => report de la visi jusqu'à M inclus (cl LFRD)
            
            station = datas.getStation('IIII')
            echeances = [ datetime(2021,11,12,11,0,0),datetime(2021,11,12,12,0,0),datetime(2021,11,12,13,0,0), datetime(2021,11,12,14,0,0), datetime(2021,11,12,15,0,0)]
            ww  = [ station.echeances[echeance].FF for echeance in echeances]
            self.assertEqual([15, 15, 15, 15, 12], ww) # Test vent PROB40 TEMPO N/M => report du FF jusqu'à M inclus (cl LFRD)
            ww  = [ station.echeances[echeance].FX for echeance in echeances]
            self.assertEqual([25, 25, 25, 25, 12], ww) # Test vent PROB40 TEMPO N/M => report du FX jusqu'à M inclus (cl LFRD)

            station = datas.getStation('JJJJ')
            echeances = [ datetime(2021,11,12,6,0,0),datetime(2021,11,12,18,0,0),datetime(2021,11,12,19,0,0)]
            ww  = [ station.echeances[echeance].FF for echeance in echeances]
            self.assertEqual([15, 15, 10], ww) # Test vent TEMPO N/M => report du FF jusqu'à M inclus (cl LFTH)
            ww  = [ station.echeances[echeance].FX for echeance in echeances]
            self.assertEqual([30, 30, 10], ww) # Test vent TEMPO N/M => report du FX jusqu'à M inclus (cl LFTH)

            station = datas.getStation('LFPG')
            echeances = [ datetime(2021,12,4,6,0,0),datetime(2021,12,4,7,0,0)]
            ww  = [ station.echeances[echeance].FX for echeance in echeances]
            self.assertEqual([30, 12], ww) # On a 30kt en tempo jusqu'à 06TU. Une autre station devrait pousser le 30kt jusqu'à 07TU. Mais pas pour LFPG
            #Pour LFPG : TEMPO N/M, déja FX reporté à M dans le CDP aéro => pas de report du FX à M+1
            
    @patch("donneur.commons.request_data_cdp")
    def test_retrieve_datas_CDPH(self, mock_request_data_cdp):
        """ Test le décryptage des données issues du cdp h """
        
        # Test une récupération des données via les SA CDP simulés par le TC1
        TC='3'
        mock_request_data_cdp.side_effect=[
            self.get_data_tc(TC,'cdph'), 
            self.get_data_tc(TC,'cdphom'),  
        ]

        stations = Station.objects.all().values_list('oaci', 'inseepp', 'outremer')
        cdph = retrieveDatasCDPH_metropole( [(oaci, insee) for oaci, insee, om in stations if not om])
        cdph_om = retrieveDatasCDPH_om( [(oaci, insee) for oaci, insee, om in stations if om])

        datas = CDPDataStations()
        datas.load_datas(cdph, False)
        datas.load_datas(cdph_om, True)
        
        # récupère une ligne d'info
        station = datas.getStation('AAAA')
        heure = station.get_echeance(datetime(2021,11,12,10,0,0))
        self.assertEqual(heure.get_param('t'), 2.5000) #2.5000;
        self.assertEqual(heure.get_param('ff'), 10) #9.71920;
        self.assertEqual(heure.get_param('fx'), 10) #0.00000;
        self.assertEqual(heure.get_param('ww'), ['FG']) #1;
        self.assertEqual(heure.get_param('rr1'), 0) #0.0000;
        self.assertEqual(heure.get_param('rr3'), 0) #0.0000;
        self.assertEqual(heure.get_param('rr6'), 0) #0.0000;
        self.assertEqual(heure.get_param('rr12'), 0) #0.0000;
        self.assertEqual(heure.get_param('rr24'), 1) #1.0000;
        self.assertEqual(heure.get_param('etatsol'), 0) #0;
        self.assertEqual(heure.get_param('pneige'), 0) #0.0000;
        self.assertEqual(heure.get_param('dd'), 160) #160;

        station = datas.getStation('CCCC')
        heure = station.get_echeance(datetime(2021,11,12,12,0,0))
        self.assertEqual(heure.get_param('t'), 27.3) #27.3000;
        self.assertEqual(heure.get_param('ff'), 4) #3.88768;
        self.assertEqual(heure.get_param('fx'), 4) #0.00000;
        self.assertEqual(heure.get_param('ww'), ['RA']) #18;
        self.assertEqual(heure.get_param('etatsol'), -999) #-999;
        self.assertEqual(heure.get_param('rr1'), 0.33) #2.0000;
        self.assertEqual(heure.get_param('rr3'), 1.0) #2.0000;
        self.assertEqual(heure.get_param('rr6'), 2) #2.0000;
        self.assertEqual(heure.get_param('rr12'), 4) #2.0000;
        self.assertEqual(heure.get_param('dd'), 55) #55;
    
    def batterie_tests(self, manager, echeance, oaci):
        """ Permet de tester tous les types de MAA sur l'écheance et la station données.

            Pour les cumuls, les seuils sont pris à 50mm
            Pour les vents, le seuil est de 50 kt
            Pour les températures, les seuils sont <-1 et >30 
        
            Retourne une liste ordonnée des types ayant déclenchés
        """
        positif = []
        if manager.question_declenche(oaci, echeance, 'VENT', 50): positif.append('VENT')
        if manager.question_declenche(oaci, echeance, 'VENT_MOY', 50): positif.append('VENT_MOY')
        if manager.question_declenche(oaci, echeance, 'TMIN', -1): positif.append('TMIN')
        if manager.question_declenche(oaci, echeance, 'TMAX', 30): positif.append('TMAX')
        if manager.question_declenche(oaci, echeance, 'RR1', 50): positif.append('RR1')
        if manager.question_declenche(oaci, echeance, 'RR3', 50): positif.append('RR3')
        if manager.question_declenche(oaci, echeance, 'RR6', 50): positif.append('RR6')
        if manager.question_declenche(oaci, echeance, 'RR12', 50): positif.append('RR12')
        if manager.question_declenche(oaci, echeance, 'RR24', 50): positif.append('RR24')
        if manager.question_declenche(oaci, echeance, 'TS') : positif.append('TS')
        if manager.question_declenche(oaci, echeance, 'GR'): positif.append('GR')
        if manager.question_declenche(oaci, echeance, 'SQ'): positif.append('SQ')
        if manager.question_declenche(oaci, echeance, 'FG'): positif.append('FG')
        if manager.question_declenche(oaci, echeance, 'FZRA'): positif.append('FZRA')
        if manager.question_declenche(oaci, echeance, 'FZFG'): positif.append('FZFG')
        if manager.question_declenche(oaci, echeance, 'FZDZ'): positif.append('FZDZ')
        if manager.question_declenche(oaci, echeance, 'DENSE_FG'): positif.append('DENSE_FG')

        return sorted(positif)
    
    @patch("donneur.commons.request_data_cdp")
    def test_assembleur(self, mock_request_data_cdp):
        """ Test la classe qui assemble les données issus des cdp """
        
        # Récupération des données via les SA CDP simulés par le TC1
        num_TC = '4'
        mock_request_data_cdp.side_effect=[
            self.get_data_tc(num_TC,'cdpaero'),
            self.get_data_tc(num_TC,'cdph'), 
            self.get_data_tc(num_TC,'cdpq'),  
        ]
        
        stations = [('EEEE', '5555555', False)]
        
        aeros = retrieveDatasAero(stations)
        datas_aero = AeroDataStations()
        datas_aero.load_datas(aeros)

        cdph = retrieveDatasCDPH_metropole( [(oaci, insee) for oaci, insee, om in stations if not om])
        datas = CDPDataStations()
        datas.load_datas(cdph, False)
        
        
        # Chargement dans l'assembleur. C'est lui qui va répondre au tests. 
        assembleur = ManagerData(datas_aero, datas)
        
        self.assertEqual( self.batterie_tests(assembleur, datetime(2021,11,11,0,0,0), 'EEEE'), [])
        self.assertEqual( self.batterie_tests(assembleur, datetime(2021,11,11,1,0,0), 'EEEE'), ['TS', 'VENT', 'VENT_MOY'])
        self.assertEqual( assembleur.question_declenche('EEEE', datetime(2021,11,11,1,0,0), 'TS', ''), True)
        self.assertEqual( self.batterie_tests(assembleur, datetime(2021,11,11,2,0,0), 'EEEE'), ['GR', 'VENT', 'VENT_MOY'])
        self.assertEqual( self.batterie_tests(assembleur, datetime(2021,11,11,3,0,0), 'EEEE'), ['FG', 'FZDZ', 'FZRA', 'SQ'])
        self.assertEqual( self.batterie_tests(assembleur, datetime(2021,11,11,4,0,0), 'EEEE'), ['FG','FZFG', 'VENT'])
        self.assertEqual( self.batterie_tests(assembleur, datetime(2021,11,11,5,0,0), 'EEEE'), ['DENSE_FG', 'FG'])
        self.assertEqual( self.batterie_tests(assembleur, datetime(2021,11,11,6,0,0), 'EEEE'), ['TMIN'])
        self.assertEqual( self.batterie_tests(assembleur, datetime(2021,11,11,7,0,0), 'EEEE'), ['TMAX'])
        self.assertEqual( self.batterie_tests(assembleur, datetime(2021,11,11,8,0,0), 'EEEE'), ['RR24'])
        self.assertEqual( self.batterie_tests(assembleur, datetime(2021,11,11,9,0,0), 'EEEE'), ['RR1', 'RR12', 'RR24', 'RR3', 'RR6'])
        self.assertEqual( self.batterie_tests(assembleur, datetime(2021,11,11,10,0,0), 'EEEE'), [])
        # A partir de là, c'est le cdp qui prend le relai
        self.assertEqual( self.batterie_tests(assembleur, datetime(2021,11,11,11,0,0), 'EEEE'), ['TS', 'VENT', 'VENT_MOY']) 
        self.assertEqual( self.batterie_tests(assembleur, datetime(2021,11,11,12,0,0), 'EEEE'), ['GR'])
        self.assertEqual( self.batterie_tests(assembleur, datetime(2021,11,11,13,0,0), 'EEEE'), ['FG', 'FZFG'])
        self.assertEqual( self.batterie_tests(assembleur, datetime(2021,11,11,14,0,0), 'EEEE'), ['FZRA'])
        self.assertEqual( self.batterie_tests(assembleur, datetime(2021,11,11,15,0,0), 'EEEE'), ['FG'])
    
    @patch("donneur.commons.request_data_cdp")
    def test_ventillation_textreme_metropole(self, mock_request_data_cdp):

        # Récupération des données via les SA CDP simulés par le TC1
        num_TC = '5'
        mock_request_data_cdp.side_effect=[
            self.get_data_tc(num_TC,'cdpaero'),
            self.get_data_tc(num_TC,'cdph'), 
            self.get_data_tc(num_TC,'cdpq'), 
            self.get_data_tc(num_TC,'cdphom'), 
            self.get_data_tc(num_TC,'cdpqom'),  
        ]

        heure_analyse = datetime(2021,11,11,5,0,0)
        stations = define_open_airport(heure_analyse)# Met le souk dans les mock si appelé en premier !?

        manager_cdp = provide_manager(stations)

        # Vérifie si le chargement est bon pour le tn
        self.assertEqual( manager_cdp.get_tempe('AAAA', datetime(2021,11,11,3,0,0)), 5)
        self.assertEqual( manager_cdp.get_tempe('AAAA', datetime(2021,11,11,12,0,0)), -1)
        
        tn_extreme = manager_cdp.cdp.getStation('AAAA').get_echeance(datetime(2021,11,11,12,0,0)).get_param('tn_extreme')
        self.assertEqual(tn_extreme, -4)
        
        self.assertEqual(manager_cdp.question_declenche('AAAA', datetime(2021,11,11,12,0,0),'TMIN', -2),
                         True) # Ne déclencherait pas juste avec le -1 du cdph
        self.assertEqual(manager_cdp.question_declenche('AAAA', datetime(2021,11,11,12,0,0),'TMIN', -6),
                         False) # Montre qu'avec un seuil plus bas que le -5 de l'heure, on déclenche

        # Vérifie si le chargement est bon pour le tx
        self.assertEqual( manager_cdp.get_tempe('AAAA', datetime(2021,11,11,11,0,0)), 8)
        
        tx_extreme = manager_cdp.cdp.getStation('AAAA').get_echeance(datetime(2021,11,11,11,0,0)).get_param('tx_extreme')
        self.assertEqual(tx_extreme, 13)
        
        self.assertEqual(manager_cdp.question_declenche('AAAA', datetime(2021,11,11,11,0,0),'TMAX', 10),
                         True) # Ne déclencherait pas juste avec le 8 du cdph
        self.assertEqual(manager_cdp.question_declenche('AAAA', datetime(2021,11,11,11,0,0),'TMAX', 16),
                         False) # Montre qu'avec un seuil plus bas que le 16 de l'heure, on déclenche
        
    @patch("donneur.commons.request_data_cdp")
    def test_vent_variable(self, mock_request_data_cdp):
        """" Test la création d'un MAA avec un paramètre vent générant un PDF avec graphique vent """
        num_TC = '6'
        mock_request_data_cdp.side_effect=[
            self.get_data_tc(num_TC,'cdpaero'),
            self.get_data_tc(num_TC,'cdph'), 
            self.get_data_tc(num_TC,'cdpq'), 
            self.get_data_tc(num_TC,'cdphom'), 
            self.get_data_tc(num_TC,'cdpqom'),  
        ]

        heure_analyse = datetime(2021,12,1,20,0,0)
        stations = define_open_airport(heure_analyse)
        manager_cdp = provide_manager(stations)

        # 1111111;0;2021-12-01 22:00:00;AAAA;2021-12-01 17:00:00;9999;;;3000;998;;;;2;;;;;;;;;;;BR;
        vent_00TU = manager_cdp.get_vent('AAAA', datetime(2021,12,2,0,0,0))
        self.assertEqual(vent_00TU, (2,2,998)) # Le vent variable est pris à 998.

        # Vérifie qu'on a bien une création de data_vent non nul si MAA de type vent
        configmaa = ConfigMAA.objects.get(station__oaci ='AAAA', type_maa = 'VENT')
        data_vent = create_data_vent(manager_cdp, configmaa ,heure_analyse)
        self.assertNotEqual(data_vent, '')

        create_maa_auto('Test de MAA vent avec data vent', manager_cdp, configmaa, heure_analyse, heure_analyse, heure_analyse)
        
        # Nota : Doit retrouver le pdf associer dans /media/upload/MM/JJ ave cun graphique
        #print(data_vent)
    
