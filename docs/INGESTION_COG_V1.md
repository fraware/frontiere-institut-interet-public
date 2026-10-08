# Territoires de référence de l’Insee — version 1

## Objet

Ce document décrit l’importation du Code officiel géographique publié par l’Insee.

Cette source sert à identifier les communes, départements, régions et autres unités territoriales. FRONTIÈRE garde ces territoires séparés des organisations qui les administrent : une commune n’est pas une mairie ; un département n’est pas un conseil départemental ; une région n’est pas un conseil régional.

## Source

Source de référence : Code officiel géographique au 1er janvier 2026, Insee.

Page officielle :

https://www.insee.fr/fr/information/8740222

Archive :

https://www.insee.fr/fr/statistiques/fichier/8740222/cog_ensemble_2026_csv.zip

## État courant

<!-- FRONTIERE:ETAT_COG:DEBUT -->
État du dernier cycle complet, observé le **2026-10-08**.

L’archive officielle produit **40 345 unités territoriales courantes** et **150 421 relations entre territoires**, avec **0 relation non résolue**.

La répartition comprend 34 875 communes, 2 105 communes déléguées, 2 293 cantons ou pseudo-cantons, 471 communes associées, 333 arrondissements, 101 départements, 45 arrondissements municipaux, 18 régions, 9 collectivités ou territoires français d’outre-mer, 95 zonages communaux associés à ces territoires.

L’Annuaire de l’administration contient **305 557 références à des codes Insee** portées par **85 681 services ou guichets locaux**. **305 550 références** correspondent exactement à une unité territoriale actuelle. Les **7 références restantes** correspondent à d’anciens codes attestés par l’historique officiel de l’Insee. **0** référence reste sans trace historique et **0** cas est ambigu.

Le taux de raccordement aux unités territoriales actuelles est de **99,9977 %**. En tenant compte de l’historique officiel, **100,0 %** des références sont expliquées.

Le fichier `resolution_annuaire_cog.json` conserve pour chaque ancien code l’objet concerné, la dernière période historique connue et le dernier événement communal publié par l’Insee.
<!-- FRONTIERE:ETAT_COG:FIN -->

## Organisation des données

Les territoires utilisent des identifiants techniques commençant par `FRONTIERE-TERR-`. Les organisations utilisent des identifiants commençant par `FRONTIERE-INST-`. Cette séparation empêche de confondre un territoire avec l’organisation qui l’administre.

La version 1 importe les régions, départements, arrondissements, cantons, communes, arrondissements municipaux, communes associées, communes déléguées, collectivités et territoires français d’outre-mer ainsi que les zonages communaux associés.

Le fichier Insee des collectivités exerçant les compétences départementales porte le code technique `CTCD`. FRONTIÈRE le conserve comme donnée source, sans le transformer automatiquement en unité territoriale.

## Relations entre territoires

Trois types de relation sont enregistrés :

| Sens pour le lecteur | Identifiant technique |
| --- | --- |
| une unité appartient à une unité plus large | `APPARTIENT_A` |
| une unité est une partie d’une commune parente | `PARTIE_DE` |
| une unité possède un chef-lieu ou un bureau centralisateur | `A_POUR_CHEF_LIEU` |

Une relation est créée seulement si la cible est retrouvée grâce à un code exact publié par l’Insee.

## Raccordement avec l’Annuaire de l’administration

Les services locaux déjà importés conservent les codes Insee publiés dans l’Annuaire. L’importation territoriale mesure combien de ces codes correspondent à une unité actuelle.

Lorsqu’un code n’existe plus dans le millésime 2026, le programme consulte les tables historiques présentes dans la même archive. Il explique ainsi l’écart sans remplacer silencieusement un ancien code par un code plus récent.

Aucun rapprochement par nom n’est utilisé.

## Fichiers produits

```text
institutionnel/
  schema_territoire_v1.json
  schema_relation_territoriale_v1.json
  territoires/cog/
  relations/territoriales/cog/
  instantanes/cog_manifest.json
  statistiques_cog.json
  anomalies_cog.json
  resolution_annuaire_cog.json
```

## Actualisation

Le Code officiel géographique est publié par millésime annuel, avec d’éventuelles corrections. FRONTIÈRE vérifie la source chaque semaine et après toute actualisation de l’Annuaire local qui pourrait modifier le raccordement des codes territoriaux.

Aucun commit n’est créé lorsque la source, la méthode de transformation et les données de l’Annuaire sont inchangées.

## Étape suivante

La base nationale des intercommunalités pourra utiliser ces territoires comme points de référence. Les établissements publics de coopération intercommunale et les syndicats resteront des organisations distinctes, reliées explicitement aux communes qu’ils couvrent.
