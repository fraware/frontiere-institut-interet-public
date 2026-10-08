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
python -m compileall -q app scripts tests
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

### Contrôle automatisé du corpus public

Exécuter `python scripts/verifier_corpus_public.py` pour vérifier conjointement `donnees/signaux_publics_v1.json` et `donnees/chronologies_v3.json`. Le programme contrôle les identifiants, l'unicité des signaux, la couverture des chronologies, la présence de liens de sources et la cohérence entre les valeurs de date et leur degré de précision déclaré (année, mois, jour ou intervalle).

Le rapport distingue les événements possédant une référence propre de ceux qui n'en possèdent pas. **Une référence attachée au signal ne constitue pas une vérification autonome de chacun de ses événements.** Le contrôle structurel ne juge pas l'exactitude des sources et n'améliore pas artificiellement la précision temporelle. Les conclusions exigeant une validation factuelle restent soumises à une relecture documentaire.

Ce contrôle est également exécuté lors des vérifications automatiques du dépôt.

## Reproductibilité des évaluations

Les méthodes comparées reçoivent le même cas de départ et le même format de réponse.

Le jeu de développement sert à améliorer le système.

Le jeu réservé sert à mesurer la performance sur des cas séparés du développement. Les références du jeu réservé restent hors du dépôt public. Une empreinte cryptographique publique permet de vérifier que les références utilisées au moment de l’évaluation correspondent au fichier préparé auparavant.

Les réponses produites par un évaluateur doivent être figées avant ouverture des références.

## Séparation des rôles

Une évaluation indépendante exige qu’un évaluateur ne dispose pas des réponses historiques du cas avant de produire sa réponse.

Une personne ayant construit ou consulté les références peut contribuer à l’infrastructure d’évaluation, mais son propre résultat ne constitue pas une mesure indépendante sur ces cas.

## Mesure des délais

Le calcul `critical_path_minutes` additionne les durées des événements le long des chaînes de dépendance représentées dans un graphe simple à parent unique. Ce calcul ne constitue pas, à lui seul, le délai calendaire observé : deux événements dépendants peuvent comporter des périodes qui se chevauchent.

La fonction `elapsed_span_minutes` mesure séparément le temps entre le premier début et la dernière fin pour un ensemble d'événements achevés. Elle conserve les périodes d'attente et ne compte pas deux fois des intervalles qui se chevauchent. Elle renvoie une valeur inconnue (`None`) si aucun événement n'est fourni ou si un événement reste ouvert ; les fins antérieures aux débuts sont rejetées.

Pour la recherche, les trois mesures suivantes doivent être conservées distinctement : temps de travail humain, somme des durées sur les dépendances et délai calendaire observé. Une mesure issue de la fonction calendaire ne démontre pas, à elle seule, que la première contribution utile a été atteinte : cette date doit être documentée séparément.

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
