from django.core.management.base import BaseCommand
from configurateur.initiate_toolbox.initiate_db_tools import Initiate

class Command(BaseCommand):
    help = 'Lance la convertion des fichiers de config de la v1 en fichier v2 (cf initiate_toolbox'

    def handle(self, *args, **options):
        Initiate.convert_v1_to_v2()