Sert à vérifier si les tests déclencheurs répondent aux critères.
C'est la station de Rennes (LFRN) qui sert de banc de tests. 

On commence avec des échéances où le CDP n'a rien de particulier. C'est alors les déclenchements sur données aéro qui sont les seuls pilote
à 2021-11-11 00:00:00 : aucun test déclencheur, le vent à 49 ne déclenche pas 
à 2021-11-11 01:00:00 : positif sur TS et Vent=50
à 2021-11-11 02:00:00 : positif sur GR
à 2021-11-11 03:00:00 : SQ FG FZRA FZDZ
à 2021-11-11 04:00:00 : montre que FZFG déclenche aussi FG. Et le vent FX=55 aussi déclenche
à 2021-11-11 05:00:00 : positif sur brouillard dense

Ensuite, les données aéro sont normales, les cdp au-dessus des seuils ne déclenchent que pour les paramètres non aéro.
On démontre ainsi la priorité des données aéro.
à 2021-11-11 06:00:00 : positif sur TMIN
à 2021-11-11 07:00:00 : positif sur TMAX
à 2021-11-11 08:00:00 : positif sur RR24 seul
à 2021-11-11 09:00:00 : positif sur tous les RR24

à 2021-11-11 10:00:00 : reste négatif alors que le cdp est positif sur VENT et TS

Pour finir, on passe la donnée aéro en CNL et on déclenche les paramètres possibles depuis CDP : tous sauf SQ, DENSE_FG, FZDZ 
à 2021-11-11 11:00:00 : positif sur VENT et TS (même contexte qu'à 10:00TU)
à 2021-11-11 12:00:00 : positif sur GR
à 2021-11-11 13:00:00 : positif sur FG, FZFG
à 2021-11-11 14:00:00 : positif sur FZRA
à 2021-11-11 15:00:00 : positif sur FG seul

TODO: Voir pour faire la même chose avec une station outre-mer





