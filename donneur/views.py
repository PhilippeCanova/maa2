from django.shortcuts import render
from django.views.generic import FormView
from django.conf import settings

from configurateur.models import Station
from donneur.commons import retrieveDatasAero, retrieveDatasCDPH_metropole, retrieveDatasCDPQ_metropole, CDPDataHoraire
from donneur.commons import retrieveDatasCDPH_om, retrieveDatasCDPQ_om, AeroDataHoraire, CDPDataHoraire

from .forms import RetrievePastDatasForm

#TODO: cette vieux n'est pas protégée en lecture et n'est pas testée. Voir s'il faut faire quelque chose en particulier. 
class RetrievePastDatasView(FormView):
    form_class = RetrievePastDatasForm
    template_name = 'donneur/retrieve_past_datas.html'

    def array_spliter(self, chaine, entetes):
        """ Permet de remettre les lignes en format liste de liste """
        donnees = []
        donnees.append(entetes)
        for ligne in chaine:
            donnees.append(ligne.split(";"))
        return donnees 
        
    def form_valid(self, form):
        """If the form is valid, redirect to the supplied URL."""
        if self.extra_context is None:
            self.extra_context= {}
        datas = form.cleaned_data
        
        oaci = datas['station']
        station = Station.objects.get(oaci = oaci) 

        self.extra_context['station']= oaci
        self.extra_context['inseepp']= station.inseepp
        self.extra_context['heure_analyse']= datas['heure_analyse']

        
        # Récupération des données Aéro :
        data_aero = retrieveDatasAero([(station.oaci, station.inseeaero, station.outremer)], settings.REMOTE_CDPAERO_ARCHIVE).get(oaci, ["Données aéro non récupérées."])
        
        # Récupération des données modèles :
        station_liste = [(station.oaci, station.inseepp)]

        if station.outremer:
            data_h = retrieveDatasCDPH_om(station_liste, settings.REMOTE_CDPH_OM_ARCHIVE).get(oaci, ["Données H non récupérées."])
            data_q = retrieveDatasCDPQ_om(station_liste, settings.REMOTE_CDPQ_OM_ARCHIVE).get(oaci, ["Données Q non récupérées."])
            entetes_h  = CDPDataHoraire.PARAMETRES_CDPH_OM
            entetes_q  = CDPDataHoraire.PARAMETRES_CDPQ_OM
        else:
            data_h = retrieveDatasCDPH_metropole(station_liste, settings.REMOTE_CDPH_ARCHIVE).get(oaci, ["Données H non récupérées."])
            data_q = retrieveDatasCDPQ_metropole(station_liste, settings.REMOTE_CDPQ_ARCHIVE).get(oaci, ["Données Q non récupérées."])
            entetes_h  = CDPDataHoraire.PARAMETRES_CDPH
            entetes_q  = CDPDataHoraire.PARAMETRES_CDPQ
        
        # Rendu
        self.extra_context['data_aero']= self.array_spliter(data_aero, AeroDataHoraire.PARAMETRES_CDP_AERO)
        self.extra_context['data_h']= self.array_spliter(data_h, CDPDataHoraire.get_entetes_requete(entetes_h))
        self.extra_context['data_q']= self.array_spliter(data_q, CDPDataHoraire.get_entetes_requete(entetes_q))
        
        return self.render_to_response(self.get_context_data(form=form))
