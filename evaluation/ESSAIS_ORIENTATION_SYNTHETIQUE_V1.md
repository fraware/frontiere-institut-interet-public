# Essais adversariaux de l'orientation documentaire — jeu artificiel

## Objet

Ce jeu vérifie la chaîne technique `besoin verrouillé → requête de capacité → index local → pistes documentaires → journal d'audit` avec des données entièrement inventées.

Il contient dix demandes et douze structures fictives. Chaque demande s'accompagne de repères documentaires fixés dans le fichier de données et d'une justification. Le programme compare les pistes effectivement restituées aux repères. Il signale les **repères non retrouvés** et les **pistes restituées en dehors des repères**.

Les repères sont élaborés par les auteurs du jeu fictif. Ils ne proviennent ni d'une enquête institutionnelle, ni de relecteurs indépendants. Les ratios produits sont des indicateurs **de fonctionnement de ce jeu artificiel**, sans valeur comme précision, rappel ou efficacité réelle de FRONTIÈRE.

## Contenu et mécanismes examinés

Le fichier `evaluation/jeu_orientation_synthetique_v1.json` regroupe des notices inventées avec une identité, un état déclaré, une mission publiée fictive ou un domaine scientifique fictif. Une notice non active permet de contrôler les exclusions.

Les cas couvrent notamment la séparation entre missions, domaines et noms ; un besoin numérique et sa classification scientifique ; une correspondance qui ne comporte qu'un nom de laboratoire ; une abréviation scientifique absente du libellé complet ; une expression trop générale qui introduit une piste supplémentaire ; et un besoin sans concordance lexicale dans le corpus de démonstration.

Le scénario relatif à l'abréviation « IRM » cherche ainsi une discipline exprimée sous sa forme développée. Il permet de relever le risque de perte d'une ressource pertinente à cause d'une divergence de formulation. Les faux rapprochements sont formulés comme **pistes hors des repères artificiels**, puisque leur pertinence scientifique réelle n'a pas été examinée.

## Exécution

Depuis la racine du dépôt :

```bash
python scripts/evaluer_orientation_synthetique.py
```

Le programme construit un nouveau répertoire et un nouvel index locaux dans un emplacement temporaire. Il crée ensuite une base d'essai en mémoire, insère les dix besoins et requêtes artificiels verrouillés, exécute l'orientation véritable de FRONTIÈRE, puis examine le journal et les résultats. Aucune source extérieure n'est interrogée et aucune base opérationnelle n'est ouverte.

Il restitue notamment :

- l'empreinte SHA-256 du jeu artificiel et l'effectif des cas ;
- pour chaque classe de preuve et pour chaque cas, les repères attendus, retrouvés et omis ;
- les pistes supplémentaires par rapport aux repères déclarés ;
- les effectifs agrégés et un rapport de repérage limité à cet univers fictif ;
- les contrôles des écritures : un événement de journal par orientation, aucune recherche publique ni découverte ni ressource créée.

Un cas dont les résultats seraient tronqués par les limites du moteur est refusé pour le calcul de ces effectifs : comparer des listes incomplètes comme si elles étaient exhaustives introduirait une distorsion supplémentaire.

Les essais sous `tests/test_orientation_synthetique.py` vérifient la reproduction à données égales, le refus des repères invalides, la séparation des types de preuve, l'absence de conclusion de mobilisation et le lancement de la commande.

## Portée et suite

Le jeu artificiel sert d'outil de diagnostic et de protection contre les régressions. Son intérêt principal est de **documenter explicitement les échecs de rapprochement** au lieu de les dissimuler dans une moyenne favorable. Une modification du moteur doit être accompagnée d'une révision raisonnée des repères et des résultats connus, sans modifier silencieusement le jeu historique.

Les étapes suivantes concernent une meilleure couverture des synonymes sans déduction excessive, la traçabilité des liens entre sources et identifiants institutionnels, et, ultérieurement, une évaluation indépendante avec des références non révélées. Les résultats de ce jeu artificiel restent entièrement séparés de ceux de l'évaluation réservée.
