# Chaînes documentaires entre acheteurs, procédures, lots et contrats

## Périmètre

Cette étude porte sur **17 avis BOAMP** issus du tirage indépendant de 36 avis. Ils contiennent 16 identifiants distincts d'acheteurs, chacun retrouvé exactement dans un établissement retourné par l'API publique Recherche d'entreprises le 13 octobre 2026. L'échantillon initial est enrichi en sujets techniques et ne représente pas le volume national des marchés publics.

Le programme `scripts/reconstituer_chaines_acheteurs_boamp_decp.py` assemble **trois sources déjà archivées**, sans accès réseau :

- le tirage indépendant et les 36 réponses BOAMP primaires, avec l'audit des identifiants ;
- le rapport et les seize réponses administratives d'origine, sans conversion ;
- les références explicites de procédure, de lot, de décision et de contrat conservées dans les formulaires eForms de ces mêmes avis.

Les deux archives officielles sont les exécutions GitHub [38474330466](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38474330466) et [38478573359](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38478573359). Les contrôles d'intégrité fixés portent sur le fichier d'audit des 36 avis (`3626f84ccf9a39ce6d8882f0d5f7463eb6bde860c90a26904a6992f5fed791e3`) et le rapport administratif (`d8e4e7570eef4c2313b1a243114473bf5075aa1aa135e8e793bfd907177576fd`).

## Critères de correspondance et de preuve

Le lien entre le rôle d'acheteur `cac:ContractingParty` et l'organisme `efac:Organizations` est reconstitué à partir d'un identifiant de rôle exactement identique et d'un unique numéro d'établissement attaché à cet organisme. Un fournisseur, une autre partie prenante ou un numéro présent ailleurs dans l'avis ne sont jamais utilisés comme identité de l'acheteur.

Le numéro d'établissement est confronté à la réponse administrative officielle conservée. Le contrôle exige la présence du **SIRET exact dans le champ d'un établissement** retourné sous le SIREN concordant. Le libellé de l'avis, le nom de l'organisme eForms et la dénomination administrative sont conservés séparément. Une identité textuelle, même exacte, n'est pas une démonstration juridique des pouvoirs de l'acheteur.

La référence interne de procédure est extraite exclusivement de `cac:ProcurementProject/cbc:ID`. Son absence demeure explicite. Le champ `cbc:ContractFolderID` correspond à la référence documentaire de l'avis, **sans conversion en numéro de marché**.

Les lots sont extraits exclusivement de `cac:ProcurementProjectLot/cbc:ID`. Pour les **avis d'attribution**, l'analyseur existant lit les résultats de lots et les contrats déclarés dans `efac:NoticeResult`. Une relation locale `lot → contrat` est retenue seulement si le lot est déclaré dans l'avis et si la référence contractuelle citée par son résultat appartient aux contrats définis dans le même avis. Les doublons et références sans définition interrompent l'examen. Les désignations `LOT-0001`, `CON-0001` et `RES-0001` sont locales à l'avis, et non des clés utilisables sans contexte dans les données essentielles de la commande publique.

## Résultats documentaires et prudence

L'examen des archives originales a identifié 17 avis, dont 6 attributions, 15 références internes de procédure renseignées, 27 lots, 9 résultats de lots et 9 références de contrats reliées au sein de leurs avis. Ces comptes sont revérifiés par le programme sur les trois sources et publiés dans le rapport d'exécution ; une anomalie empêche toute production.

Le cas `25-93431` présente l'intitulé « MINARM » dans l'avis, avec un établissement intitulé « SERVICES DE L'ÉTAT POUR LA FACTURATION ÉLECTRONIQUE » dans la réponse administrative. La différence de dénomination est un **signal de vérification**, non une erreur juridique établie. Les avis `25-108230` et `26-60102` réutilisent le même SIRET administratif tout en employant des dénominations de services opérationnels distinctes. Ces cas ne sont pas additionnés comme deux établissements.

Aucune correspondance contractuelle avec un identifiant de marché DECP n'est encore démontrée. L'étude ne vérifie pas les délégations de signature, la représentation légale de l'acheteur, les pièces originales du contrat, la date de début d'exécution, la première contribution utile ou un déficit de compétences.

## Reproduction

```bash
python -m pytest -q tests/test_reconstituer_chaines_acheteurs_boamp_decp.py
python scripts/reconstituer_chaines_acheteurs_boamp_decp.py \
  --tirage /sources/boamp/echantillon-independant-technique.json \
  --releve /sources/boamp/releve-issues-36 \
  --audit-boamp /sources/boamp/audit-identifiants-acheteurs-36.json \
  --administration /sources/administration \
  --sortie /tmp/frontiere-chaines-documentaires.json
```

La procédure `.github/workflows/chaines-documentaires-acheteurs-boamp.yml` télécharge les deux archives GitHub déjà publiées, vérifie leurs empreintes, relit les 36 réponses d'origine et produit ce bilan en pièce jointe téléchargeable. Aucun nouveau prélèvement n'est effectué auprès du BOAMP ou de l'API administrative.

La suite devra rapprocher, au cas par cas, les unités procédure–lot–contrat de la nomenclature DECP, puis rechercher les avis de consultation, les avis d'attribution et les documents contractuels correspondants. Une concordance arithmétique ou textuelle ne suffit pas pour classer ce lien comme démontré.
