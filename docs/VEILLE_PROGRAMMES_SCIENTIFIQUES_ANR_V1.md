# Surveillance documentaire des programmes scientifiques ANR — version 1

**Création : 14 octobre 2026.** **État : infrastructure proposée, validation réseau et première proposition d'observations encore à réaliser.**

## Finalité

Observer les publications officielles relatives à deux dispositifs ANR importants pour l'étude FRONTIÈRE :

- **SAPS–CPPE 2026** : programme de recherche en coopération avec les administrations, dont l'ANR a annoncé 22 projets retenus le 29 juin 2026. Source primaire : [communiqué ANR](https://anr.fr/actus/details/news/science-avec-et-pour-la-societe-22-laureats-pour-co-construire-les-politiques-publiques-par-lexpe/).
- **ANR–NRF 2026 (IA et biotechnologies)** : appel ouvert le 2 avril et clos le 4 juin 2026 ; [page de l'appel](https://anr.fr/fr/detail/call/appel-a-projets-anr-nrf-2026-intelligence-artificielle-pour-les-biotechnologies/). Une liste de cinq projets sélectionnés a été publiée le 13 octobre 2026, avec financement conditionné par les étapes administratives prévues.

Le [répertoire officiel des dernières listes de projets sélectionnés](https://anr.fr/fr/projets-finances-et-impact/projets-finances/dernieres-listes-de-projets-selectionnes/) est le cinquième point de surveillance. Il sert à détecter des changements de publications et non à attribuer automatiquement un nouveau statut à un projet.

## Périmètre et garanties

Le registre `institutionnel/programmes_scientifiques/sources_v1.json` définit exactement cinq URL officielles, leurs programmes, leurs natures documentaires et les formats attendus. La liste est fermée ; seuls `anr.fr` et `www.anr.fr` sont admis. Les accès imposent HTTPS, contrôlent les redirections et limitent chaque réponse à trois millions d'octets. Les contenus acceptés sont des pages HTML et un PDF dont la signature est vérifiée.

Le programme `scripts/surveiller_programmes_scientifiques.py` normalise les textes HTML pour calculer une empreinte, ou calcule l'empreinte des octets du PDF. Il conserve uniquement les métadonnées techniques et les signatures SHA-256, sans republier les documents scientifiques.

Le registre `institutionnel/programmes_scientifiques/etat_observations.json` démarre **vide**. Aucune capture HTTP réelle, date de consultation ou empreinte du producteur n'a été inventée pour l'initialiser. La première exécution réussie enregistrera les signatures et leur provenance.

Les états observables sont `premiere_observation`, `identique`, `modification_a_requalifier` et `echec_observation`. Une modification du code HTML peut correspondre à une variation éditoriale sans conséquence scientifique ; l'examen humain de l'acte ou de la liste nouvelle reste obligatoire.

**Aucune transition institutionnelle n'est déduite automatiquement.** La chaîne scientifique distingue les étapes suivantes : appel annoncé, appel clos, projets sélectionnés, aide attribuée, convention ou notification, travaux réalisés, résultat publié, premier usage documenté. L'absence de pièce relative à une étape ne prouve pas qu'elle n'a pas eu lieu.

## Procédure programmée

La procédure `.github/workflows/veille-programmes-scientifiques.yml` est prévue une fois par jour, avec lancement manuel possible. Elle vérifie d'abord les contrats par des tests hors connexion, puis effectue le relevé des cinq points d'entrée.

Les changements d'empreinte sont conservés dans un historique borné à 25 modifications par publication. Le rapport complet d'exécution est déposé comme pièce JSON/Markdown durant 30 jours. Les échecs d'accès sont signalés et n'effacent jamais les observations antérieures.

Lors d'une exécution programmée, les fichiers modifiés sont soumis, **exclusivement** s'il existe des changements, à `scripts/publier_mise_a_jour_institutionnelle.py --source programmes --publier`. Le périmètre autorisé se limite à `institutionnel/programmes_scientifiques/etat_observations.json`. Le programme crée une proposition de fusion et déclenche les vérifications de dépôt. La publication automatique ne fusionne pas la proposition et la relève documentaire est à examiner avant toute adoption.

Les contrôles ne garantissent pas que l'ANR ait publié toutes les décisions, ni que la période sans changement d'empreinte corresponde à l'absence de progression d'un projet. Le déclenchement quotidien de GitHub Actions est indicatif. Le contrôle transversal suit désormais cette procédure avec une fenêtre de 72 heures.

## Reproduction

Les tests hors réseau s'exécutent avec :

`python -m pytest -q tests/test_surveiller_programmes_scientifiques.py tests/test_publication_institutionnelle.py`

Pour effectuer un relevé sans publication de proposition :

`python -m scripts.surveiller_programmes_scientifiques --bilan-json /tmp/anr-bilan.json --bilan-markdown /tmp/anr-bilan.md`

Les réponses réseau peuvent être refusées par le producteur, les pages peuvent être redirigées et la taille ou le type d'un fichier peut changer. Dans ces cas, conserver le dernier état validé, signaler l'incident et rechercher un accès officiel autorisé, sans contourner les restrictions.

## Prochain seuil scientifique

Un rapprochement des cinq empreintes permet de décider **quelles pages relire**. La construction d'une véritable chronologie probatoire nécessite des identifiants de projet, des actes de sélection, des conventions, les résultats et leur utilisation effective. Ces relations seront proposées dans un registre scientifique distinct, revues contradictoirement et jamais déduites de la seule signature d'une page.

Suivi correspondant : [problème GitHub n° 415](https://github.com/fraware/frontiere-institut-interet-public/issues/415).