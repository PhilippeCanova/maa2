import urllib

from django.core.management.base import BaseCommand

from configurateur.initiate_toolbox.initiate_db_tools import Initiate



class Command(BaseCommand):
    help = """
    Charge la configuration issue des données opérationnelles (positionnés dans initiate_toolbox/box_oper). 
    Au préalable, il faut lancer la commande convertV1V2, ce qui a pour but de prendre les config V1 du répertoire initiate_toolbox/v1 
    pour les mettre au bon format dans le répertoire initiate_toolbox/box_oper.
    """

    def handle(self, *args, **options):
        
        init = Initiate("box_oper")
        # init.delete() # Le mieux est de repartir d'une base complétement vide 

        init.create_all_base_oper()