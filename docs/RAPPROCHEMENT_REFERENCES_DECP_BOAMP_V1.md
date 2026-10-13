# Premier rapprochement prudent des références DECP et BOAMP

## Objectif et portée

Ce programme constitue une **présélection documentaire**, pas un répertoire de contrats juridiquement identifiés. Il rapproche l'identifiant de marché déclaré dans les données essentielles de la commande publique (DECP) avec la **référence interne de procédure** contenue dans les formulaires officiels eForms des avis BOAMP déjà capturés. Ces deux identifiants n'ont pas nécessairement la même portée. Même une égalité exacte après normalisation ne prouve pas qu'il s'agit du même contrat.

Le premier travail ne prétend donc aucune correspondance contractuelle vérifiée. Il ne modifie ni l'index commun AIFE/DGFiP, ni son compteur de correspondances BOAMP, actuellement égal à zéro.

## Sources et preuve

L'outil accepte les deux relevés complets qui alimentent déjà l'index DECP :

- `institutionnel/decp/sonde_aife_json.json` ;
- `institutionnel/decp/lot_dgfip_xml.json`.

Il réutilise les contrôles de provenance et de complétude de l'indexeur commun. Une ressource tronquée, un nombre de marchés discordant ou une identité documentaire invalide empêchent toute production de résultats. L'identité DECP est toujours le couple **SIRET de l'acheteur + identifiant du marché** ; plusieurs fichiers ou plusieurs versions d'une même identité ne constituent pas plusieurs contrats.

Pour le BOAMP, l'outil lit un ou plusieurs dossiers de **captures officielles** produits par `scripts/collecter_notices_pilotes_boamp.py`. Il revalide le manifeste, les identifiants, les dates et les empreintes SHA-256 avant d'interpréter une seule référence. Il conserve, dans chaque piste, l'identifiant de l'avis, l'URL interrogée, l'empreinte de la réponse et le chemin exact du champ eForms `cac:ProcurementProject/cbc:ID`. Le champ `nomacheteur` n'est conservé qu'à titre de renseignement documentaire ; il ne remplace jamais la vérification du SIRET.

Seuls les formulaires `EFORMS/ContractNotice` et `EFORMS/ContractAwardNotice` dont le chemin est connu sont interprétés. Les autres formats sont comptés comme inconnus, sans extraction par recherche textuelle arbitraire.

## Reproduire hors réseau

Extraire d'abord une archive officielle produite par la procédure de capture des pilotes (contenant `rapport.json` et les réponses `26-xxxxx.json`). Puis exécuter :

```bash
python scripts/rapprocher_references_decp_boamp.py \
  --aife institutionnel/decp/sonde_aife_json.json \
  --dgfip institutionnel/decp/lot_dgfip_xml.json \
  --captures /chemin/captures-notices-pilotes \
  --sortie /tmp/frontiere-rapprochements-decp-boamp.json

python -m pytest -q tests/test_rapprocher_references_decp_boamp.py
```

L'argument `--captures` est répétable pour plusieurs lots de captures complets. La sortie n'est publiée nulle part automatiquement.

## Interprétation des résultats

Une référence partagée par un seul couple SIRET + identifiant de marché produit `reference_commune_non_suffisante`. Si plusieurs identités contractuelles partagent cette référence normalisée, le résultat est `reference_partagee_plusieurs_identites_de_marche`. Plusieurs **avis** avec la même référence ne sont pas additionnés comme plusieurs marchés.

La normalisation neutralise la ponctuation et les accents ; elle est uniquement une aide à la recherche. Les références trop courtes sont exclues. Le programme indique toujours `identite_contractuelle_verifiee=false` et `correspondances_contractuelles_verifiees=0`.

Un passage à la classe « correspondance contractuelle vérifiée » demanderait au minimum de contrôler les identifiants de l'acheteur et du contrat dans les **champs officiels pertinents**, leur unité d'analyse (procédure, lot ou contrat), les variantes documentaires, les dates et les éventuelles contradictions. Ce contrôle est **un chantier distinct**, qui exige les documents primaires correspondants et ne peut pas être inféré à partir du seul intitulé.

Une attribution ne démontre ni un besoin actuel, ni une pénurie de compétences, ni le commencement d'exécution ou la date de première contribution utile.

## Limitation actuelle

Les captures BOAMP déjà réalisées sont un ensemble pilote de petite taille. Une absence de rapprochement ne prouve aucune absence de contrat correspondant dans BOAMP. La première extension empirique utile consistera à exploiter davantage de notices officielles complètes avec leur provenance, sans élargir prématurément la catégorie des liens confirmés.
