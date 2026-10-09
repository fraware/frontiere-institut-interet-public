# Publication des actualisations institutionnelles — première étape

Le code de référence peut être modifié par des procédures automatiques. L'objectif est de préparer **une proposition de fusion** pour chaque lot d'actualisation, avec vérifications et décision de fusion distinctes.

## Invariants de publication

L'outil `scripts/publier_mise_a_jour_institutionnelle.py` accepte trois périmètres fermés de fichiers : structures publiques de recherche, surveillance des sources et chaîne administrative et territoriale. Une modification non prévue entraîne un refus explicite. L'outil vérifie la concordance entre le point de départ de la collecte et la dernière version de `main`, afin d'éviter de publier un lot calculé à partir de référentiels périmés.

Un seul lot en attente par source est autorisé. L'identifiant de branche est déterminé par le numéro de la procédure GitHub et sa tentative, sans date inventée ni remplacement forcé. Aucun lot n'est fusionné automatiquement. Les noms de fichiers sont passés aux commandes par arguments distincts, sans exécution de contenu provenant des sources administratives.

La commande de vérification est locale et **sans écriture distante** :

```bash
python scripts/publier_mise_a_jour_institutionnelle.py --source rnsr
python scripts/publier_mise_a_jour_institutionnelle.py --source surveillance
python scripts/publier_mise_a_jour_institutionnelle.py --source referentiel
```

L'option `--publier` est réservée aux procédures GitHub ayant le droit explicite de créer des branches et des propositions. Elle exige une exécution sur `main`, une identité de dépôt et un jeton disponible uniquement lors de la publication.

## Vérifications automatisées des nouvelles propositions

Une proposition ouverte à l'aide du jeton propre aux procédures GitHub ne déclenche normalement pas une nouvelle exécution de toutes les procédures associées aux propositions de fusion. L'outil ordonne donc explicitement le lancement des `Vérifications` sur la branche générée. La procédure `ci.yml` accepte pour cela un déclenchement à la demande. Les trois résultats de référence sont Python 3.11, Python 3.12 et conteneur.

Le jeton de publication doit pouvoir écrire une branche, ouvrir une proposition et déclencher une vérification. Les réglages du dépôt doivent autoriser les propositions créées par les procédures automatisées. Le jeton n'est transmis qu'à l'étape de publication, et les informations d'authentification ne sont pas conservées lors de la récupération initiale du dépôt.

La création de la branche ou de la proposition **n'implique pas** que les vérifications soient réussies. Une fusion demande une confirmation explicite des résultats et des autorisations prévues par la politique de protection de `main`.

## Transition des collectes

La première migration concerne les sources sans dépendance sur les autres importations : structures publiques de recherche et surveillance des sources. Les procédures de contrôle des propositions externes gardent des droits en lecture seule.

La chaîne liée doit ensuite traiter dans **la même version de travail** l'organisation administrative de l'État, puis l'Annuaire des services locaux, puis les territoires. Les contrôles de couverture, de relations et de variation doivent être conservés entre les étapes. Les déclenchements historiques à la fin des procédures ne seront retirés qu'une fois ce parcours validé.

## Conditions restant à démontrer

- Le dépôt autorise effectivement les propositions créées par le jeton de procédure GitHub et le déclenchement explicite des contrôles.
- Les trois résultats automatiques apparaissent sur la bonne révision de la branche technique.
- Le traitement d'une source inchangée ne crée aucune nouvelle proposition.
- Une proposition déjà ouverte bloque les doubles créations.
- Les collectes indépendantes, la chaîne dépendante et les alertes critiques conservent leur comportement prévu.

Aucune règle d'administration protégeant `main` n'est activée par cet outil. Les dossiers sensibles et les références privées sont exclus de ses périmètres.
