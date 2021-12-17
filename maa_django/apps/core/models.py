import datetime

from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models.query import QuerySet

from maa_django.mes_mixins import Activable

TYPES_LOG = [
    ('error','Erreur'),
    ('warning','Avertissement'),
    ('info','Information'),
]

class Log(models.Model):
    """ Stoque les logs que l'on veut faire remonter """
    heure = models.DateTimeField(auto_now=True)
    type = models.CharField(max_length=10, null=False, choices= TYPES_LOG)
    machine = models.CharField(max_length=20, null=False) # Indique le nom de la machine ayant lancé le log
    code = models.CharField(max_length = 8)
    message = models.TextField(null=False)

    def __str__(self):
        return "{}-{}-{}-{}-{}".format(self.heure, self.type, self.machine, self.code, self.message)



