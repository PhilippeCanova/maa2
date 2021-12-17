from datetime import datetime

from django.db import models

from maa_django.mes_mixins import Activable

# Create your models here.
class AutorisedMAA(object):
    def __init__(self, type, nom, **options):
        self.type = type
        self.nom = nom
        self.seuil = options.get('seuil', None)
        self.automatisable = options.get('auto', False)
        self.pause = options.get('pause', 2)
        self.scan =  options.get('scan', 12)
        self.profondeur =  options.get('profondeur', 12)
        self.occurrence =  options.get('occurrence', True)
        self.decription_genre_féminin =  options.get('decription_genre_féminin', True)
        self.description_singulier =  options.get('description_singulier', True)
        self.description_label =  options.get('description_label', self.type)
        self.description_comparatif =  options.get('description_comparatif', '?')
        self.description_unit =  options.get('description_unit', '')
        self.force_unit  = options.get('force_unit', 'kt')


    def get_description(self, fcst, seuil=None, at=None, force_unit=None):
        """ Détermine la description en clair du message à insérer dans le MAA """
        #TODO: il est possible que tous les *AT* ne soient plus utilisés. Les retirer si c'est confirmé. 
        unite = self.description_unit
        if force_unit is not None:
            unite = force_unit

        label = "De la " + self.description_label
        if not self.decription_genre_féminin:
            label = "Du " + self.description_label
        if not self.description_singulier:
            label = "Des " + self.description_label
        if not self.occurrence:
            label = "Une " + self.description_label
            if not self.decription_genre_féminin:
                label = "Un " + self.description_label
            if not self.description_singulier:
                label = "Des " + self.description_label
                
        accord = ''
        if self.decription_genre_féminin: accord='e'

        verbe_etre = 'est'
        verbe_avoir = "a"
        if not self.description_singulier:
            verbe_etre = 'sont'
            verbe_avoir = "ont"
            accord = accord + "s"
            
        phrase = ""
        if self.occurrence:
            if fcst=="FCST":
                phrase = "{} {} prévu{} durant la période de validité.".format(label, verbe_etre, accord)
            elif fcst=="OBS":
                phrase = "{} {} été observé{}.".format(label, verbe_avoir, accord)
            elif fcst=="OBSAT":
                phrase = "{} {} été observé{} à {}.".format(label, verbe_avoir, accord, datetime.strftime(at),"%H:%M")
            elif fcst=="OBSATANDFCST":
                phrase = "{} {} été observé{} à {}\net {} prévu{} durant la période de validité.".format(label, verbe_avoir, accord, datetime.strftime(at),"%H:%M", verbe_etre, accord)
            elif fcst=="OBSANDFCST":
                phrase = "{} {} été observé{}\net {} prévu{} durant la période de validité.".format(label, verbe_avoir, accord, verbe_etre, accord)
        else:
            qualificatif = "{} {} {}{}".format(label, self.description_comparatif, seuil, unite)
            if fcst=="FCST":
                phrase = "{} {} prévu{} durant la période de validité.".format(qualificatif, verbe_etre, accord)
            elif fcst=="OBS":
                phrase = "{} {} été observé{}.".format(qualificatif, verbe_avoir, accord)
            elif fcst=="OBSAT":
                phrase = "{} {} été observé{} à {}.".format(qualificatif, verbe_avoir, accord, datetime.strftime(at),"%H:%M")
            elif fcst=="OBSATANDFCST":
                phrase = "{} {} été observé{} à {}\net {} prévu{} durant la période de validité.".format(qualificatif, 
                                            verbe_avoir, accord, datetime.strftime(at),"%H:%M", verbe_etre, accord)
            elif fcst=="OBSANDFCST":
                phrase = "{} {} été observé{}\net {} prévu{} durant la période de validité.".format(qualificatif, 
                                            verbe_avoir, accord, verbe_etre, accord)

        return phrase
        
class AutorisedMAAs(object):
    autorised = {
        'TS':AutorisedMAA('TS', 'Orage', auto=True, occurrence=True, 
            decription_genre_féminin= False, description_singulier=False, description_label="orages", description_comparatif=None), 

        'HVY_TS':AutorisedMAA('HVY_TS', 'HVY_TS ', auto=False, occurrence=True, 
            decription_genre_féminin= False, description_singulier=False, description_label="orages violents", description_comparatif=None), 

        'SQ':AutorisedMAA('SQ', 'Grain', auto=True, occurrence=True, 
        decription_genre_féminin= False, description_singulier=True, description_label="grain", description_comparatif=None), 

        'FG':AutorisedMAA('FG', 'FG ', auto=True, occurrence=True, 
            decription_genre_féminin= False, description_singulier=True, description_label="brouillard", description_comparatif=None), 

        'DENSE_FG':AutorisedMAA('DENSE_FG', 'Brouillard dense', auto=True, occurrence=True, 
            decription_genre_féminin= False, description_singulier=True, description_label="brouillard dense", description_comparatif=None), 

        'SN':AutorisedMAA('SN', 'SN', auto=False, occurrence=True,
            decription_genre_féminin= True, description_singulier=True, description_label="neige", description_comparatif=None), 
        'HVY_SN':AutorisedMAA('HVY_SN', 'HVY_SN ', auto=False, occurrence=True,
            decription_genre_féminin= True, description_singulier=True, description_label="neige forte", description_comparatif=None), 

        'FZDZ':AutorisedMAA('FZDZ', 'FZDZ', auto=True, occurrence=True,
        decription_genre_féminin= True, description_singulier=True, description_label="bruine verglaçante", description_comparatif=None), 
        'HVY_FZDZ':AutorisedMAA('HVY_FZDZ', 'HVY_FZDZ ', auto=False, occurrence=True,
        decription_genre_féminin= True, description_singulier=True, description_label="bruine verglaçante forte", description_comparatif=None), 

        'VENT_MOY':AutorisedMAA('VENT_MOY', 'VENT_MOY', auto=True, occurrence=False,
        decription_genre_féminin= False, description_singulier=True, description_label="vent moyen", description_comparatif=">=", description_unit="kt"), 
        
        'VENT':AutorisedMAA('VENT', 'VENT ', auto=True, occurrence=False,
        decription_genre_féminin= False, description_singulier=False, description_label="vent max ou rafales", description_comparatif=">=", description_unit="kt"), 
        
        'VEHICLE_RIME':AutorisedMAA('VEHICLE_RIME', 'VEHICLE_RIME ', auto=False, occurrence=True,
        decription_genre_féminin= True, description_singulier=True, description_label="gelée blanche véhicule", description_comparatif=None), 
        
        'TMIN':AutorisedMAA('TMIN', 'TMIN ', auto=True, occurrence=False,
        decription_genre_féminin= True, description_singulier=True, description_label="température", description_comparatif="<=", description_unit="°C"),

        'TMAX':AutorisedMAA('TMAX', 'TMAX ', auto=True, occurrence=False,
        decription_genre_féminin= True, description_singulier=True, description_label="température", description_comparatif=">=", description_unit="°C"),
        
        'TOXCHEM':AutorisedMAA('TOXCHEM', 'TOXCHEM ', auto=False, occurrence=True,
        decription_genre_féminin= False, description_singulier=False, description_label="produits chimiques toxiques", description_comparatif=None), 

        'TC':AutorisedMAA('TC', 'TC ', auto=False, occurrence=True,
        decription_genre_féminin= False, description_singulier=False, description_label="cyclones tropicaux", description_comparatif=None), 
       
        'DU':AutorisedMAA('DU', 'DU ', auto=False, occurrence=True,
        decription_genre_féminin= False, description_singulier=False, description_label="vents de poussiere", description_comparatif=None),
        'DS':AutorisedMAA('DS', 'DS ', auto=False, occurrence=True,
        decription_genre_féminin= True, description_singulier=False, description_label="tempêtes de poussiere", description_comparatif=None),
        'SS':AutorisedMAA('SS', 'SS ', auto=False, occurrence=True,
        decription_genre_féminin= True, description_singulier=False, description_label="tempêtes de sable", description_comparatif=None),
        
        'RIME':AutorisedMAA('RIME', 'RIME ', auto=False, occurrence=True,
        decription_genre_féminin= True, description_singulier=False, description_label="gelées blanches", description_comparatif=None),
        
        'RR1':AutorisedMAA('RR1', 'RR1 ', auto=True, occurrence=False,
        decription_genre_féminin= False, description_singulier=False, description_label="cumuls de précipitations", description_comparatif=">=", description_unit="mm/1h"),
        'RR3':AutorisedMAA('RR3', 'RR3 ', auto=True, occurrence=False,
        decription_genre_féminin= False, description_singulier=False, description_label="cumuls de précipitations", description_comparatif=">=", description_unit="mm/3h"),
        'RR6':AutorisedMAA('RR6', 'RR6 ', auto=True, occurrence=False,
        decription_genre_féminin= False, description_singulier=False, description_label="cumuls de précipitations", description_comparatif=">=", description_unit="mm/6h"),
        'RR12':AutorisedMAA('RR12', 'RR12 ', auto=True, occurrence=False,
        decription_genre_féminin= False, description_singulier=False, description_label="cumuls de précipitations", description_comparatif=">=", description_unit="mm/12h"),
        'RR24':AutorisedMAA('RR24', 'RR24 ', auto=True, occurrence=False,
        decription_genre_féminin= False, description_singulier=False, description_label="cumuls de précipitations", description_comparatif=">=", description_unit="mm/24h"),

        'GR':AutorisedMAA('GR', 'GR ', auto=True, occurrence=True,
        decription_genre_féminin= True, description_singulier=True, description_label="grêle", description_comparatif=None),
        'HVY_GR':AutorisedMAA('HVY_GR', 'HVY_GR ', auto=False, occurrence=True,
        decription_genre_féminin= True, description_singulier=True, description_label="grêle forte", description_comparatif=None),

        'FWOID':AutorisedMAA('FWOID', 'FWOID ', auto=False, occurrence=True,
        decription_genre_féminin= True, description_singulier=True, description_label="Tempé <0°C sans dépot de glace au sol", description_comparatif=None),
        
        'FWID':AutorisedMAA('FWID', 'FWID ', auto=False, occurrence=True,
        decription_genre_féminin= True, description_singulier=True, description_label="Tempé <0°C avec dépot de glace au sol", description_comparatif=None),

        'ICE_DEPOSIT':AutorisedMAA('ICE_DEPOSIT', 'ICE_DEPOSIT ', auto=False, occurrence=True,
        decription_genre_féminin= False, description_singulier=False, description_label="dépots de glace", description_comparatif=None),

        'FZFG':AutorisedMAA('FZFG', 'FZFG ', auto=True, occurrence=True,
        decription_genre_féminin= False, description_singulier=True, description_label="brouillard givrant", description_comparatif=None),
        
        'SNRA':AutorisedMAA('SNRA', 'SNRA ', auto=False, occurrence=True,
        decription_genre_féminin= True, description_singulier=False, description_label="pluies et neiges mélées", description_comparatif=None),
        'HVY_SNRA':AutorisedMAA('HVY_SNRA', 'HVY_SNRA ', auto=False, occurrence=True,
        decription_genre_féminin= True, description_singulier=False, description_label="pluies et neiges mélées fortes", description_comparatif=None),

        'FZRA':AutorisedMAA('FZRA', 'FZRA ', auto=True, occurrence=True,
        decription_genre_féminin= True, description_singulier=True, description_label="pluie verglaçante", description_comparatif=None),
        'HVY_FZRA':AutorisedMAA('HVY_FZRA', 'HVY_FZRA ', auto=False, occurrence=True,
        decription_genre_féminin= True, description_singulier=False, description_label="pluies verglaçantes fortes", description_comparatif=None),

        'SA':AutorisedMAA('SA', 'SA ', auto=False, occurrence=True,
        decription_genre_féminin= True, description_singulier=False, description_label="tempêtes de sable", description_comparatif=None),

        'VA':AutorisedMAA('VA', 'VA ', auto=False, occurrence=True,
        decription_genre_féminin= True, description_singulier=False, description_label="cendres volcaniques", description_comparatif=None),
        
        'SEA':AutorisedMAA('SEA', 'SEA ', auto=False, occurrence=True,
        decription_genre_féminin= False, description_singulier=False, description_label="coups de mer", description_comparatif=None),

        'INV_TEMPE':AutorisedMAA('INV_TEMPE', 'INV_TEMPE', auto=False, occurrence=True,
        decription_genre_féminin= True, description_singulier=False, description_label="inversions de température", description_comparatif=None),

        'BLSN':AutorisedMAA('BLSN', 'BLSN ', auto=False, occurrence=True,
        decription_genre_féminin= False, description_singulier=True, description_label="poudrin de glace", description_comparatif=None),

        'TSUNAMI':AutorisedMAA('TSUNAMI', 'TSUNAMI ', auto=False, occurrence=True,
        decription_genre_féminin= False, description_singulier=False, description_label="tsunamis", description_comparatif=None),

        'HVY_SWELL':AutorisedMAA('HVY_SWELL', 'HVY_SWELL', auto=False, occurrence=True,
        decription_genre_féminin= True, description_singulier=False, description_label="fortes houles", description_comparatif=None),
    }

    AUTORISED_FCST = ['FCST', 'OBS', 'OBSAT', 'OBSATANDFCST', 'OBSANDFCST'] #TODO: cf les restrictions sur les type de fcst

    @staticmethod
    def get_choices()-> list:
        reponse = [ (m.type, m.nom) for key, m in AutorisedMAAs.autorised.items() ]
        return sorted(reponse)
    @staticmethod
    def is_occurrence(type_maa)-> bool:
        return AutorisedMAAs.autorised[type_maa].occurrence == True

    @staticmethod
    def is_automatisable(type_maa)-> bool:
        return AutorisedMAAs.autorised[type_maa].automatisable == True
    
    @staticmethod
    def get_instance(type_maa)-> AutorisedMAA:
        return AutorisedMAAs.autorised.get(type_maa, None)
    
class Region(models.Model):
    """ Région météo regroupant les aéroport"""
    tag = models.TextField(max_length=40, null=False, unique=True, verbose_name="Tag région")

    def __str__(self):
        return self.tag

class Station(Activable):
    """ Aéroport"""
    oaci = models.CharField(max_length=4, null=False, unique=True, verbose_name="Code OACI")
    nom = models.CharField(max_length=124, null=False, verbose_name="Nom")
    entete = models.CharField(max_length=11, null=False, verbose_name="Entete")
    region = models.ForeignKey(Region, on_delete=models.CASCADE, null=False, blank=False, verbose_name="Dir")
    inseepp = models.CharField(max_length=7, null=False, verbose_name="INSEEpp")
    inseeaero = models.CharField(max_length=7, null=False, verbose_name="INSEEaero")
    outremer = models.BooleanField(default= False, null=False)
    date_pivot = models.DateTimeField(null=False, verbose_name="Date changement d'heure")
    ouverture = models.TimeField(null=False, verbose_name="H ouverture")
    ouverture_ete = models.TimeField(null=False, verbose_name="H ouverture été")
    ouverture_hiver = models.TimeField(null=False, verbose_name="H ouverture hiver")
    fermeture = models.TimeField(null=False, verbose_name="H fermeture")
    fermeture_ete = models.TimeField(null=False, verbose_name="H fermeture été")
    fermeture_hiver = models.TimeField(null=False, verbose_name="H fermeture hiver")
    retention = models.IntegerField(null=False)
    reconduction = models.IntegerField(null=False)
    repousse = models.IntegerField(null=False)
    fuseau = models.CharField(max_length=124, null=False)
    wind_unit = models.CharField(max_length=3, null=False, choices=[('kt','kt'), ('kmh','km/h')], verbose_name="Unité de vitesse")
    
    class Meta:
        verbose_name = "Aéroport"

    def __str__(self):
        return "{}- {} ({})".format(self.oaci, self.nom, self.region)

    def is_kt(self):
        """ simple booléen qui retourne True si l'unité est en kt """
        return self.wind_unit == 'kt'
    
    def get_wind_with_station_unit(self, ff):
        """ Permet de convertir facilement le vent dans l'unité propre à la station 
            on fournit une valeur de vent en kt, en on retourne ff dans l'unité station et le label (unit, label)
        """
        if self.wind_unit == 'kt':
            return (ff, ('kt','kt'))
        else:
            return (round ( (ff * 1.852), 0 ), ('km','km/h'))

class ConfigMAA(Activable):
    """ Liste les MAA autorisés pour une station"""
    station = models.ForeignKey(Station, related_name='configmaa', on_delete=models.CASCADE, null=False)
    type_maa = models.CharField(max_length=20, null=False, choices= AutorisedMAAs.get_choices(), verbose_name="Type MAA")
    seuil = models.FloatField(null=True, blank=True)
    auto = models.BooleanField(null=False, default= False)
    pause = models.IntegerField(null=False, default=2)
    scan = models.IntegerField(null=False, default=12)
    profondeur = models.IntegerField(null=False, default=12)

    def __str__(self):
        reponse = "{} - {}".format(self.station, self.type_maa)
        if not AutorisedMAAs.is_occurrence(self.type_maa):
            # Ajout du seuil si le maa n'est pas de type occurrence
            reponse = reponse + " - {}".format(self.seuil)
        reponse = reponse + " ({} {} {} {})".format(self.auto, self.pause, self.scan, self.profondeur)

        return reponse
    
    def get_seuil_unit(self):
        """ Permet de retourner l'unité et le seuil dans cette unité.
            Ceci n'a d'intérêt que pour le vent
        """
        if self.type_maa in ['VENT', 'VENT_MOY']:
            unite = self.station.wind_unit
            if unite== 'kt':
                return unite, self.seuil
            else:
                return unite, round ( (self.seuil * 1.852), 0 )
        return None, None
    class Meta:
        ordering = ["station", "type_maa", "seuil"]
        verbose_name = "Configuration MAA"
        verbose_name_plural = "Configurations MAA"
        
        # Permet d'éviter un enregistrement de plusieurs MAA avec le même combo station/Type/seuil
        constraints = [
            models.UniqueConstraint(fields=['station', 'type_maa', 'seuil'], name='unique combo MAA par station')
        ]

class Client(Activable):
    """ Liste des destinataires reconnus"""
    nom = models.CharField(max_length= 250, null=False)
    prenom = models.CharField(max_length= 250, null=True, blank=True)
    telephone = models.CharField(max_length= 15, null=False)
    email = models.EmailField(max_length= 250, null=True, blank=True)
    regions = models.ManyToManyField(Region, blank=True, related_name='regions')
    stations = models.ManyToManyField(Station, blank=True, related_name='station')
    configmaas = models.ManyToManyField(ConfigMAA, blank=True)
    # TODO: Ajouter une fin d'abonnement pour pouvoir désactiver la production avant de pouvoir supprimer de la base

    def __str__(self):
        return "{} {} {} {}".format(self.nom, self.prenom, self.telephone, self.email)

class MediumMail(models.Model):
    """ Destinataires d'un client donnée"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=False)
    email = models.EmailField( null=False)

class MediumSMS(models.Model):
    """ Destinataires d'un client donnée"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=False)
    sms = models.CharField(max_length=15, null=False)

class MediumFax(models.Model):
    """ Destinataires d'un client donnée"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=False)
    fax = models.CharField(max_length=15, null=False)

class MediumFTP(models.Model):
    """ Destinataires d'un client donnée"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=False)
    remote = models.CharField(max_length=254, null=False)
    login = models.CharField(max_length=254, null=False)
    pwd = models.CharField(max_length=254, null=False)
    dir = models.CharField(max_length=254, null=True, blank=True)
    