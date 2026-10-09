# Protection effective de la branche principale — procédure de réception

## État observé avant activation

Le 9 octobre 2026, l'API publique de GitHub a renvoyé, pour `main`, `protected: false`. La collection des règles générales du dépôt était vide. Les trois contrôles ayant réussi sur le commit `4643407028d212651004c433da987a3283e2addc` étaient `Python 3.11`, `Python 3.12` et `Conteneur`. Leur source était l'application officielle GitHub Actions, identifiant `15368`.

La connexion GitHub utilisée pour les travaux techniques possède des droits d'écriture sur les fichiers et propositions, **sans permission administrative de modification des règles**. Une tentative de lecture détaillée des anciennes règles de protection a renvoyé une interdiction d'accès à l'API (`403 Resource not accessible by integration`). Ces constats concernent les droits du connecteur, pas ceux du propriétaire du dépôt.

## Règle recommandée, immédiatement importable

Le fichier `gouvernance/regle_protection_main_v1.json` contient une politique GitHub pour la seule branche `main` :

- Toute modification doit passer par une proposition de fusion ; méthode autorisée, fusion condensée uniquement.
- Les contrôles `Python 3.11`, `Python 3.12` et `Conteneur` sont obligatoires et doivent provenir de GitHub Actions, application `15368`.
- Les suppressions de `main`, les réécritures forcées et les historiques non linéaires sont interdits.
- Aucune identité ni application ne dispose d'une exception permanente.
- Les conversations de revue doivent être résolues avant fusion.
- Le nombre de validations humaines obligatoires est initialement **zéro**. Cela permet au responsable unique de fusionner les propositions vérifiées sans revendiquer une revue indépendante. Passer à une approbation externe obligatoire dès qu'un relecteur habilité et disponible a été nommé.

Pour la première mise en service, les vérifications obligatoires sont configurées en mode **non strict sur la mise à jour de la branche source** (`strict_required_status_checks_policy: false`). Cette mesure protège déjà les fusions contre des contrôles absents ou défaillants, tout en préservant le fonctionnement des branches produites par GitHub Actions, sur lesquelles les contrôles sont déclenchés explicitement. Une règle stricte imposant d'actualiser la branche avant fusion sera évaluée après un premier lot technique complet : elle demande une reprise du calcul et de ses validations dès que `main` avance.

## Activation par le propriétaire du dépôt

1. Ouvrir [Settings → Rules → Rulesets](https://github.com/fraware/frontiere-institut-interet-public/settings/rules).
2. Sélectionner **New ruleset → Import a ruleset** et fournir `gouvernance/regle_protection_main_v1.json`. Cette importation constitue une **préparation** : examiner le nom, la cible `main`, la liste de contournements vide, les cinq règles et les trois contrôles.
3. Vérifier que l'application choisie pour chaque contrôle est **GitHub Actions** et que la politique est en état **Active**. Confirmer l'enregistrement.
4. Vérifier les règles accessibles avec `python scripts/verifier_protection_main.py --exiger`. La commande interroge exclusivement les renseignements publics de GitHub. Elle ne possède aucune capacité de modification des paramètres.
5. En cas de conformité des protections publiquement accessibles mais d'accès insuffisant à la liste des dérogations, consulter la page des règles depuis le compte administrateur et consigner le résultat. `--exiger-integral` exige également la lecture de la liste complète des exceptions, susceptible d'être absente pour un jeton disposant uniquement des permissions de lecture. Ne pas déclarer un audit complet tant que les exceptions éventuelles n'ont pas été revues.
6. Exercer une proposition d'essai contenant uniquement un fichier fictif sur une branche indépendante : constater l'impossibilité de fusionner en présence d'un contrôle requis absent, puis lancer les trois contrôles sur la révision exacte et confirmer que la fusion est autorisée. **Ne pas exécuter de poussée forcée réelle ni de suppression de `main`** pour éprouver la protection.
7. Sur le premier lot institutionnel effectivement modifié, confronter le manifeste, la liste des fichiers et les résultats de contrôle à l'empreinte de la proposition. La branche technique ne doit jamais être fusionnée sans examen de son contenu.

La documentation GitHub pertinente est la procédure de [création des règles du dépôt](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository) et la [référence des vérifications obligatoires](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).

## Contrôles reproductibles

En amont de l'activation, vérifier uniquement la conformité du modèle fourni :

```bash
python scripts/verifier_protection_main.py --modele-seulement
```

Pour constater l'état GitHub **réel** :

```bash
python scripts/verifier_protection_main.py --exiger
```

Le contrôle est conservateur. L'option `--exiger` réussit seulement si GitHub montre une branche protégée et des règles actives lisibles pour les propositions obligatoires, l'historique linéaire, les interdictions de suppression et de poussée forcée et les trois vérifications issues de la bonne application. L'option `--exiger-integral` impose en outre la preuve de l'absence de dérogations. Les dérogations non exposées par l'API publique sont qualifiées **non vérifiables** ; elles interdisent une conclusion d'audit intégral, même si le contrôle des protections publiques réussit.

Une ancienne protection classique dont les paramètres détaillés sont réservés aux administrateurs pourra apparaître comme active sans être intégralement vérifiable par cet audit ; il conviendra alors de lire ses paramètres avec le compte propriétaire.

## Frontière scientifique et opérationnelle

Protéger `main` garantit des règles de modification du logiciel et des fichiers, sans certifier l'exactitude des observations publiques ni la disponibilité des compétences. Le premier lot réel ayant changé après cette migration devra encore être examiné par rapport à sa provenance et aux critères de qualité ; les expériences prospectives institutionnelles restent des étapes distinctes.

Le ticket [n° 54](https://github.com/fraware/frontiere-institut-interet-public/issues/54) demeure ouvert tant que l'activation administrative n'est pas confirmée et que les contrôles n'ont pas été exercés sur une proposition d'essai.
