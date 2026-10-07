# Organisation administrative de l’État — ingestion de la source DILA

## Objet

Ce document décrit l’importation du Référentiel de l’organisation administrative de l’État, publié par la Direction de l’information légale et administrative (DILA).

Cette source fournit la structure de base utilisée par FRONTIÈRE pour représenter les ministères, services centraux, services déconcentrés, établissements et autres organismes présents dans ce référentiel. Elle contient notamment des identifiants, des liens hiérarchiques, des coordonnées, des responsables, des missions et des textes de référence lorsque ces informations sont publiées.

Source officielle :

https://www.data.gouv.fr/datasets/referentiel-de-lorganisation-administrative-de-letat

Fichier courant :

https://echanges.dila.gouv.fr/OPENDATA/RefOrgaAdminEtat/FluxAnneeCourante/dila_refOrga_admin_Etat_fr_latest.zip

## État observé le 7 octobre 2026

La publication utilisée contient **7 905 services ou organismes**. FRONTIÈRE produit **7 905 objets normalisés** et **8 073 relations hiérarchiques résolues**.

Parmi ces objets :

- **7 900** disposent d’un parent principal directement justifié par la source ;
- **5** n’ont pas de parent principal dans ce périmètre ;
- **7 799** disposent d’au moins une coordonnée ;
- **7 550** disposent d’au moins un responsable ;
- **1 569** disposent d’une mission publiée ;
- **1 171** disposent d’au moins un texte de référence ;
- **417** exposent un numéro SIREN ;
- **415** exposent un numéro SIRET.

La source contient également **158 liens hiérarchiques dont la cible n’apparaît pas dans cette seule publication**. FRONTIÈRE les conserve dans `institutionnel/anomalies_roae.json`. Aucun lien de remplacement n’est créé à partir d’une ressemblance de nom.

Le croisement avec l’Annuaire de l’administration résout les 158 cibles grâce à leurs identifiants exacts. L’anomalie reste néanmoins conservée comme propriété de cette source isolée : cela permet de distinguer ce que fournit chaque publication de ce que FRONTIÈRE obtient en les croisant.

## Reproduire l’importation

```bash
python scripts/ingerer_roae.py
```

Le programme télécharge l’archive officielle, vérifie la structure du fichier et l’unicité des identifiants, puis produit les fichiers normalisés du dépôt.

## Fichiers produits

```text
institutionnel/
  entites/roae/
  relations/roae/
  instantanes/roae_manifest.json
  statistiques_roae.json
  anomalies_roae.json
```

Les sous-fichiers numérotés répartissent les données volumineuses en ensembles de taille raisonnable. Cette organisation limite aussi la taille des différences Git lors d’une mise à jour.

## Données normalisées et données source

Chaque objet contient une représentation normalisée utilisée par FRONTIÈRE et l’enregistrement DILA d’origine dans `source_dila`.

La copie de l’enregistrement d’origine permet de recalculer ultérieurement une nouvelle représentation sans perdre un champ publié par la source.

## Identité

L’identifiant technique de FRONTIÈRE est construit à partir de l’identifiant DILA :

```text
FRONTIERE-INST-DILA-<IDENTIFIANT DILA>
```

Les numéros SIREN, SIRET et autres identifiants restent enregistrés séparément. Deux organismes ne sont jamais fusionnés sur la seule ressemblance de leur nom.

## Hiérarchie

La source publie des liens entre services. FRONTIÈRE les traduit en relations explicites entre l’enfant et son parent.

Le nom technique de cette relation est `DEPEND_DE`. Une relation est créée uniquement lorsque la cible est retrouvée par son identifiant exact.

Les références dont la cible manque restent dans le fichier d’anomalies. Elles ne sont pas complétées par supposition.

## Dates et provenance

FRONTIÈRE distingue la date à laquelle une information est observée des dates de création, modification ou diffusion fournies par la DILA.

Une nouvelle exécution du programme ne crée pas artificiellement une nouvelle date d’observation si l’enregistrement source est identique. Une empreinte cryptographique de l’enregistrement permet cette comparaison.

Le fichier `institutionnel/instantanes/roae_manifest.json` conserve le producteur, la licence, la page du jeu de données, l’adresse de téléchargement, la date d’observation et les empreintes des fichiers utilisés et produits.

## Mise à jour

Une action GitHub vérifie quotidiennement la publication officielle. Elle recalcule les fichiers seulement si la source ou la méthode de transformation a changé. Un commit est créé uniquement lorsque l’état normalisé évolue.

## Limite

Cette source décrit une part importante de l’organisation de l’État, mais elle ne représente pas à elle seule tout le secteur public français. Les services locaux, collectivités, intercommunalités, structures de recherche, établissements de santé, opérateurs budgétaires et participations publiques nécessitent d’autres sources.
