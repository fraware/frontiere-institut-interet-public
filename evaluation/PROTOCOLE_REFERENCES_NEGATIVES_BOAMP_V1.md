# Références documentaires indépendantes sur 60 avis BOAMP — protocole v1

## Objet et périmètre

La présente expérience **ne reprend pas** la relecture de dix questions d'orientation H01–H10 ni celle des 45 événements historiques. Elle porte uniquement sur la lecture des résultats publiés dans **60 notices BOAMP complètes**, sélectionnées dans deux ensembles séparés : 36 avis techniques tirés sans utiliser leurs résultats, et 24 avis sélectionnés sur la mention « infructueux » dans leur intitulé. Le second ensemble est délibérément enrichi et ne permet aucune estimation de fréquence de la commande publique.

L'archive primaire utilisée est celle de l'exécution [38260128904](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38260128904), comprenant les deux fichiers de tirage, les deux rapports de collecte et les 60 réponses JSON. Les empreintes ordonnées des sélections sont, respectivement :

- 36 : `40f791c35adcdc67d69bb933e873b0efaa7b24dd0c74958474dc6272b94242c8` ;
- 24 : `abdd53aa7e2c5f89dc42a74ea7e6f9afdcaf85a1ba86042bcac6f3dc86253689`.

L'analyse automatique antérieure décrit 28 résultats de lots attribués dans les 36 cas ; dans les 24 autres, elle décrit 5 lots attribués et 2 lots avec un compteur officiel `tenders=0`, malgré le motif administratif `other`. Ce sont des **prédictions du lecteur logiciel**, non des références établies.

## Préparer les deux lectures

À partir de l'archive publique BOAMP déjà obtenue, préparer les dossiers en dehors du répertoire public du dépôt :

```bash
python scripts/preparer_relecture_issues_boamp.py \
  --archive /donnees/frontiere-etats-offres-et-motifs-20261012.zip \
  --sortie /espace/prive/relecture-issues-001
\`\`\``

Le programme contrôle l'intégrité ZIP, l'identité, la date officielle et l'empreinte SHA-256 de chaque réponse, les 60 identifiants des deux tirages, leur ordre et leur séparation. Il s'interrompt si la sélection ou les octets changent et refuse d'écraser un dossier existant.

Il produit le paquet commun, les sources officielles réordonnées selon une semence déterministe indépendante du résultat, deux dossiers autonomes `relecteur_1/` et `relecteur_2/` comprenant le même paquet, les mêmes sources, les consignes et un formulaire vierge. La correspondance entre cas et cohorte figure uniquement dans `correspondances_privees.json` à la racine réservée au responsable. Elle n'est pas transmise aux lecteurs.

Un document public peut contenir lui-même le mot « infructueux », un code d'attribution ou le motif du marché. Cet indice n'est ni supprimé ni réécrit, car il fait partie des preuves à évaluer. L'aveuglement concerne les **jugements préalables du logiciel** et la provenance de la sélection, sans prétendre masquer le contenu officiel.

## Grille individuelle, à partir de la source

Chaque lecteur conserve, pour chaque avis, une des quatre valeurs `RESULTATS_PAR_LOT`, `ATTRIBUTION_SANS_LOT`, `SANS_RESULTAT_DANS_CET_AVIS` ou `INDETERMINE`. Un avis d'appel d'offres dépourvu de résultat **dans cette publication** n'est pas un avis prouvant zéro offre reçue. Pour un avis avec résultats structurés, le jugement doit identifier chacun des lots vérifiés et éviter de compter trois décisions contractuelles du même lot comme trois lots différents.

Au niveau de chaque lot : décision officielle, code du motif, effectif total d'offres `tenders`, nombre de soumissions électroniques `t-esubm` et localisation de la preuve. L'absence d'un nombre total est inscrite `null`, jamais zéro. Les motifs `no-rece` et `other` ne doivent pas être déduits des effectifs, ni utilisés pour les remplacer.

Le jugement causal est **également par lot** : `SANS_OBJET` pour un lot attribué, et `NON_ETABLIE`, `DOCUMENTEE` ou `INDETERMINEE` pour une décision négative ou incertaine. La valeur `DOCUMENTEE` exige une pièce supplémentaire et un passage justifiant le lien causal, au-delà du simple résultat administratif. Le corpus des avis d'attribution seul ne démontre généralement pas la raison économique, technique ou scientifique d'un échec.

Les lecteurs ne consultent pas le rapport automatique avant d'avoir clos leurs deux formulaires et ne comparent pas leurs réponses entre eux. L'indépendance intellectuelle réelle ne saurait être attestée par une simple déclaration dans un fichier.

## Contrôle et désaccords

Une fois **les deux** lectures réellement complétées et leurs empreintes enregistrées séparément, exécuter :

```bash
python scripts/consolider_relecture_issues_boamp.py \
  --paquet /espace/prive/relecture-issues-001/paquet_commun.json \
  --lecture-1 /espace/prive/relecture-issues-001/relecteur_1/jugements_vierges.json \
  --lecture-2 /espace/prive/relecture-issues-001/relecteur_2/jugements_vierges.json \
  --sortie /espace/prive/relecture-issues-001/bilan-double-lecture.json
\`\`\``

Le vérificateur refuse des formulaires incomplets, deux identifiants de lecteur égaux, des lots répétés, des comptes incohérents, des chiffres sans localisation documentaire et un jugement causal `DOCUMENTEE` sans pièce propre. Il contrôle le rattachement des avis au même paquet et mesure l'accord séparément sur le statut de l'avis, les identifiants de lots, les décisions, les motifs, les deux effectifs et les jugements de causalité.

Les désaccords sont publiés avec les deux appréciations distinctes. Même avec 100 % d'accord, le logiciel ne délivre **aucune référence consensuelle**. Il reste à documenter la séparation effective des lecteurs, à arbitrer les désaccords par une troisième procédure et à fixer les références avant de dévoiler les prédictions des méthodes.

## Conditions d'une évaluation scientifique ultérieure

Une fois les références établies indépendamment, mesurer le résultat sur le jeu initial de 36 et l'ensemble enrichi de 24 **séparément**. Le premier a été tiré sans issue connue, mais son filtre lexical technique n'est pas représentatif. Le second est enrichi sur un indice de procédure antérieure infructueuse. Aucun pourcentage ne sera extrapolé à l'ensemble des marchés français.

Les mesures pertinentes sont l'exactitude par catégorie de résultat, l'absence de faux diagnostics de zéro offre, le taux d'abstention justifié, la conformité des comptes `tenders`/`t-esubm`, l'accord entre lecteurs, la traçabilité par lot, et la séparation entre preuve d'échec de consultation et **cause véritablement documentée**. Si le jeu de 36 ne contient aucun lot négatif, sa sensibilité au cas négatif n'est pas estimable sur cet ensemble.

**État actuel :** instrumentation et contrôles automatiques de préparation. Aucune double lecture humaine ni évaluation des performances n'est prétendue accomplie.
