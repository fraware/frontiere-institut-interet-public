# Gouvernance de main — transition avant protection

**État : audit et migration à préparer.** Ce document ne prétend pas qu'une règle de branche soit activée. Le contrôle exécuté localement n'accède pas aux réglages administratifs de GitHub.

## Constat vérifié dans les procédures

Trois procédures administratives et territoriales exécutent encore une commande de poussée Git vers `main` : organisation administrative de l'État, Annuaire local et territoires de l'Insee. Les structures de recherche et la surveillance publient désormais leurs modifications sous forme de propositions distinctes. Le contrôle `python scripts/auditer_ecritures_main.py` énumère ces écritures historiques et fait échouer l'intégration si une **nouvelle procédure** ajoute une écriture directe littérale. Il ne détecte pas les actions tierces ou les commandes construites dynamiquement.

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
4. Vérifier lors de chaque exécution des structures de recherche et de la surveillance que les propositions sont créées et que leurs contrôles sont effectivement déclenchés ; conserver la sérialisation des écritures communes.
5. Vérifier sur une branche expérimentale les autorisations des jetons, les contrôles de fusion et les réactions aux changements du référentiel. Une fusion automatique exige une identité et des permissions correctement configurées : ne jamais lui accorder un contournement général pour simplifier l'intégration.
6. Activer ensuite la règle administrative `main` et vérifier par lecture des réglages et par essais non destructifs qu'elle est effectivement appliquée. Le ticket n° 54 reste ouvert jusqu'à cette preuve.

## Limites du contrôle livré

L'inventaire des trois écrivains actuels n'est **pas** une approbation de leurs écritures directes. Il identifie la dette préalable et empêche de l'étendre silencieusement. Une recherche textuelle ne remplace ni un analyseur sémantique de procédures YAML, ni une inspection des actions tierces ou des réglages GitHub.

Le connecteur GitHub actuel n'expose pas une action d'administration permettant de modifier directement les règles de protection. Leur activation n'est donc pas revendiquée.

## Blocage de publication constaté le 9 octobre 2026

Le premier essai ponctuel du 9 octobre 2026, sur une branche contenant uniquement un document fictif, avait démontré que le jeton GitHub ne disposait pas encore de la permission de créer des propositions. GitHub a répondu : « GitHub Actions is not permitted to create or approve pull requests ». [Consulter l'exécution](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/37890689595).

Un repli temporaire des deux procédures indépendantes avait alors préservé les actualisations courantes. La permission a ensuite été modifiée et vérifiée, permettant de réactiver leur publication par propositions distinctes. **Aucune protection stricte de `main` n'est déclarée active.** La procédure contrôlée des trois référentiels administratifs a toutefois réussi un essai complet sans publication sur les sources réelles : [exécution](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/37890327489).

La permission de création des propositions a été confirmée par une seconde exécution réelle, après modification des paramètres. Les trois procédures administratives encore historiques seront migrées seulement après vérification d'un lot complet publié sur une branche technique.

## Limitation des droits des essais — 9 octobre 2026

Les deux procédures responsables des services locaux et des territoires sont désormais séparées en deux tâches. La première vérifie les propositions externes uniquement avec des autorisations de lecture. La seconde réalise les actualisations programmées ou déclenchées à la suite d'une collecte précédente, avec un droit d'écriture limité à son propre travail. Les identifiants nécessaires à l'écriture ne sont fournis que lors de l'enregistrement final.

Cette séparation des droits est conservée pendant la transition des trois écritures historiques restantes. Elle ne remplace ni une règle de protection de la branche principale, ni l'identité technique nécessaire pour ouvrir des propositions automatiquement. Le traitement expérimental unique des trois référentiels demeure disponible et a réussi son essai sans publication.


## Nouvelle vérification des droits et migration des deux sources indépendantes

Le [second essai de création de proposition](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/37950043096) a réussi avec le jeton propre à GitHub Actions. Une proposition entièrement fictive, n° 122, a été ouverte, puis fermée sans fusion et la branche a été supprimée. Cette preuve lève le blocage de création constaté plus tôt ; elle ne démontre pas encore la réussite du cycle complet de publication de données et d'exécution explicite des contrôles sur la nouvelle branche.

Les procédures de structures de recherche et de surveillance ont été migrées à nouveau vers des propositions distinctes, sans fusion automatique. Une seule proposition en attente par source est admise ; le mécanisme refuse tout état de départ dépassé. Les trois collectes dépendantes gardent temporairement leurs écritures directes afin de préserver leur continuité jusqu'à une validation distincte de publication. **La branche `main` n'est toujours pas déclarée administrativement protégée.**
