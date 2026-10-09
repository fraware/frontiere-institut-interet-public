# Essai contrôlé de la chaîne administrative et territoriale

**Statut : procédure d'essai sans lancement confirmé.** Cette procédure prépare la migration des trois collectes interdépendantes. Elle n'a aucun déclenchement périodique et n'écrit rien dans `main`.

## Enchaînement

La procédure `.github/workflows/preparer-proposition-referentiel.yml` exécute, dans une même copie de travail :

1. les tests, la collecte et le contrôle de variation du référentiel de l'organisation administrative de l'État ;
2. les tests, la collecte et le contrôle de variation de l'Annuaire local, à partir de l'organisation administrative actualisée ;
3. les tests, la collecte et le contrôle de variation des territoires de référence, à partir de l'Annuaire actualisé ;
4. la reconstruction et la vérification des synthèses publiques ;
5. le contrôle de cohérence entre les trois ensembles, puis la vérification des seuls fichiers autorisés.

Le contrôle `python scripts/verifier_chaine_referentiel.py` recoupe les décomptes administratifs, les services locaux, les références hiérarchiques et les territoires de l'Insee. Il refuse notamment un décalage entre catégories et totaux, des relations incompatibles, des références géographiques inexpliquées ou une empreinte déclarée mal formée. Le résultat est **structurel**. Il ne vérifie pas la signification scientifique des missions, la disponibilité opérationnelle des compétences ou l'identité des octets originaux des téléchargements.

## Préparer et exécuter un essai

La procédure apparaît dans les actions du dépôt sous le nom « Préparation contrôlée du référentiel institutionnel ». Elle est lancée à la demande sur `main`.

- Avec `publier = false`, réglage initial : collecter et valider sans publier de proposition.
- Avec `publier = true` : après toutes les vérifications, préparer une branche technique et ouvrir une proposition de fusion, puis demander l'exécution des contrôles automatisés sur la branche produite. La proposition n'est jamais fusionnée automatiquement.

Le jeton de publication n'est fourni qu'à la dernière étape, la récupération initiale ne conserve aucune information d'authentification et l'exécution partage le groupe de sérialisation des anciennes collectes. La proposition n'est ouverte que si le point de départ est encore le dernier état de `main`.

## Conditions avant remplacement des procédures historiques

Lancer un essai complet sans publication, observer les temps, les téléchargements, les décomptes, les contrôles de variation et le résultat des synthèses. Un succès de tests locaux ne prouve pas à lui seul que la chaîne de téléchargement complète a été exécutée.

Ensuite, exercer la publication d'un lot sur branche technique et constater effectivement la création de sa proposition et les trois résultats automatiques. Examiner une exécution sans changement et une tentative où `main` a avancé, afin de vérifier les blocages et les reprises.

Une fois ces observations acquises, déplacer la programmation périodique vers cette procédure, retirer les commandes d'écriture directe des trois collectes historiques et réexaminer leurs déclenchements en cascade. Ce changement doit être coordonné : la fin d'une collecte sans fusion ne signifie plus que ses résultats sont présents dans `main`.

La protection administrative de `main` est un chantier distinct. Elle n'est pas déclarée activée par l'existence de cet essai.
