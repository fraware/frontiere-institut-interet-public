# Gouvernance de main — transition avant protection

**État : audit et migration à préparer.** Ce document ne prétend pas qu'une règle de branche soit activée. Le contrôle exécuté localement n'accède pas aux réglages administratifs de GitHub.

## Constat vérifié dans les procédures

Cinq procédures actuelles exécutent littéralement une commande de poussée Git vers `main` : importations référentiel de l'organisation administrative de l'État, Annuaire local, COG et RNSR, ainsi que surveillance des sources. Le contrôle `python scripts/auditer_ecritures_main.py` énumère ces écritures historiques et fait échouer l'intégration si une **nouvelle procédure** ajoute une écriture directe littérale. Il ne détecte pas les actions tierces ou les commandes construites dynamiquement.

Les ingestions référentiel de l'organisation administrative de l'État, Annuaire local et COG fonctionnent actuellement avec dépendances et déclenchements successifs. **Protéger `main` en interdisant les poussées directes avant d'avoir migré ces procédures entraînerait un risque d'interruption des actualisations.**

## Politique cible

- Toute modification de code et de référentiel doit passer par une proposition de fusion avec contrôles obligatoires des environnements Python 3.11 et 3.12 ainsi que du conteneur.
- Interdire les poussées forcées et la suppression de `main`, limiter les contournements et maintenir un registre des identités habilitées.
- Les procédures automatiques ne doivent disposer que des autorisations indispensables. Les essais déclenchés par une proposition externe restent séparés des opérations dotées de droits d'écriture.
- Conserver une preuve vérifiable du contenu exact des sources et de l'état du référentiel utilisé pour chaque génération.
- Ne pas présumer qu'une vérification portant sur les données brutes valide à elle seule la pertinence scientifique de leur interprétation.

## Transition proposée

1. Enregistrer les vérifications obligatoires **réellement présentes** dans les résultats d'intégration continue avant d'éditer une règle de protection.
2. Réunir la chaîne référentiel de l'organisation administrative de l'État → Annuaire local → COG dans une orchestration privilégiée distincte des essais externes. Pour chaque nouveau lot, créer une branche technique et une proposition de fusion portant sur les données normalisées et leurs manifestes, sans pousser directement sur `main`.
3. Réexaminer les déclenchements `déclenchement à la fin d'une autre procédure` : aujourd'hui la fin de l'import référentiel de l'organisation administrative de l'État signifie aussi la fin de son écriture. Avec une proposition de fusion en attente, cette hypothèse devient fausse. Déclencher les étapes dépendantes après la fusion appropriée ou exécuter leur chaîne dans une même orchestration.
4. Appliquer la même politique au RNSR et à la surveillance, en préservant la sérialisation des écritures qui partagent des fichiers ou des empreintes.
5. Vérifier sur une branche expérimentale les autorisations des jetons, les contrôles de fusion et les réactions aux changements du référentiel. Une fusion automatique exige une identité et des permissions correctement configurées : ne jamais lui accorder un contournement général pour simplifier l'intégration.
6. Activer ensuite la règle administrative `main` et vérifier par lecture des réglages et par essais non destructifs qu'elle est effectivement appliquée. Le ticket n° 54 reste ouvert jusqu'à cette preuve.

## Limites du contrôle livré

L'inventaire des cinq écrivains actuels n'est **pas** une approbation de leurs écritures directes. Il identifie la dette préalable et empêche de l'étendre silencieusement. Une recherche textuelle ne remplace ni un analyseur sémantique de procédures YAML, ni une inspection des actions tierces ou des réglages GitHub.

Le connecteur GitHub actuel n'expose pas une action d'administration permettant de modifier directement les règles de protection. Leur activation n'est donc pas revendiquée.

## Blocage de publication constaté le 9 octobre 2026

Une exécution ponctuelle, réalisée sur une branche temporaire ne contenant qu'un document explicitement fictif, a démontré que le jeton des procédures GitHub n'est actuellement pas autorisé à ouvrir des propositions de fusion. GitHub a répondu : « GitHub Actions is not permitted to create or approve pull requests ». [Consulter l'exécution](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/37890689595).

Les deux procédures indépendantes qui avaient été migrées vers cette publication ont donc été remises dans leur fonctionnement antérieur pour préserver les actualisations courantes. **Aucune protection stricte de `main` n'est déclarée active.** La procédure contrôlée des trois référentiels administratifs a toutefois réussi un essai complet sans publication sur les sources réelles : [exécution](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/37890327489).

Pour reprendre la migration, activer la faculté de créer des propositions dans les paramètres d'autorisation des procédures GitHub ou fournir une identité technique spécifique, limiter ses droits et répéter l'essai de création sur une branche artificielle. Les procédures historiques doivent rester opérationnelles jusqu'à cette validation.
