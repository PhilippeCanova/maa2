from django.core.management.base import BaseCommand

from analyseur.commons import analyse_15mn


class Command(BaseCommand):
    help = """
    Vérifie régulièrement, à partir des données récupérées, s'il est opportun d'envoyer des MAA
    """

    def handle(self, *args, **options):
        analyse_15mn()
