from pathlib import Path
import datetime


from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from configurateur.models import Region, Station, ConfigMAA
from analyseur.models import EnvoiMAA
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.http import FileResponse

from profiles.models import Profile

class Command(BaseCommand):
    help = 'Crée un MAA à partir dùn EnvoiMAA'

    """def add_arguments(self, parser):
        parser.add_argument('poll_ids', nargs='+', type=int)

    def handle(self, *args, **options):
        for poll_id in options['poll_ids']:
            try:
                poll = Poll.objects.get(pk=poll_id)
            except Poll.DoesNotExist:
                raise CommandError('Poll "%s" does not exist' % poll_id)

            poll.opened = False
            poll.save()

            self.stdout.write(self.style.SUCCESS('Successfully closed poll "%s"' % poll_id))
            """
    
            

    def handle(self, *args, **options):

        # implémente quelques envois de MAA
        envois = EnvoiMAA.objects.all()
        
        
        conf_maa = ConfigMAA.objects.get(station__oaci = 'LFPG', type_maa= 'TS')
        envoi = EnvoiMAA.objects.get(configmaa = conf_maa, numero=1)
        print (envoi)
        
        base_dir = Path(__file__).parent
        from producteur.pdf_tools import MaaPDF
        pdf = MaaPDF(str(base_dir.joinpath("test.pdf").absolute()), envoi)

            
        """
        with open(base_dir.joinpath('MAAx.pdf'), 'rb') as f:
            envoi.message_pdf.save("MAA_LFPG_TS_1_20210824052410_1.pdf", File(f))
        print(envoi.message_pdf.path)
        """