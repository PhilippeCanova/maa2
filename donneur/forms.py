from django import forms
from django.core.exceptions import ValidationError
from configurateur.models import Station

class StationOACIField(forms.CharField):
    """ Champ devant accueillir un code OACI d'aéroport à analyser """

    def validate(self, value):
        """ Permet de vérifier si la valeur code oaci entrée est bonne """
        super().validate(value)
        try: 
            station = Station.objects.get(oaci = value)
        except:
            raise ValidationError("La station {} n'est pas reconnue !")
        
        

#TODO: mettre aussi un validateur sur le champ date qui permet de restreindre les dates
# à la fois futures et trop anciennes.
class RetrievePastDatasForm(forms.Form):
    station = StationOACIField(label="Code OACI : ", max_length= 4)
    heure_analyse = forms.DateTimeField(label="Date d'analyse (AAAA-MM-JJ hh:mm:ss) : ")
