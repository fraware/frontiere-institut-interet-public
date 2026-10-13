# Vérification administrative des 16 identifiants d'acheteurs BOAMP

## Sources et question mesurée

Le tirage indépendant de 36 avis BOAMP, examiné dans le [relevé d'indexation 38474330466](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38474330466), a produit 17 observations d'identifiants à quatorze chiffres sans schéma déclaré, correspondant à **16 chaînes distinctes**. Le fichier `audit-identifiants-acheteurs-36.json` est figé par son empreinte SHA-256 :

`3626f84ccf9a39ce6d8882f0d5f7463eb6bde860c90a26904a6992f5fed791e3`

Les numéros sont ceux déclarés dans le champ de l'entité acheteuse, et non ceux des entreprises attributaires. La vérification est **transversale au corpus**, elle ne réinterprète pas le tirage initial et ne change aucun statut contractuel.

L'[API Recherche d'entreprises](https://recherche-entreprises.api.gouv.fr/docs/), gérée dans le cadre de l'annuaire public des entreprises, documente une recherche directe par SIREN ou SIRET dans `q`. Elle reconnaît explicitement son **caractère non exhaustif**. Une requête négative signifie seulement « non retrouvé par cette API à cet instant ». Il est interdit d'en déduire l'inexistence d'un établissement dans Sirene.

## Traitement

Le programme `scripts/verifier_identifiants_acheteurs_api_entreprises.py` charge l'audit BOAMP et contrôle ses unités, ses dénominateurs et la provenance par avis. Le contrôle arithmétique de Luhn est **une vérification de forme**, sans portée administrative.

Pour chaque numéro distinct, le programme interroge l'API à un débit inférieur à une requête par seconde en moyenne. Il interdit les redirections, impose un plafond de taille, gère de manière bornée les réponses HTTP 429 et ne publie aucun résultat partiel en cas de défaillance du service. Chaque réponse est conservée **octet pour octet** avec son empreinte SHA-256, son adresse, sa date de relevé et le ou les avis BOAMP correspondants.

Les réponses sont catégorisées selon des critères stricts :

- `siret_exact_retourne_par_api_publique` : la réponse de recherche directe contient le SIRET exact dans un champ **d'établissement** (`siege.siret` ou `matching_etablissements[].siret`), au sein de l'unité légale dont le SIREN concorde.
- `unite_legale_associee_etablissement_non_atteste` : l'API retourne une unité légale au SIREN concordant, sans attestation explicite de l'établissement demandé.
- `non_retrouve_dans_api_non_exhaustive` : aucun résultat retourné par cette interface.
- `reponse_sans_identite_exacte` : des résultats sont présents, sans correspondance documentaire de l'unité légale.

Une réponse ne répondant pas au schéma attendu interrompt la publication, afin d'éviter des résultats faussement négatifs. Aucun résultat n'est qualifié comme « SIRET inexistant ».

## Reproduction

La procédure ponctuelle `.github/workflows/verifier-identifiants-acheteurs-boamp.yml` relit directement l'artefact préexistant de GitHub, **vérifie son empreinte fixée**, exécute les tests sans réseau, effectue les 16 recherches directes et conserve le rapport avec toutes les réponses intégrales pendant 30 jours. La procédure est déclenchée une seule fois lors de l'intégration du programme sur `main`, avec possibilité d'exécution manuelle ultérieure tant que l'archive source est disponible. Les archives GitHub ont une durée de conservation : toute réexécution tardive nécessitera un fichier source ayant conservé sa provenance et sa vérification d'intégrité.

Exécution locale avec une archive BOAMP validée :

```bash
python -m pytest -q tests/test_verifier_identifiants_acheteurs_api_entreprises.py
python scripts/verifier_identifiants_acheteurs_api_entreprises.py \
  --audit-boamp /chemin/audit-identifiants-acheteurs-36.json \
  --sortie /chemin/verification-acheteurs-16
```

La sortie comporte `rapport.json` et un fichier JSON brut par numéro consulté. Le résultat ne doit pas être confondu avec les données complètes de l'API Sirene de l'Insee.

## Périmètre exact des conclusions

Trois niveaux d'observation restent distincts : (1) la chaîne à quatorze chiffres et sa conformité arithmétique, (2) la présence du SIRET exact parmi les établissements explicitement retournés par l'interface publique, (3) le rattachement documentaire et juridique de cette identité au pouvoir adjudicateur et au contrat. Le programme n'exécute que les niveaux 1 et 2.

Il ne reconstitue aucune correspondance contractuelle BOAMP–DECP, aucune relation lot–contrat ni aucune date d'exécution. Aucun nombre de besoins scientifiques non satisfaits ne saurait être inféré du présent bilan. Un résultat positif permet seulement de prioriser les cas à reconstituer depuis les documents primaires.
