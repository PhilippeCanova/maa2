from datetime import datetime, timedelta

from django.db import models
from django.db.models.query import QuerySet

from maa_django.models.mes_mixins import Activable
from configurateur.models import ConfigMAA


# Create your models here.

class EnvoiMAAQuerySet(QuerySet):
    """ Permet de définir un manager particulier et d'accès plus simplement à certaines requêtes """
    #TODO: voir pour être sûr de n'avoir que le plus récent
    def current_maas(self):
        """ Permet de retourner tous les maa en cours 
            Attention, plusieurs peuvent être retournés pour un même type
        """
        return self.filter(date_fin__gt = datetime.utcnow()).order_by('-date_envoi')
    
    def current_maas_by_station(self, oaci, heure= datetime.utcnow()):
        """ Permet de retourner les maa en cours pour une station {oaci} donnée 
            Attention, plusieurs peuvent être retournés
        """
        return self.filter(date_fin__gt = heure).filter(configmaa__station__oaci = oaci).order_by('-date_envoi')
    
    def current_maas_by_type(self, oaci, type_maa, heure = datetime.utcnow(), seuil = None):
        """ Permet de retourner le dernier MAA en cours de validité pour un type données 
            C'est donc une instance de EnvoiMAA s'il y en a un, ou None sinon """
        print(oaci, type_maa, heure, seuil)
        selon_seuil = self.filter(date_fin__gt = heure).filter(configmaa__station__oaci = oaci)
        selon_seuil = selon_seuil.filter(configmaa__type_maa = type_maa).order_by('-date_envoi')
        if seuil is not None:
            selon_seuil = selon_seuil.filter(configmaa__seuil = seuil)      
        return selon_seuil.first()
    
    def last_MAA(self, oaci, date_emission):
        """ Ne pas utiliser !!

            Permet de retourner le dernier MAA envoyé pour une station depuis 00TU de la date passée 
            Retourne None si aucun    
        """
        debut = date_emission.replace(hour=0).replace(minute=0).replace(second=0).replace(microsecond=0)
        fin = debut + timedelta(days=1)
        
        return self.filter(configmaa__station__oaci = oaci).filter(date_envoi__gte = debut).filter(date_envoi__lt = fin).order_by('numero').last()

    def history_maas(self, nb_heures = 48, maintenant = datetime.utcnow(), liste_stations=None):
        """ Permet de retourner la liste des maa envoyés au cours de {nb_heures} dernières heures 
            Si liste_stations est passée, c'est la liste des codes oaci des aéroports concernés
        """
        avant = maintenant - timedelta(hours=nb_heures)
        filtre = self.filter(configmaa__station__oaci__in = liste_stations)
        return filtre.filter(date_envoi__gt = avant).order_by('configmaa__station__oaci').order_by('-date_envoi')

class EnvoiMAA(models.Model):
    """ Liste des MAA générés/envoyés"""

    # Détermine les différents statuts possibles pour un MAA généré en base.
    CHOICES_STATUS = [
        ('to_create', 'A créer'), # Indique à la routine secondaire qu'il y a une production de pdf à générer
        ('to_send', 'A envoyer'),   # A envoyer
        ('ok', 'Envoyé'),         # Acquittement de délivrance de Difmet, Transmet et Metgate
    ]

    objects = EnvoiMAAQuerySet.as_manager()
    configmaa = models.ForeignKey(ConfigMAA, related_name='maa_emis',  on_delete=models.CASCADE, null=False)
    date_envoi = models.DateTimeField(null=False)
    date_debut = models.DateTimeField(null=False)
    date_fin = models.DateTimeField(null=False)
    numero = models.IntegerField(null=False)
    message = models.TextField(null=False)
    entete_transmet = models.TextField(null=True)
    fcst = models.CharField(max_length=20, editable=True, null=False, blank=False, default="FCST")
    at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, editable=True, null=False, default='new', choices = CHOICES_STATUS)
    context_TAF = models.TextField(null=True, blank=True)
    context_CDPH = models.TextField(null=True, blank=True)
    context_CDPQ = models.TextField(null=True, blank=True)
    description_maa = models.TextField(null=True, blank=True)
    log = models.TextField(null=True, blank=True)
    message_mail = models.TextField(null=True, blank=True)
    message_pdf = models.FileField(upload_to='uploads/%Y/%m/%d/', null=True, blank=True)
    message_sms = models.TextField(null=True, blank=True)
    num_groupe = models.IntegerField(null=False, default=1)
    total_groupe = models.IntegerField(null=False, default=1)
    cancel = models.BooleanField(null=False, default=False)
    data_vent = models.TextField(null=True, blank=True)
    data_tempe = models.TextField(null=True, blank=True)
    

    @staticmethod
    def current_maas_by_type(oaci, type_maa, heure= datetime.utcnow(), seuil=None):
        """ Permet de retourner le dernier MAA en cours de validité pour un type données 
            C'est donc une instance de EnvoiMAA s'il y en a un, ou None sinon """
        last_maa = EnvoiMAA.objects.filter(configmaa__station__oaci = oaci).filter(configmaa__type_maa = type_maa).filter(configmaa__seuil = seuil).order_by('numero').last()
        if last_maa is None:
            return None
        if last_maa.date_fin <= heure:
            return None
        return last_maa
        
    @staticmethod
    def get_choix_status(status):
        """ Permet de renvoyer le tuple status pour une clé passée """
        for cle, label in EnvoiMAA.CHOICES_STATUS:
            if cle == status:
                return (cle, status)
        return None

    def __str__(self):
        return "pk:{} {} {} {} {}".format(self.pk, self.configmaa.station.oaci, self.configmaa.type_maa, self.date_envoi, self.numero)
