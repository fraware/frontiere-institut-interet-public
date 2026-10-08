# Gouvernance de main — transition avant protection

**État : audit et migration à préparer.** Ce document ne prétend pas qu'une règle de branche soit activée. Le contrôle exécuté localement n'accède pas aux réglages administratifs de GitHub.

## Constat vérifié dans les procédures

Cinq procédures actuelles exécutent littéralement une commande de poussée Git vers `main` : importations ROAE, Annuaire local, COG et RNSR, ainsi que surveillance des sources. Le contrôle `python scripts/auditer_ecritures_main.py` énumère ces écritures historiques et fait échouer l'intégration si une **nouvelle procédure** ajoute une écriture directe littérale. Il ne détecte pas les actions tierces ou les commandes construites dynamiquement.

Les ingestions ROAE, Annuaire local et COG fonctionnent actuellement avec dépendances et déclenchements successifs. **Protéger `main` en interdisant les poussées directes avant d'avoir migré ces procédures entraînerait un risque d'interruption des actualisations.**

## Politique cible

- Toute modification de code et de référentiel doit passer par une proposition de fusion avec contrôles obligatoires des environnements Python 3.11 et 3.12 ainsi que du conteneur.
- Interdire les poussées forcées et la suppression de `main`, limiter les contournements et maintenir un registre des identités habilitées.
- Les procédures automatiques ne doivent disposer que des autorisations indispensables. Les essais déclenchés par une proposition externe restent séparés des opérations dotées de droits d'écriture.
- Conserver une preuve vérifiable du contenu exact des sources et de l'état du référentiel utilisé pour chaque génération.
- Ne pas présumer qu'une vérification portant sur les données brutes valide à elle seule la pertinence scientifique de leur interprétation.

## Transition proposée

1. Enregistrer les vérifications obligatoires **réellement présentes** dans les résultats d'intégration continue avant d'éditer une règle de protection.
2. Réunir la chaîne ROAE → Annuaire local → COG dans une orchestration privilégiée distincte des essais externes. Pour chaque nouveau lot, créer une branche technique et une proposition de fusion portant sur les données normalisées et leurs manifestes, sans pousser directement sur `main`.
3. Réexaminer les déclenchements `workflow_run` : aujourd'hui la fin de l'import ROAE signifie aussi la fin de son écriture. Avec une proposition de fusion en attente, cette hypothèse devient fausse. Déclencher les étapes dépendantes après la fusion appropriée ou exécuter leur chaîne dans une même orchestration.
4. Appliquer la même politique au RNSR et à la surveillance, en préservant la sérialisation des écritures qui partagent des fichiers ou des empreintes.
5. Vérifier sur une branche expérimentale les autorisations des jetons, les contrôles de fusion et les réactions aux changements du référentiel. Une fusion automatique exige une identité et des permissions correctement configurées : ne jamais lui accorder un contournement général pour simplifier l'intégration.
6. Activer ensuite la règle administrative `main` et vérifier par lecture des réglages et par essais non destructifs qu'elle est effectivement appliquée. Le ticket n° 54 reste ouvert jusqu'à cette preuve.

## Limites du contrôle livré

L'inventaire des cinq écrivains actuels n'est **pas** une approbation de leurs écritures directes. Il identifie la dette préalable et empêche de l'étendre silencieusement. Une recherche textuelle ne remplace ni un analyseur sémantique de procédures YAML, ni une inspection des actions tierces ou des réglages GitHub.

Le connecteur GitHub actuel n'expose pas une action d'administration permettant de modifier directement les règles de protection. Leur activation n'est donc pas revendiquée.
