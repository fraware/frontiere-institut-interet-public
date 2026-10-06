# Contribuer à FRONTIÈRE

FRONTIÈRE est à la fois un prototype logiciel et un dispositif de recherche empirique. Une contribution utile doit préserver cette double exigence : qualité technique et intégrité de la preuve.

## Avant de proposer une modification

Une modification doit répondre à au moins une question concrète :

- améliore-t-elle la définition d’un besoin réel ?
- améliore-t-elle l’identification ou la vérification d’une capacité ?
- améliore-t-elle l’analyse de la mobilisabilité d’une ressource ?
- améliore-t-elle la mesure d’un délai, d’un coût ou d’un résultat ?
- améliore-t-elle la traçabilité, la reproductibilité ou la sécurité ?
- améliore-t-elle la compréhension du projet sans introduire une nouvelle affirmation non étayée ?

Les fonctions sans lien direct avec ces objectifs restent hors du périmètre.

## Intégrité de la recherche

Les contributions portant sur les données ou les conclusions suivent les règles suivantes.

**Provenance.** Toute affirmation empirique importante conserve une source identifiable.

**Précision temporelle.** Une date partielle reste partielle. Une estimation reste une estimation.

**Séparation des faits et des interprétations.** Les fichiers de données enregistrent les observations ; les documents d’analyse distinguent explicitement ce qui est observé de ce qui est interprété.

**Conservation des résultats négatifs.** Les cas où un mécanisme existant fonctionne correctement sont conservés.

**Absence de réécriture silencieuse.** Une correction substantielle doit être versionnée et expliquée.

**Protection des jeux d’évaluation.** Les références réservées ne doivent jamais être introduites dans les fichiers publics ni consultées par un évaluateur censé travailler en aveugle.

## Données sensibles

Le dépôt est public.

Aucune contribution ne doit contenir de secret, donnée personnelle confidentielle, élément de sécurité, conflit d’intérêts sensible, dossier individuel ou information soumise à une restriction d’accès.

Consulter [SECURITE.md](SECURITE.md) avant d’ajouter des données.

## Environnement local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Sous Windows PowerShell :

```powershell
.venv\Scripts\Activate.ps1
```

## Avant une demande de fusion

Exécuter :

```bash
python -m compileall -q app scripts tests
pytest
```

Vérifier également :

- les fichiers JSON sont valides ;
- les nouvelles données possèdent une provenance ;
- les nouveaux documents figurent dans `docs/INDEX.md` lorsque leur portée est durable ;
- la documentation décrit l’état réel du système ;
- aucun exemple artificiel n’est présenté comme observation empirique ;
- aucune information sensible n’a été ajoutée.

## Structure des modifications

Privilégier une modification cohérente par demande de fusion.

Les changements empiriques doivent expliquer :

1. la question étudiée ;
2. la nouvelle preuve ;
3. la limite de cette preuve ;
4. l’effet éventuel sur une conclusion antérieure.

Les changements logiciels doivent expliquer :

1. le comportement actuel ;
2. le comportement recherché ;
3. le test qui établit le nouveau comportement.

## Conventions de rédaction

La documentation publique est rédigée en français clair. Les règles détaillées figurent dans [docs/PRINCIPES_REDACTION.md](docs/PRINCIPES_REDACTION.md).

Les termes techniques nécessaires sont définis dans [docs/REPERES_DE_LECTURE.md](docs/REPERES_DE_LECTURE.md).

## Relecture

Une relecture porte séparément sur :

- exactitude technique ;
- exactitude empirique ;
- cohérence méthodologique ;
- sécurité des données ;
- clarté documentaire.

Une demande de fusion peut être techniquement correcte et rester insuffisante sur l’un de ces autres critères.
