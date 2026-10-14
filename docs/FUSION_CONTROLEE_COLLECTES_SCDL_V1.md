# Concurrence des collectes et fusion protégée des propositions SCDL

**Date : 14 octobre 2026. Statut : correctif soumis à vérification.**

## Incident observé

La procédure [SCDL n° 38629460138](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38629460138) a achevé un relevé documenté (536 lignes SCDL examinées, aucune nouvelle piste, 11 pistes préservées et des anomalies partielles à examiner). Elle a créé la [proposition n° 427](https://github.com/fraware/frontiere-institut-interet-public/pull/427), dont les trois contrôles techniques ont réussi. GitHub a ensuite refusé la tentative de fusion avec le message « Base branch was modified. Review and try the merge again. ».

L'analyse des commits séparant le point initial du dernier état de `main` a établi l'absence de modification du fichier `institutionnel/deliberations_publiques/etat_collecte.json` dans la branche principale. La proposition n° 427 a ensuite été fusionnée **manuellement et de façon conditionnée à son empreinte exacte**, sans conflit identifié dans les chemins modifiés. Ce succès ponctuel ne résout pas la concurrence entre les procédures futures.

## Contrôle ajouté

Le programme `scripts/fusionner_proposition_controlee.py`, appelé par `moissonnage-deliberations-scdl.yml` à la place de l'appel direct de fusion, intervient **uniquement après** réussite de Python 3.11, Python 3.12 et du contrôle en conteneur. La liste fermée des deux fichiers SCDL autorisés est toujours contrôlée par la procédure initiale.

Avant **chaque** tentative de fusion, il vérifie :

1. L'identité du dépôt, de la source et de la branche créée par la collecte.
2. Le numéro de proposition, sa branche de base `main`, son état ouvert et son caractère non provisoire.
3. L'empreinte exacte du commit, inchangée depuis la réussite des contrôles.
4. Les fichiers modifiés par la proposition et leur conformité au périmètre déclaré de la source.
5. Les chemins modifiés sur `main` depuis l'ancêtre commun à la proposition. Le chevauchement avec les fichiers proposés provoque l'arrêt immédiat.
6. Les changements de code ou de configuration intervenus sur `main` : tout changement extérieur à `institutionnel/` ou `docs/` impose une nouvelle validation, même si les fichiers de collecte restent disjoints.

La commande finale utilise `gh pr merge --squash --match-head-commit`, qui conditionne la fusion à la correspondance de l'empreinte du commit. Le programme confirme ensuite auprès de GitHub que la proposition porte l'état **MERGED** ; une acceptation pour traitement ultérieur ne suffit pas à déclarer l'opération achevée.

## Reprises limitées

Seul le message précis de concurrence sur la branche de base autorise une nouvelle tentative, **au maximum trois**. Les changements sont réexaminés avant chacune, avec une attente bornée. Les échecs d'accès, les conflits sur les mêmes données, un nouveau commit dans la proposition, un changement de configuration, une absence de contrôles ou tout autre refus GitHub interrompent la procédure. La protection de `main` n'est pas contournée. Aucune réécriture automatique de l'historique ni revalidation présumée n'est effectuée.

Les tests hors réseau simulent les trois tentatives, les modifications concurrentes de données, les modifications de code, les propositions déplacées ou modifiées, les refus d'accès, les limites de fichiers, les identités de proposition et l'absence de preuve de fusion.

## Limites

Le mécanisme concerne **la procédure SCDL** dans cette première version. Les autres collecteurs contiennent encore leur propre logique de fusion ; toute généralisation devra examiner leurs conditions et leurs chemins autorisés. La concurrence peut encore se produire entre la dernière inspection et la requête GitHub. Dans ce cas précis, GitHub refuse l'opération et le programme reprend le diagnostic dans ses limites strictes.

La fiabilité de la collecte demeure distincte de la fiabilité de sa publication : un relevé comportant des erreurs partielles doit conserver ces erreurs même si son état est intégré à `main`. L'objectif est la traçabilité et la continuité de connaissance, sans masquer les échecs réseau des producteurs.

Suivi : [problème n° 431](https://github.com/fraware/frontiere-institut-interet-public/issues/431).
