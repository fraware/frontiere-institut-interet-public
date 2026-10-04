# FRONTIÈRE - INSTITUT POUR L’INTÉRÊT PUBLIC - — prototype opératoire v0.2

Prototype interne pour l'étude de la mobilisation des capacités scientifiques et techniques au service de l'action publique.

## Objet

FRONTIÈRE - INSTITUT POUR L’INTÉRÊT PUBLIC - ne présume ni d'une place de marché de talents, ni d'une nouvelle institution. Le prototype sert à documenter des épisodes réels, qualifier le besoin, rechercher d'abord les capacités publiques pertinentes, comparer les voies de résolution, conserver les décisions et mesurer ce qui devient réutilisable d'un cas au suivant.

La chaîne de travail est :

`Besoin → Capacité → Ressource → Intervention → Décision → Résultat → Connaissance réutilisable`

Une solution publique existante, une prestation de marché, un recrutement permanent, un abandon justifié ou l'absence de nouvelle intervention constituent des résultats valides.

## Ce que la version 0.2 réalise

- registre des épisodes avec D0–D4 et distinction entre cas réels et cas synthétiques ;
- formulation du besoin, résultat attendu, responsable, échéance, contrefactuel et hypothèse initiale ;
- recherche prioritaire dans le secteur public avec classification conservatrice P0/P1/P2/P3 ;
- registre de capacités, ressources, recherches, découvertes R0–R5 et voies possibles au niveau du modèle de données ;
- journal des décisions avec éléments contradictoires et incertitudes ;
- modèle des frictions et dépendances pour calculer le chemin critique ;
- résultats et additionalité par dimensions séparées ;
- connaissances réutilisables et événements de réutilisation ;
- registre pré-enregistré des quinze hypothèses de plateforme ;
- douze scénarios synthétiques adverses séparés des données réelles ;
- interface interne légère et API de lecture ;
- pré-enregistrement du besoin et du contrefactuel avant investigation ;
- registre des preuves A–E avec environnement de données ;
- registre opérationnel des interlocuteurs avec règle preuve / cas / expérience / mise en relation ;
- export de recherche minimal et non sensible ;
- tests automatisés des invariants méthodologiques essentiels.

## Lancer localement

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/seed_demo.py
uvicorn app.main:app --reload
```

Puis ouvrir `http://127.0.0.1:8000`.

Tests :

```bash
pytest
```

## Principes non négociables

1. Un épisode réel garde la possibilité de conclure que Frontière n'était pas nécessaire.
2. P2 ne devient jamais P3 parce qu'une mobilité échoue.
3. Une disponibilité ancienne n'est jamais assimilée à une disponibilité actuelle.
4. Une personne identifiée n'est jamais assimilée à une ressource mobilisable.
5. Les décisions critiques conservent preuves, contradictions, incertitudes et contexte historique.
6. Les résultats négatifs et les mécanismes existants satisfaisants sont conservés.
7. Les informations sensibles restent séparées par finalité et niveau d'accès.
8. Aucun score global ne remplace les portes ou dimensions distinctes.
9. Les cas synthétiques sont exclus des statistiques opérationnelles par défaut.
10. Le logiciel structure et calcule ; les décisions institutionnelles importantes restent humaines.

## Documentation

- `docs/PROTOCOLE_V1.1.md` — protocole consolidé avant premiers cas réels.
- `docs/MODELE_DONNEES_V0.2.md` — schéma conceptuel et invariants.
- `docs/REGLES_DECISION.md` — D0–D4, P0–P3, R0–R5, orientation et clôture.
- `docs/SECURITE_GOUVERNANCE.md` — séparation des données et règles d'accès.
- `docs/PLAN_12_SEMAINES.md` — cadence de l'exécution contrôlée.
- `docs/LANCEMENT_OPERATIONNEL.md` — première vague et règles de bascule vers les cas réels.

## Périmètre actuel

Cette version est un outil de recherche et d'opérations internes. Elle ne constitue ni un système de recrutement automatisé, ni une base publique de réputation, ni une plateforme nationale finalisée. Les abstractions seront modifiées uniquement à partir d'observations réelles, avec historique des versions.


## Sécurité de la version publique

Cette version ne possède pas encore d’authentification. Elle refuse les niveaux de sensibilité 3 et 4. Ne saisir aucune donnée confidentielle ou nominative restreinte dans une instance publique. Voir `SECURITY.md`.
