# Évaluation technique — version 0.5

## Question évaluée

L'évaluation cherche à déterminer si FRONTIÈRE transforme une demande de capacité scientifique ou technique en une réponse plus utile, plus précise ou plus rapide qu'une recherche ordinaire.

Les méthodes sont comparées sur les mêmes cas et avec les mêmes informations de départ.

## Ce qu'un cas contient

Chaque cas comprend :

- une demande formulée comme elle aurait pu l'être au moment du besoin ;
- une ou plusieurs voies de résolution connues ;
- les formes de ressource qui se sont révélées pertinentes ;
- lorsque les sources le permettent, des ressources nommées ;
- des documents publics permettant de vérifier la référence ;
- un degré de confiance dans la qualité de cette référence.

## Deux ensembles de cas

Le **jeu de développement** contient vingt cas publics. Il sert à améliorer le système et à comprendre ses erreurs.

Le **jeu réservé** contient dix autres cas. Ses réponses de référence sont gardées hors du dépôt public. Il sert à vérifier les performances sur des cas qui n'ont pas servi au développement.

## Méthodes comparées

Trois comparaisons sont prioritaires :

1. une recherche manuelle réalisée par un analyste ;
2. un assistant généraliste disposant d'une recherche en ligne ;
3. FRONTIÈRE.

Une quatrième comparaison peut utiliser uniquement les sources institutionnelles habituelles.

## Mesures

Les résultats sont examinés séparément selon :

- la justesse des voies proposées ;
- la justesse des formes de ressource proposées ;
- la capacité à retrouver des ressources concrètes lorsque la référence le permet ;
- le temps total consacré au cas ;
- le temps humain consacré à la vérification ;
- la qualité et la pertinence des preuves fournies.

Pour les catégories attendues, trois mesures complémentaires sont utilisées :

- **précision** : part des propositions qui sont correctes ;
- **rappel** : part des éléments attendus qui ont été retrouvés ;
- **mesure harmonique** : équilibre entre précision et rappel.

Aucune note unique ne remplace ces dimensions.

## Protection du jeu réservé

Les questions du jeu réservé sont publiques. Les réponses de référence ne le sont pas.

Le dépôt public contient une empreinte cryptographique du fichier de référence. Cette empreinte permet de vérifier que les références utilisées pour l'évaluation correspondent bien au fichier préparé avant les réponses des évaluateurs.

Un évaluateur indépendant reçoit uniquement les questions, les consignes et le modèle de réponse. Il ne doit pas consulter l'historique du dépôt ni rechercher l'origine exacte des formulations.

## Ce que cette évaluation permet de décider

Les résultats doivent aider à distinguer trois sources possibles de valeur :

- meilleure compréhension et orientation du besoin ;
- meilleure découverte ou vérification de ressources ;
- meilleure capacité à transformer une ressource pertinente en ressource réellement mobilisable.

La version technique suivante dépendra de l'avantage observé, et non d'une liste de fonctions prévue à l'avance.

## Publication conditionnelle des résultats du banc de développement

L'interface `/evaluation` contient les cas de **développement** enregistrés dans l'application, distincts du jeu réservé H01–H10 dont les références restent hors du dépôt public. Lorsqu'un cas interne n'est pas encore marqué comme révélé, ses étiquettes de référence, ses scores individuels et sa contribution aux moyennes par méthode doivent rester absents des vues et de `/api/v1/evaluation`. La seule présence d'une moyenne chiffrée sur un cas unique suffirait à dévoiler sa qualité relative sans révélation explicite.

Le compteur `prediction_count` dénombre toutes les réponses enregistrées à ce banc interne ; `scored_prediction_count` indique les réponses appartenant à des cas révélés, et `sealed_prediction_count` les réponses encore masquées. Les indicateurs `methods` et leurs tailles `n` portent uniquement sur les réponses révélées. Les méthodes disposant exclusivement de réponses scellées n'ont pas de score public.

La révélation d'un cas du banc interne relève d'une décision explicite et irréversible pour son statut de développement : les autres réponses ultérieures à ce cas perdent leur caractère aveugle. Le dispositif H01–H10 possède une chaîne de gel et de correction indépendante ; **cette interface ne remplace pas sa procédure de protection des références privées**. Aucun score affiché par le banc interne ne doit être assimilé à un résultat indépendant de l'étude réservée.
