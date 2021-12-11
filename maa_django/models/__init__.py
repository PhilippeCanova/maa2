# Mettre les modèles communs dans ce répertoire et les déclarer comme suit :
"""
from postable import Postable
from post import Post
from comment import Comment

Chaque modèle étant dans un fichier séparé

Dans un modèle, on peut définir une combinaison unique avec :
    class Meta:
        unique_together = ("latitude", "longitude")
"""

from .mes_mixins import Activable

