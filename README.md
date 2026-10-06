# FRONTIÈRE — INSTITUT POUR L’INTÉRÊT PUBLIC

FRONTIÈRE est un outil de recherche et d'expérimentation consacré à une question pratique : comment une institution publique trouve-t-elle et mobilise-t-elle, au bon moment, la capacité scientifique ou technique dont elle a besoin ?

Le projet ne suppose pas qu'une nouvelle structure soit nécessaire. Il compare les solutions déjà disponibles, recherche les capacités pertinentes, suit les délais et les obstacles, puis conserve ce qui peut être réutilisé dans des cas futurs.

## Chaîne de travail

`Besoin → Capacité nécessaire → Ressource possible → Voie de mobilisation → Décision → Résultat → Connaissance réutilisable`

Une ressource peut être une personne, une équipe, un laboratoire, un organisme, un prestataire, un outil, une donnée, une infrastructure ou un service.

## Ce que l'application permet aujourd'hui

L'application permet de :

- enregistrer un cas réel et son besoin initial ;
- conserver les versions successives du besoin ;
- rechercher d'abord les capacités déjà présentes dans le secteur public ;
- enregistrer les ressources trouvées et le degré de vérification de chacune ;
- comparer plusieurs voies de résolution ;
- suivre les délais et les obstacles ;
- enregistrer le résultat obtenu, le coût et le temps consacré ;
- conserver les connaissances utiles à d'autres cas ;
- comparer plusieurs méthodes de recherche sur un même ensemble de cas ;
- distinguer les cas réels des cas de démonstration.

Les décisions importantes restent humaines. Le logiciel sert à structurer les faits, conserver les preuves et rendre les comparaisons reproductibles.

## Lire les documents

Les documents principaux sont :

- `docs/PROTOCOLE_V1.1.md` — ce qui est observé dans chaque cas et comment les conclusions sont établies ;
- `docs/MODELE_DONNEES_V0.2.md` — les objets enregistrés par l'application ;
- `docs/REGLES_DECISION.md` — les règles utilisées pour qualifier une situation et choisir une voie ;
- `docs/SECURITE_GOUVERNANCE.md` — les règles de protection et de séparation des données ;
- `docs/PLAN_12_SEMAINES.md` — la séquence de travail sur les douze premières semaines ;
- `docs/LANCEMENT_OPERATIONNEL.md` — la première vague de cas et d'interlocuteurs ;
- `docs/TRACEABILITE_V0.3.md` — la conservation de l'historique des décisions ;
- `docs/EVALUATION_TECHNIQUE_V0.5.md` — la comparaison des méthodes de recherche ;
- `evaluation/CAS_RETROSPECTIFS_DEVELOPPEMENT.md` — les douze cas historiques utilisés pour comparer les méthodes pendant le développement ;
- `docs/REPERES_DE_LECTURE.md` — les termes utilisés dans le projet, expliqués en langage courant.
- `docs/PRINCIPES_REDACTION.md` — les règles de rédaction en français clair.
- `docs/PLAN_SOURCES_PUBLIQUES.md` — le programme de constitution du corpus public.
- `donnees/README.md` — les règles du corpus de signaux publics.

## Évaluation technique

Le projet utilise deux ensembles distincts :

- un **jeu de développement** de vingt cas publics, utilisé pour améliorer le système ;
- un **jeu réservé** de dix cas, utilisé pour vérifier les performances sur des cas qui n'ont pas servi au développement.

Les réponses de référence du jeu réservé sont conservées hors du dépôt public. Le dépôt contient seulement les questions et une empreinte cryptographique permettant de vérifier que les réponses de référence n'ont pas été modifiées après le lancement de l'évaluation.

Les fichiers publics de cette évaluation se trouvent dans le dossier `evaluation/`.

## Sécurité

Le dépôt est public. L'application actuelle n'est pas destinée à recevoir des informations confidentielles, sensibles ou nominatives restreintes. Les règles détaillées figurent dans `SECURITE.md` et `docs/SECURITE_GOUVERNANCE.md`.

## Lancer l'application localement

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/initialiser_demonstration.py
uvicorn app.main:app --reload
```

Puis ouvrir `http://127.0.0.1:8000`.

Pour exécuter les vérifications automatiques :

```bash
pytest
```

## Principe de développement

Une nouvelle fonction n'est ajoutée que si elle améliore directement l'une des opérations suivantes : comprendre le besoin, trouver une capacité, vérifier une ressource, déterminer si elle peut réellement être mobilisée, mesurer le résultat ou réutiliser une connaissance acquise sur un cas précédent.
