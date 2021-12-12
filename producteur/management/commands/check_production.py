from django.core.management.base import BaseCommand

from producteur.commons import analyse_1mn


class Command(BaseCommand):
    help = """
    Vérifie régulièrement si des maa ont été initiés mais pas encore produits (pdf) et diffusés.
    Se charge alors de ces deux actions
    """

    def handle(self, *args, **options):
        analyse_1mn()
