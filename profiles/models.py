from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from maa_django.mes_mixins import Activable
from configurateur.models import Region


class Profile(Activable):
    """ Garder des champs nullable ou avec des valeurs par défaur pour éviter les conflits à la création d'un compte """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile',
                        primary_key=True)
    # User doit pouvoir être remplacé par settings.AUTH_USER_MODEL
    region = models.ForeignKey(Region, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return "{}".format(self.user.username)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        #print('create_user')
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    #print('save_user')
    instance.profile.save()
