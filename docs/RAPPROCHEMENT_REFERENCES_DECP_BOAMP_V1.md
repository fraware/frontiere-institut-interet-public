# Premier rapprochement prudent des références DECP et BOAMP

## Objectif et portée

Ce programme constitue une **présélection documentaire**, pas un répertoire de contrats juridiquement identifiés. Il rapproche l'identifiant de marché déclaré dans les données essentielles de la commande publique (DECP) avec la **référence interne de procédure** contenue dans les formulaires officiels eForms des avis BOAMP déjà capturés. Ces deux identifiants n'ont pas nécessairement la même portée. Même une égalité exacte après normalisation ne prouve pas qu'il s'agit du même contrat.

Le premier travail ne prétend donc aucune correspondance contractuelle vérifiée. Le contrôle supplémentaire de l'identité de l'acheteur peut renforcer certaines pistes, sans transformer une référence de procédure en identifiant contractuel certain. Il ne modifie ni l'index commun AIFE/DGFiP, ni son compteur de correspondances contractuelles vérifiées, qui reste égal à zéro.

## Sources et preuve

L'outil accepte les deux relevés complets qui alimentent déjà l'index DECP :

- `institutionnel/decp/sonde_aife_json.json` ;
- `institutionnel/decp/lot_dgfip_xml.json`.

Il réutilise les contrôles de provenance et de complétude de l'indexeur commun. Une ressource tronquée, un nombre de marchés discordant ou une identité documentaire invalide empêchent toute production de résultats. L'identité DECP est toujours le couple **SIRET de l'acheteur + identifiant du marché** ; plusieurs fichiers ou plusieurs versions d'une même identité ne constituent pas plusieurs contrats.

Pour le BOAMP, l'outil lit un ou plusieurs dossiers de **captures officielles** produits par `scripts/collecter_notices_pilotes_boamp.py`. Il revalide le manifeste, les identifiants, les dates et les empreintes SHA-256 avant d'interpréter une seule référence. Il conserve, dans chaque piste, l'identifiant de l'avis, l'URL interrogée, l'empreinte de la réponse et le chemin exact du champ eForms `cac:ProcurementProject/cbc:ID`. Le champ `nomacheteur` n'est conservé qu'à titre de renseignement documentaire ; il ne remplace jamais la vérification du SIRET.

Seuls les formulaires `EFORMS/ContractNotice` et `EFORMS/ContractAwardNotice` dont le chemin est connu sont interprétés. Les autres formats sont comptés comme inconnus, sans extraction par recherche textuelle arbitraire.

### Qualification complémentaire de l'acheteur

`scripts/extraire_references_boamp_decp.py` est utilisé par le rapprocheur historique. Il réutilise les captures BOAMP validées et ne confond jamais un SIRET de titulaire avec celui de l'acheteur. Le rôle d'acheteur doit être documenté par `cac:ContractingParty`. Le SIRET est accepté seulement si l'identifiant de l'entité acheteuse est explicitement marqué `SIRET` ou `FR-SIRET` (variantes de séparateur contrôlées), soit directement, soit par une correspondance univoque avec `efac:Organizations` et `cac:PartyLegalEntity/cbc:CompanyID`.

L'extraction conserve séparément le chemin de l'identifiant de projet et celui du SIRET de l'acheteur. Les acheteurs multiples, références de projet manquantes, organismes sans rattachement univoque, identifiants à rôle inconnu et formats non pris en charge ne produisent aucune identité déduite. L'examen n'effectue aucune recherche générale de nombres à quatorze chiffres dans l'avis.

Pour une référence de procédure commune à plusieurs avis, la confirmation d'un SIRET concordant n'est enregistrée que si les SIRET d'acheteurs déterminés sur ces avis ne sont pas contradictoires et si ce SIRET figure parmi les identités DECP candidates. Les avis dépourvus d'identité exploitable restent inconnus, sans preuve positive supplémentaire. Les résultats exposent `pistes_avec_concordance_de_siret`, `acheteur_boamp_identifie_dans_role`, `chemin_preuve_siret` et `plusieurs_acheteurs_declares_dans_les_avis`.

**Limite de compatibilité :** le lecteur de SIRET traite certaines structures eForms précisément définies. Un avis réel employant une autre structure sera classé comme non interprétable pour l'acheteur. Les tests structurels utilisent des formulaires artificiels ; la capacité à extraire ces champs des avis réels exige une mesure explicite lors d'une collecte officielle. Le compteur des correspondances contractuelles vérifiées reste nul, y compris si une référence interne et un SIRET sont identiques.


## Reproduire hors réseau

Extraire d'abord une archive officielle produite par la procédure de capture des pilotes (contenant `rapport.json` et les réponses `26-xxxxx.json`). Puis exécuter :

```bash
python scripts/rapprocher_references_decp_boamp.py \
  --aife institutionnel/decp/sonde_aife_json.json \
  --dgfip institutionnel/decp/lot_dgfip_xml.json \
  --captures /chemin/captures-notices-pilotes \
  --sortie /tmp/frontiere-rapprochements-decp-boamp.json

python -m pytest -q tests/test_rapprocher_references_decp_boamp.py tests/test_extraire_references_boamp_decp.py
```

L'argument `--captures` est répétable pour plusieurs lots de captures complets. La sortie n'est pas ajoutée automatiquement au dépôt. Le dispositif existant de captures primaires des six pilotes BOAMP exécute aussi ce rapprochement au cours de ses passages hebdomadaires et lors des modifications du programme : son rapport est joint à l'archive GitHub Actions, avec les réponses primaires correspondantes. Une exécution interrompue ou un fichier absent n'autorise aucun résultat de substitution.

## Interprétation des résultats

Une référence partagée par un seul couple SIRET + identifiant de marché produit `reference_commune_non_suffisante`. Une concordance explicite de SIRET constitue un champ indépendant de qualification, sans changement de ce classement. Si plusieurs identités contractuelles partagent cette référence normalisée, le résultat est `reference_partagee_plusieurs_identites_de_marche`. Plusieurs **avis** avec la même référence ne sont pas additionnés comme plusieurs marchés.

La normalisation neutralise la ponctuation et les accents ; elle est uniquement une aide à la recherche. Les références trop courtes sont exclues. Le programme indique toujours `identite_contractuelle_verifiee=false` et `correspondances_contractuelles_verifiees=0`.

Un passage à la classe « correspondance contractuelle vérifiée » demanderait encore de contrôler l'identifiant **contractuel** au sens exact des deux circuits, la relation entre projet, procédure, lot et contrat, les versions documentaires, les dates et les éventuelles contradictions. Ce contrôle est **un chantier distinct**, qui exige les documents primaires correspondants et ne peut pas être inféré à partir du seul intitulé.

Une attribution ne démontre ni un besoin actuel, ni une pénurie de compétences, ni le commencement d'exécution ou la date de première contribution utile.

## Limitation actuelle

Les captures BOAMP déjà réalisées sont un ensemble pilote de petite taille. Une absence de rapprochement ne prouve aucune absence de contrat correspondant dans BOAMP. La première extension empirique utile consistera à exploiter davantage de notices officielles complètes avec leur provenance, sans élargir prématurément la catégorie des liens confirmés.
