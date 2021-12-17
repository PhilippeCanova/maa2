from pathlib import Path
import datetime
import time
import csv
import xml.etree.ElementTree as ET

from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.core import serializers

from maa_django.apps.core.models import Log
from analyseur.models import EnvoiMAA
from profiles.models import Profile
from configurateur.models import Region, Station, ConfigMAA, AutorisedMAAs
from configurateur.models import Client, MediumMail, MediumFax, MediumFTP, MediumSMS


class ConfigClients(object):
    def __init__(self, fichier):
        """ Sérialize une Informationc Client à partir d'une ligne de la base MySQL """
        self.clients = {}
        with open(fichier, 'r') as ficin:
            entetes = ficin.readline()
            entetes = entetes.split(';')
                
            for ligne in ficin.readlines():
                client = {}
                infos = ligne.split(';')
                for index, val in enumerate(infos):
                    client[entetes[index].strip()] = val.strip()
                self.clients[client['id']]= client

class ConfigClientProduit(object):
    def __init__(self, fichier):
        """ Sérialize une information Client-Produit à partir d'une ligne de la base MySQL """
        self.client_prod = {}
        with open(fichier, 'r') as ficin:
            entetes = ficin.readline().strip()
            entetes = entetes.split(';')

            for ligne in ficin.readlines():
                instance = {}
                instance['mails'] = []
                instance['smss'] = []
                instance['ftps'] = []
                instance['faxs'] = []
                instance['type_maa'] = []
                
                infos = ligne.split(';')
                for index, val in enumerate(infos):
                    champs = entetes[index].strip()
                    if champs in ['id_client', 'nom_produit', 'date_fin', 'station', 'params', 'actif']:
                        instance[champs] = val.strip()

                if instance['nom_produit'] == 'maa':
                    date_fin = datetime.datetime.strptime(instance['date_fin'], "%Y-%m-%d %H:%M:%S")
                    if date_fin < datetime.datetime.utcnow(): # Abonnement terminé, on ne le prend pas
                        continue

                    # Extrait les infos params
                    try:
                        params  = instance['params'][10:]
                        params = params.split('\\n\\n')
                        for param in params:
                            str_param = param[1:-1].replace('\\n', '')

                            root = ET.fromstring(str_param)
                            station = root.find('station')
                            if station is not None:
                                instance['station'] = station.get('id')
                                params = root.find('params')
                                for type_param in params.attrib:
                                    instance['type_maa'].append(type_param)

                            mails = root.find('mail')
                            if mails is not None:
                                for dmail in mails.findall('dests'):
                                    for mail in dmail.findall('dest'):
                                        instance['mails'].append(mail.text)

                            smss = root.find('sms')
                            if smss is not None:
                                for dsms in smss.findall('dests'):
                                    for sms in dsms.findall('dest'):
                                        instance['smss'].append(sms.text)
                            
                            ftps = root.find('ftp')
                            if ftps is not None:
                                for dftp in ftps.findall('dests'):
                                    for ftp in dftp.findall('dest'):
                                        host = ftp.find('host')
                                        user = ftp.find('user')
                                        passwd = ftp.find('passwd')
                                        path = ftp.find('path')
                                        passive = ftp.find('passive')
                                        instance['ftps'].append( {'host': host.text,
                                                                  'user': user.text,
                                                                  'passwd': passwd.text,
                                                                  'path': path.text,
                                                                  'passive': passive.text})
                            
                            faxs = root.find('fax')
                            if faxs is not None:
                                for dfax in faxs.findall('dests'):
                                    for fax in dfax.findall('dest'):
                                        instance['faxs'].append(fax.text)

                        id_client = instance['id_client']
                        if id_client not in self.client_prod.keys():
                            self.client_prod[id_client] = []
                        self.client_prod[id_client].append(instance)

                    except Exception as e:
                        print (e)
                    
class ConfigStation(object):
        def __init__(self, entetes, ligne) -> None:
            super().__init__()
            infos = ligne.split('\t')
            for index, val in enumerate(infos):
                self.__dict__[entetes[index].strip()] = val.strip()
            self.outremer = False
            self.active = True

        def serialize_v2(self):
            """ Permet de retrouner la config sous forme d'une config v2 """
            rep = []
            rep.append(self.station)
            rep.append(self.nom)
            rep.append(self.entete)
            rep.append(datetime.datetime.strftime(self.date_pivot, "%Y-%m-%d %H:%M:%S"))
            rep.append(self.dir)
            rep.append(self.inseepp)
            rep.append(str(self.outremer))
            rep.append(str(self.active))
            rep.append(datetime.datetime.strftime(self.ouverture,"%H:%M"))
            rep.append(datetime.datetime.strftime(self.fermeture,"%H:%M"))
            rep.append(self.retention)
            rep.append(self.reconduction)
            rep.append(self.delta_debut_repousse)
            rep.append(self.unite_vent)
            rep.append(self.fuseau)
            rep.append(self.ouverture2)
            rep.append(self.fermeture2)
            rep.append(self.ouverture1)
            rep.append(self.fermeture1)
            rep.append(self.inseeaero)
            
            return ";".join(rep)

class ConfigsStation(object):
        def __init__(self, fichier) -> None:
            """ Charge les config du fichier"""
            super().__init__()
            self.stations = {}
            with open(fichier, 'r') as ficin:
                entetes = ficin.readline()
                entetes = entetes.split('\t')

                for ligne in ficin.readlines():
                    config = ConfigStation(entetes, ligne)
                    config.date_pivot = datetime.datetime.strptime(config.date_pivot, "%Y-%m-%d %H:%M:%S")
                    config.ouverture = datetime.datetime.strptime(config.ouverture, "%H:%M")
                    config.ouverture_ete = datetime.datetime.strptime(config.ouverture1, "%H:%M")
                    config.ouverture_hiver = datetime.datetime.strptime(config.ouverture2, "%H:%M")
                    if config.fermeture == '24:00': config.fermeture = '23:59'
                    if config.fermeture1 == '24:00': config.fermeture1 = '23:59'
                    if config.fermeture2 == '24:00': config.fermeture2 = '23:59'
                    config.fermeture = datetime.datetime.strptime(config.fermeture, "%H:%M")
                    config.fermeture_ete = datetime.datetime.strptime(config.fermeture1, "%H:%M")
                    config.fermeture_hiver = datetime.datetime.strptime(config.fermeture2, "%H:%M")
                    self.stations[config.station] = config

        def get_liste_stations(self):
            return sorted(list(self.stations.keys()))

        def get_station(self, tag):
            return self.stations.get(tag, None)

        def get_dirs(self):
            """ Récupérer un set avec toutes les dirs apparaissant dans les configs"""
            regions = []
            for config in self.stations.values():
                regions.append(config.dir)
            return set(regions)
        
        def add_inseepp(self, correspondance, correspondance_aero):
            """ A partir du dictionnaire correspondance {oaci, inseepp}, j'ajoute l'insee aux config station """
            for oaci, station in self.stations.items():
                inseepp = correspondance.get(oaci, None)
                inseeaero = correspondance_aero.get(oaci, None)
                
                if inseepp is None or inseeaero is None:
                    print("Pas de correspondance Inseepp pour " + oaci)
                else:
                    station.inseepp = inseepp
                    station.inseeaero = inseeaero
                    
                    if inseepp[:2] > '95':
                        station.outremer = True

class ConfMAA(object):
    def __init__(self, configsStation, ligne) -> None:
        """ Convertit le fichier de config maa v1 en objet ConfMAA"""
        super().__init__()
        infos = ligne.split('\t')
        #id		station	type		seuil	deroule		next_run			auto	pause
        #3260	FMEE	TS			1					2021-08-19 06:16:28	1		2
        self.station = infos[1]
        self.type_maa = infos[2]
        self.seuil = float(infos[3])
        self.auto = infos[6]=='1'
        self.pause = int(infos[7])
        try:
            self.scan = configsStation[self.station].__dict__['scan_'+self.type_maa]
            self.profondeur =  configsStation[self.station].__dict__['duree_'+self.type_maa ]
        except:
            pass
    
    def serialize_to_v2(self):
        """ Permet de formater la ligne allant dans liste_maas.csv """
        # oaci;type;seuil;auto;pause;scan;profondeur
        default_config = AutorisedMAAs.get_instance(self.type_maa)
        if default_config is None:
            print("Le type de MAA {} n'est pas reconnu.".format(self.type_maa))
            return ""
        
        rep = [] #TODO: convertir les seuils 1 pour les occurrences en champ vide
        rep.append(self.station)
        rep.append(self.type_maa)
        seuil = str(self.seuil)
        if AutorisedMAAs.is_occurrence(self.type_maa):
            seuil=""
        rep.append(seuil)
        rep.append(str(self.auto))
        rep.append(str(self.pause))
        rep.append(str(self.scan))
        rep.append(str(self.profondeur))
        return ";".join(rep)

    def __str__(self):
        reponse = [ "{}: {}".format(key, value) for key, value in self.__dict__.items()]
        return "\n".join(reponse)

    @staticmethod
    def loadConfigs(fichier, configsStation):
        reponse = []
        with open(fichier, 'r') as ficin:
            ficin.readline()
            for ligne in ficin.readlines():
                if ligne.strip() != "":
                    config = ConfMAA(configsStation, ligne)
                    if config.station in configsStation.keys():
                        reponse.append(config)
        return reponse

class Initiate(object):
    """ Cette classe permet de préparer la base de donnée en fonction des besoins :
            - initialisation de la base oper lors de la migration ou des tests d'intégration
            - lancement des tests

        Les outils principaux sont découpés comme suit :
            - une fonciton delete qui remet à zéro la base. 
            - ... à détailler ...
    """
    @staticmethod
    def convert_v1_to_v2():
        """" Permet de charger la config depuis les fichiers v1 pour en faire un set de config v2 """

        # Répertoires de données
        rep = Path(__file__).parent
        v1 = rep.joinpath('v1')
        oper = rep.joinpath('box_oper')

        print ('Lecture de la config v1')
        correspondance_oaci_insee = Initiate.set_correspondance_oaci_inseepp(v1.joinpath("correspondanceMAA.csv"))
        correspondance_oaci_inseeaero = Initiate.set_correspondance_oaci_inseeaero(v1.joinpath("correspondanceMAA.csv"))
        
        station_v1 = ConfigsStation(v1.joinpath('config_station.csv'))
        station_v1.add_inseepp(correspondance_oaci_insee, correspondance_oaci_inseeaero)

        print ('Création des régions')
        regions = station_v1.get_dirs()
        with open(oper.joinpath('liste_regions.csv'), 'w') as ficout:
            for region in regions:
                ficout.write(region + "\n")
        
        print('création de la config Stations')
        entetes = "oaci;nom;entete;date_pivot;region__tag;inseepp;outremer;active;ouverture;fermeture;retention;reconduction;repousse;wint_unit;fuseau;ouverture_hiver;fermeture_hiver;ouverture_ete;fermeture_ete;inseeaero"
        with open(oper.joinpath('liste_stations.csv'), 'w') as ficout:
            ficout.write(entetes + "\n")
            for oaci in station_v1.get_liste_stations():
                config1 = station_v1.get_station(oaci)
                ficout.write(config1.serialize_v2() + "\n")
        
        print("Création des config MAA")
        entetes= "oaci;type;seuil;auto;pause;scan;profondeur\n"
        fichier = v1.joinpath('table config_maa.csv')
        configs_maa = ConfMAA.loadConfigs(fichier, station_v1.stations) #TODO: pas belle adhérence à stations...
        with open(oper.joinpath('liste_maas.csv'), 'w') as ficout:
            ficout.write(entetes)
            for config in configs_maa:
                ficout.write(config.serialize_to_v2() + "\n")

        print("Création des clients")
        fichier = v1.joinpath('client.csv')
        clients = ConfigClients(fichier)

        print("Création des client-produt")
        fichier = v1.joinpath('client_produit.csv')
        clients_produits = ConfigClientProduit(fichier)

        for id_client, produits in clients_produits.client_prod.items():
            print("Client : ", id_client)
            for instance in produits:
                print ("Station", instance['station'])
                print ("type_maa", instance['type_maa'])
                print ("FTPs", instance['ftps'])
                print ("Mails", instance['mails'])
                print ("SMSs", instance['smss'])
                print ("Faxs", instance['faxs'])

        """ Forme du modèle client
        nom = models.CharField(max_length= 250, null=False)
        prenom = models.CharField(max_length= 250, null=True, blank=True)
        telephone = models.CharField(max_length= 15, null=False)
        email = models.EmailField(max_length= 250, null=True, blank=True)
        configmaas"""

        print("TODO: implémenter la récupération les clients et médiums. Prendre config MetservicesPlus ?")

    @staticmethod   
    def set_correspondance_oaci_inseepp(fichier):
        """ Retourne un dictionnaire {oaci:insepp} lue à partir du fichier de correspondance """
        correspondance = {}
        with open(fichier, 'r') as ficin:
            ficin.readline() # Skip première ligne
            for ligne in ficin.readlines():
                infos = ligne.split(';')
                correspondance[infos[1].strip()] = infos[0]
        return correspondance
    
    @staticmethod   
    def set_correspondance_oaci_inseeaero(fichier):
        """ Retourne un dictionnaire {oaci:inseeaero} lue à partir du fichier de correspondance """
        correspondance = {}

        with open(fichier, 'r') as ficin:
            ficin.readline() # Skip première ligne
            for ligne in ficin.readlines():
                print(ligne)
                infos = ligne.split(';')
                correspondance[infos[1].strip()] = infos[2].strip()
        return correspondance

    def delete(self):
        # Suppression des régions existantes
        regions = Region.objects.all()
        for region in regions:
            region.delete()
        
        # Suppression des stations existantes
        stations = Station.objects.all()
        for station in stations:
            station.delete()

        # Création des groupes et permission
        groups = Group.objects.all()
        for group in groups:
            group.delete()
        
        # Charge les configs MAA depuis le fichier de confgi
        configsMAA = ConfigMAA.objects.all()
        for conf in configsMAA:
            conf.delete()

        # implémente quelques envois de MAA
        envois = EnvoiMAA.objects.all()
        for envoi in envois:
            envoi.delete()

        clients = Client.objects.all()
        for client in clients:
            client.delete()

        mails = MediumMail.objects.all()
        for mail in mails:
            mail.delete()

        smss = MediumSMS.objects.all()
        for sms in smss:
            sms.delete()

        ftps = MediumFTP.objects.all()
        for ftp in ftps:
            ftp.delete()

        faxs = MediumFax.objects.all()
        for fax in faxs:
            fax.delete()

        # Création des profils
        users = User.objects.all()
        for user in users:
            #if not user.is_superuser:
            user.delete()

        content_ConfiMAA = ContentType.objects.get_for_model(ConfigMAA)
        try:
            expert = Permission.objects.get(codename = 'expert_configmaa', content_type=content_ConfiMAA)
            expert.delete()
        except:
            pass

    def check_ressource(self, path):
        """ Fait la vérification d'usage pour le fichier """
        path_file = self.box.joinpath(path)
        if not path_file.exists():
            raise FileExistsError("Le chemin {} n'existe pas. Les données ne peuvent pas être initialisées.".format(path_file))
        
    def __init__(self, box="box_test", repertoire=None):
        """ box nomme le répertoire contenant les fichiers configuration à installer 
            Par défaut, on va chercher les fichiers dans le répertoire voisin box.

            Pour le rejeu, on peut modifier le comportement et aller dans un autre répertoire (exemple de TC)
            repertoire est alors le parent de box
        """
        if repertoire is None:
            rep = Path(__file__).parent
        else:
            rep = repertoire
        self.box = rep.joinpath(box)
        self.check_ressource(self.box)

        #TODO: prévoir aussi la création d'instance EnvoiMAA basiques et spécifiques
    
    def create_all_base_oper(self):
        """ Instancie toutes les tables en une seule commande """
        self.delete()
        self.create_region()
        self.create_group_and_permissions()
        self.create_users()
        self.create_stations()
        self.create_configsmaa()
        #self.create_client()

    def create_all_base_test(self, with_real_configmaa=False):
        """ Instancie toutes les tables en une seule commande """
        self.create_region()
        self.create_group_and_permissions()
        self.create_users()
        self.create_stations()
        if with_real_configmaa: 
            print("Chargement de la config MAA par fichier...")
            self.create_configsmaa()
        else:
            print(("Chargement de la config MAA par défaut..."))
            self.create_full_configmaa()

    def create_region(self, fichier="liste_regions.csv"):
        """ Crée les objets Region """
        path_file = self.box.joinpath(fichier)
        self.check_ressource(path_file)

        with open(path_file, 'r') as ficin:
            for ligne in ficin.readlines():
                ligne = ligne.strip()
                if ligne != "":
                    Region.objects.create(tag=ligne)

    def create_group_and_permissions(self):
        # Création des groupes
        configurateur, create = Group.objects.get_or_create(name="Configurateur")
        administrateur, create = Group.objects.get_or_create(name="Administrateur")
        superadmin, create = Group.objects.get_or_create(name="Super admin")
        maa_manuel, create = Group.objects.get_or_create(name="Editeur manuel")
        
        # Droits sur Station
        content_Station = ContentType.objects.get_for_model(Station)
        configurateur.permissions.add(Permission.objects.get(codename='view_station', content_type=content_Station))
        configurateur.permissions.add(Permission.objects.get(codename='change_station', content_type=content_Station))
        
        superadmin.permissions.add(Permission.objects.get(codename='delete_station', content_type=content_Station))

        administrateur.permissions.add(Permission.objects.get(codename='add_station', content_type=content_Station))

        # Droits sur Région
        content_Region = ContentType.objects.get_for_model(Region)
        administrateur.permissions.add(Permission.objects.get(codename='view_region', content_type=content_Region))
        administrateur.permissions.add(Permission.objects.get(codename='change_region', content_type=content_Region))
        administrateur.permissions.add(Permission.objects.get(codename='add_region', content_type=content_Region))
        
        superadmin.permissions.add(Permission.objects.get(codename='delete_region', content_type=content_Region))

        # Droits sur Profil
        content_Region = ContentType.objects.get_for_model(Profile)
        content_User = ContentType.objects.get_for_model(User)

        administrateur.permissions.add(Permission.objects.get(codename='view_profile', content_type=content_Region))
        administrateur.permissions.add(Permission.objects.get(codename='view_user', content_type=content_User))
        administrateur.permissions.add(Permission.objects.get(codename='change_profile', content_type=content_Region))
        administrateur.permissions.add(Permission.objects.get(codename='change_user', content_type=content_User))
        administrateur.permissions.add(Permission.objects.get(codename='add_profile', content_type=content_Region))
        administrateur.permissions.add(Permission.objects.get(codename='add_user', content_type=content_User))

        superadmin.permissions.add(Permission.objects.get(codename='delete_profile', content_type=content_Region))
        superadmin.permissions.add(Permission.objects.get(codename='delete_user', content_type=content_User))
        

        # Droits sur les configMAA
        content_ConfiMAA = ContentType.objects.get_for_model(ConfigMAA)
        # => crée une autorisation de modifier les paramètres fins des config MAA
        change_fin, nope = Permission.objects.get_or_create(codename = 'expert_configmaa', name="Can specify configMAA", content_type=content_ConfiMAA)
        administrateur.permissions.add(change_fin)
        
        superadmin.permissions.add(change_fin)

        configurateur.permissions.add(Permission.objects.get(codename='view_configmaa', content_type=content_ConfiMAA))
        configurateur.permissions.add(Permission.objects.get(codename='change_configmaa', content_type=content_ConfiMAA))
        configurateur.permissions.add(Permission.objects.get(codename='add_configmaa', content_type=content_ConfiMAA))
        configurateur.permissions.add(Permission.objects.get(codename='delete_configmaa', content_type=content_ConfiMAA))


        # Droits sur les envoi MAA
        envoi_maa = ContentType.objects.get_for_model(EnvoiMAA)
        configurateur.permissions.add(Permission.objects.get(codename='view_envoimaa', content_type=envoi_maa))
        # Créé un droit particulier pour éditer des maa manuels
        edit_manuel, nope = Permission.objects.get_or_create(codename = 'envoimaa_manuel', name="Can Send manual MAA", content_type=envoi_maa)
        maa_manuel.permissions.add(edit_manuel)

    def create_users(self, fichier="liste_utilisateurs.csv"):
        """ Crée les utilisateurs """
        path_file = self.box.joinpath(fichier)
        self.check_ressource(path_file)

        groupes = {}
        for tag in ['Super admin', 'Administrateur', 'Configurateur', 'Editeur manuel']:
            groupes[tag] = Group.objects.get(name=tag)

        with open(path_file, 'r') as ficin:
            # pseudo;mail;pwd;is_superadmin;is_taf;tag_region;liste/groupes
            ficin.readline()
            for ligne in ficin.readlines():
                if ligne.strip() == '':
                    continue
                infos = ligne.strip().split(";")
                login = infos[0]
                email = infos[1]
                pwd = infos[2]
                is_admin = bool(infos[3])
                is_staff = bool(infos[4])
                tag_region = infos[5]
                liste_groupes = infos[6].split("/")

                if is_admin:
                    # Pour la création du superuser, on doit pouvoir passer par :
                    #from django.contrib.auth import get_user_model
                    #get_user_model().objects.create_superuser
                    user = User.objects.create_superuser(login, email, pwd)
                    user.is_staff = is_staff
                else:
                    user.is_staff = True
                    user = User.objects.create_user(login, email, pwd)
                
                user.is_staff = is_staff
                if tag_region != "": 
                    user.profile.region = Region.objects.get(tag = tag_region)

                #Affecte un groupe
                for groupe in liste_groupes:
                    user.groups.add(groupes[groupe])
                user.save()

    def create_stations(self, fichier="liste_stations.csv"):
        """ Configure les stations """
        path_file = self.box.joinpath(fichier)
        self.check_ressource(path_file)

        with open(path_file, 'r') as ficin:

            # oaci;nom;entete;date_pivot;region__tag;inseepp;outremer;active;ouverture;fermeture;retention;reconduction;repousse;wint_unit;fuseau
            ficin.readline() # Evince la première ligne
            
            for ligne in ficin.readlines():
                if ligne.strip() == '':
                    continue

                infos = ligne.strip().split(";")
                oaci= infos[0]
                nom = infos[1]
                entete = infos[2]
                date_pivot = datetime.datetime.strptime(infos[3], "%Y-%m-%d %H:%M:%S")
                region = Region.objects.get(tag=infos[4])
                inseepp = infos[5]
                outremer = infos[6]=='True'
                active = infos[7]=='True'
                ouverture = infos[8]
                fermeture = infos[9]
                retention = int(infos[10])
                reconduction = int(infos[11])
                repousse = int(infos[12])
                wind_unit = infos[13]
                fuseau = infos[14]
                ouverture_hiver = infos[15]
                fermeture_hiver = infos[16]
                ouverture_ete = infos[17]
                fermeture_ete = infos[18]
                inseeaero = infos[19]
                

                station= Station.objects.create(
                    oaci = oaci, nom=nom, entete=entete, date_pivot=date_pivot,
                    region=region, inseepp=inseepp, outremer=outremer, active=active, 
                    ouverture=ouverture, fermeture=fermeture, retention=retention, reconduction=reconduction,
                    repousse=repousse, wind_unit=wind_unit, fuseau = fuseau, 
                    ouverture_hiver = ouverture_hiver, fermeture_hiver = fermeture_hiver,
                    ouverture_ete = ouverture_ete, fermeture_ete = fermeture_ete,
                    inseeaero = inseeaero
                    )

    def create_configmaa(self, oaci, types = ['VENT', 'TMIN', 'TS']):
        """ Crée un set de config MAA pour une station oaci en fonction des types passés en paramètres
            Par défaut, pause = 2, scan = 3 pour GR, TS et 12 pour les autres, profondeur = 12
            Les maa automatisable sont mis à auto

        """
        station = Station.objects.get(oaci = oaci)
        pause = 2
        scan = 12
        profondeur = 12
        for type_maa in types:
            if type_maa in ['GR', 'TS']: scan = 3
            default_maa = AutorisedMAAs.get_instance(type_maa)
            auto = default_maa.automatisable

            if not default_maa.occurrence:
                seuil = 10
            else:
                seuil = None
            ConfigMAA.objects.create(
                station = station, type_maa = type_maa, seuil = seuil,
                auto = auto, pause = pause, scan = scan, profondeur = profondeur)
    
    def create_configsmaa(self, fichier="liste_maas.csv"):
        """ Charge les configsmaa """
        path_file = self.box.joinpath(fichier)
        self.check_ressource(path_file)

        with open(path_file, 'r') as ficin:

            # oaci;type;seuil;auto;pause;scan;profondeur
            ficin.readline() # Evince la première ligne des entêtes
            
            for ligne in ficin.readlines():
                if ligne.strip() == '':
                    continue
                infos = ligne.strip().split(";")
                oaci = infos[0] #TODO: et avec une sérialisation ?
                type_maa= infos[1]
                seuil = None
                if infos[2] != "":
                    seuil = float(infos[2])
                auto = infos[3] == 'True'
                pause = int(infos[4])
                scan = int(infos[5])
                profondeur = int(infos[6])

                # Récupère l'instance de station correspondance
                try:
                    station = Station.objects.get(oaci = infos[0])
                    configmaa = ConfigMAA.objects.create(
                        station = station,
                        type_maa = type_maa,
                        seuil = seuil,
                        auto = auto,
                        pause = pause, 
                        scan = scan, 
                        profondeur = profondeur
                    )
                    configmaa.save()
                except:
                    pass

    def create_full_configmaa(self):
        """ Crée l'ensemble des MAA possibles pour l'ensemble des stations exitantes """
        stations = Station.objects.all()
        all_types = [ type_maa for type_maa, label in AutorisedMAAs.get_choices()]
        for station in stations:
            self.create_configmaa(station.oaci, all_types)

    def create_client(self, fichier="client.csv"):
        """ Charge les clients """
        path_file = self.box.joinpath(fichier)
        self.check_ressource(path_file)
