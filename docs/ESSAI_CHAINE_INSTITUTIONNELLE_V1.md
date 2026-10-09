# Essai contrôlé de la chaîne administrative et territoriale

**Statut : essai intégral réussi, publication distincte en cours de validation.** L'[exécution du 9 octobre 2026](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/37890327489) a confirmé les trois collectes sur les sources officielles, sans publication. La procédure commune est destinée à leur actualisation programmée ; elle n'écrit jamais directement dans `main`.

## Enchaînement

La procédure `.github/workflows/preparer-proposition-referentiel.yml` exécute, dans une même copie de travail :

1. les tests, la collecte et le contrôle de variation du référentiel de l'organisation administrative de l'État ;
2. les tests, la collecte et le contrôle de variation de l'Annuaire local, à partir de l'organisation administrative actualisée ;
3. les tests, la collecte et le contrôle de variation des territoires de référence, à partir de l'Annuaire actualisé ;
4. la reconstruction et la vérification des synthèses publiques ;
5. le contrôle de cohérence entre les trois ensembles, puis la vérification des seuls fichiers autorisés.

Le contrôle `python scripts/verifier_chaine_referentiel.py` recoupe les décomptes administratifs, les services locaux, les références hiérarchiques et les territoires de l'Insee. Il refuse notamment un décalage entre catégories et totaux, des relations incompatibles, des références géographiques inexpliquées ou une empreinte déclarée mal formée. Le résultat est **structurel**. Il ne vérifie pas la signification scientifique des missions, la disponibilité opérationnelle des compétences ou l'identité des octets originaux des téléchargements.

## Préparer et exécuter un essai

La procédure apparaît dans les actions du dépôt sous le nom « Préparation contrôlée du référentiel institutionnel ». Elle est programmée chaque jour à 5 h 47 UTC et accepte également un lancement manuel sur `main`.

- **Lancement manuel avec `publier = false`**, réglage initial : collecter et valider sans ouvrir de proposition.
- **Lancement manuel avec `publier = true`**, ou **déclenchement programmé** : après vérifications, ouvrir une proposition si un lot a changé, puis lancer les contrôles automatiques sur sa branche. Aucun lot n'est fusionné automatiquement.

Le jeton de publication n'est fourni qu'à la dernière étape, la récupération initiale ne conserve aucune information d'authentification et l'exécution partage le groupe de sérialisation des anciennes collectes. La proposition n'est ouverte que si le point de départ est encore le dernier état de `main`.

## Réception des lots et limites de l'essai

La [première exécution complète sans publication](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/37890327489) a réussi. La [vérification des droits GitHub sur données fictives](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/37950043096) a également réussi. Ces deux constats sont complémentaires, mais n'établissent pas à eux seuls la création réussie d'une proposition issue d'un lot **réellement modifié**.

À chaque actualisation programmée, consulter le journal de la procédure commune. La réussite des trois importations, des contrôles de variation et du contrôle final de portée constitue le premier critère. Si le lot est inchangé, aucune proposition n'est créée. Si un lot diffère du référentiel, la branche technique, la proposition et les résultats des vérifications sur l'empreinte exacte de la branche doivent être identifiés.

L'ancienne programmation des collectes individuelles est remplacée par cette chaîne commune. Leur code de transformation demeure disponible dans le dépôt et leurs procédures conservent les vérifications des propositions externes, en lecture seule.

Toute activation de la protection administrative de `main` reste conditionnée à la vérification du mode de publication sur un lot modifié et aux réglages de gouvernance du dépôt. Le changement de procédure ne vaut pas activation d'une règle de protection.
