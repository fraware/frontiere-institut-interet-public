# Rectificatif de mesure — 100 dates de flux RSS

**12 octobre 2026.** Ce document corrige un classement informatique et conserve l'historique de son origine.

## Constat reproductible

Deux relevés successifs des neuf flux officiels ont produit chacun **282 publications distinctes**.

- Première publication de données : commit `f3d2c0e93def41ff1ae7ac9870d27d6dcaa50835`, relevé **21:58:28 UTC**.
- Second relevé : **22:05:11 UTC**, effectué avec un extracteur lisant aussi les dates RSS `dc:date`, `published` et `updated`.

Le bilan du second cycle déclarait **100 révisions**. La comparaison des deux fichiers de publications, par identifiant stable, établit que les **282 titres, descriptions, liens, sources et identifiants sont identiques**. Exactement **100 champs `date_publication`** sont passés d'une valeur inconnue à une date extraite du flux `service_public_pro`. Le logiciel avait incorporé la date à l'empreinte de version et qualifié tout changement d'empreinte de « révision ».

Il s'agit donc de **100 enrichissements des métadonnées de date**, et non de 100 changements éditoriaux prouvés des publications officielles.

## Rectification datée

Le fichier `institutionnel/flux_publics/observations.json` conserve les 282 identifiants et les dates désormais reconnues. Pour les 100 notices concernées, la valeur `nombre_revisions` est rectifiée de 1 à 0 ; le champ `nombre_enrichissements_metadonnees` est fixé à 1, avec une annotation `rectification_extraction` citant le premier commit et la raison du changement.

Dans `institutionnel/flux_publics/etat_collecte.json`, les 100 révisions du deuxième relevé sont reclassées en enrichissements, avec un bloc `rectification_historique` documentant l'ancien calcul, les deux dates, le nombre de notices et le mode de comparaison. Les commits originaux demeurent consultables dans GitHub ; il n'y a pas de réécriture rétroactive des versions antérieures.

## Nouveau contrat logiciel

Le collecteur conserve une empreinte de **version normalisée**, comprenant la date. Sa qualification de révision éditoriale se fonde désormais sur les seuls champs `titre`, `description` et `lien`. Si ces champs sont inchangés et qu'une autre métadonnée est mieux extraite, seul `enrichissements_metadonnees` augmente.

Les compteurs ne prouvent pas qu'aucun changement éditorial transitoire ait été effectué entre les deux relevés ; ils classent uniquement les différences **effectivement observées**.

Cette distinction est indispensable avant de mesurer les nouveaux besoins détectés : une amélioration du logiciel d'extraction ne doit jamais être annoncée comme une augmentation réelle de l'activité administrative.
