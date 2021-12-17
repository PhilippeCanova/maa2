# Mettre les modèles communs dans ce répertoire et les déclarer comme suit :

from django.db import models

class Activable(models.Model):
    active = models.BooleanField(default = True)
    class Meta:
        abstract = True

