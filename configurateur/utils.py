from datetime import datetime, timedelta

from configurateur.models import Station

def retrieve_utcnow():
    """ Retourne le datetime courrant (permet d'intercepter le retour dans les tests) """
    return datetime.utcnow()

def retrieve_pivot(annee, mois):
    """ Trouve le premier dimanche qui précède le 01/mois donné (mettre 4 pour le printemps et 11 pour l'automne) """
    pivot = datetime(annee, mois,1,1,0,0)
    jour = pivot.weekday()
    delta = -1 - jour
    pivot = pivot + timedelta(days=delta)
    return pivot

def chek_and_change_pivot_date(station = None):
    """ Permet de déterminer s'il y a opportunité de changer de date pivot, trouve la prochaine 
    et le cas échéant, met à jour ces heures"""
    NOW = retrieve_utcnow()
    annee = NOW.year
    
    pivot1 = retrieve_pivot(annee, 4) # Premier changement de l'année
    pivot2 = retrieve_pivot(annee, 11) # Premier changement de l'année
    pivot3 = retrieve_pivot(annee+1, 4) # Premier changement de l'année suivante

    if station is None:
        # On ne fournit pas d'instance de station précise, donc on traite toutes les stations
        stations = Station.objects.all()
        for station in stations:
            prochain_changement = pivot1
            if NOW > station.date_pivot:
                # On a dépassé le changement d'heure, on réaffecte à la prochaine
                if NOW > pivot1: # Passe à l'heure d'été
                    prochain_changement = pivot2
                    ouverture = station.ouverture_ete
                    fermeture = station.fermeture_ete
                if NOW > pivot2: # Passe à l'heure d'hiver
                    prochain_changement = pivot3
                    ouverture = station.ouverture_hiver
                    fermeture = station.fermeture_hiver
                station.date_pivot = prochain_changement
                station.ouverture = ouverture
                station.fermeture = fermeture
                station.save()

if __name__== "__main__":
     chek_and_change_pivot_date()
