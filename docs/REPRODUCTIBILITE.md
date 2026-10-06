# Reproductibilité

FRONTIÈRE combine logiciel, données publiques et évaluations comparatives. La reproductibilité repose sur la possibilité de reconstruire séparément le comportement du logiciel, l’état du corpus et les décisions méthodologiques.

## Environnement logiciel

Version minimale : Python 3.11.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Sous Windows PowerShell :

```powershell
.venv\Scripts\Activate.ps1
```

## Vérifications minimales

```bash
python -m compileall -q app scripts
pytest
```

La branche principale exécute ces vérifications sur Python 3.11 et 3.12 par GitHub Actions.

## Initialisation d’une démonstration

```bash
python scripts/initialiser_demonstration.py
uvicorn app.main:app --reload
```

Les données de démonstration servent à vérifier le comportement du logiciel. Elles restent distinctes des observations empiriques.

## Reproductibilité du corpus

Les fichiers du répertoire `donnees/` conservent les observations, les chronologies, les analyses successives et les limites de preuve.

Une affirmation empirique importante doit pouvoir être reliée à une source publique identifiée. La précision de la donnée source est conservée : une année reste une année, un mois reste un mois, une estimation reste une estimation.

Les versions antérieures restent disponibles dans l’historique Git afin de reconstruire l’évolution de l’analyse.

## Reproductibilité des évaluations

Les méthodes comparées reçoivent le même cas de départ et le même format de réponse.

Le jeu de développement sert à améliorer le système.

Le jeu réservé sert à mesurer la performance sur des cas séparés du développement. Les références du jeu réservé restent hors du dépôt public. Une empreinte cryptographique publique permet de vérifier que les références utilisées au moment de l’évaluation correspondent au fichier préparé auparavant.

Les réponses produites par un évaluateur doivent être figées avant ouverture des références.

## Séparation des rôles

Une évaluation indépendante exige qu’un évaluateur ne dispose pas des réponses historiques du cas avant de produire sa réponse.

Une personne ayant construit ou consulté les références peut contribuer à l’infrastructure d’évaluation, mais son propre résultat ne constitue pas une mesure indépendante sur ces cas.

## Reproduction d’un résultat empirique

Pour reproduire une conclusion à partir d’un cas :

1. identifier le signal ou le cas concerné ;
2. retrouver la source primaire ou institutionnelle associée ;
3. vérifier la formulation exacte soutenue par cette source ;
4. reconstruire la chronologie avec son degré de précision ;
5. vérifier l’interprétation dans le document d’analyse correspondant ;
6. comparer avec la version Git utilisée pour la conclusion.

## Révisions et corrections

Une correction factuelle doit préciser :

- la formulation antérieure ;
- la nouvelle formulation ;
- la source qui justifie le changement ;
- l’effet éventuel sur les analyses dépendantes.

Une amélioration documentaire qui ne modifie aucune conclusion peut être traitée comme telle.

## Limites actuelles

Le dépôt permet de reproduire la structure logicielle, les données publiques enregistrées et les évaluations de développement.

Les cas prospectifs complets et les comparaisons indépendantes constituent encore des travaux à exécuter. Leur absence doit rester explicite dans toute présentation des résultats.
