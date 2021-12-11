"""
    Cette app a pour objectif d'analyser les données fournies par l'app donneur et déterminer s'il y a opportunité 
    d'envoi ou d'annulation d'un MAA.

    Lors de l'analyse, toutes les 15 mn, si cette opportunité est répérée, l'information est stoquée dans le modèle EnvoiMAA pour traitement ultérieur.
"""