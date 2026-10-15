# FRONTIÈRE — Acquisition des avis européens TED

Le collecteur repose sur l'interface publique officielle **TED Search API v3**
du Journal officiel de l'Union européenne :
https://docs.ted.europa.eu/ODS/latest/reuse/search-api.html

Aucun compte ni secret d'accès n'est nécessaire pour les recherches publiques.
Le circuit est prévu pour l'interrogation des avis publiés concernant les
acheteurs français, puis pour l'extension à d'autres pays.

## Acquisition

- Interrogation de la recherche experte avec pays acheteur FRA et date de
  publication précise.
- Récupération de tous les résultats d'une journée par pagination de type
  ITERATION, sans appliquer le plafond de 15 000 résultats de l'autre mode.
- Contrôle du nombre de publications annoncé et de la pagination avant
  toute modification de la base pour cette journée.
- Conservation du contenu JSON fourni par TED, de son empreinte SHA-256
  et de versions successives.
- Recherche des avis par titre ou acheteur, avec numéro TED et lien officiel.
- Réinterrogation des quatre derniers jours toutes les deux heures par défaut.
  Les journées antérieures restent consultables dans la base persistante.

Il s'agit de **dates de publication**, pas nécessairement de périodes de
validité des appels d'offres ni de besoins encore ouverts. Les avis TED
peuvent inclure des annonces de résultats ou d'autres actes.

## Exécution et stockage

Lancer uniquement ce nouveau collecteur :

    docker compose -f compose.collecte.yml up -d --build collecte-ted

Lancer tous les collecteurs FRONTIÈRE configurés :

    docker compose -f compose.collecte.yml up -d --build

Le volume indépendant stockage-frontiere-ted conserve le fichier SQLite
entre les redémarrages. Aucun port public n'est exposé par le collecteur.

Pour une exécution ponctuelle depuis la racine du dépôt :

    python -m app.collecteur_ted_continu \
      --base /tmp/frontiere-ted/avis.sqlite3 collecter --jours 4

Pour reprendre une période historique bornée :

    python -m app.collecteur_ted_continu \
      --base /tmp/frontiere-ted/avis.sqlite3 collecter \
      --depuis 2026-09-01 --jours 31

Pour rechercher un organisme :

    python -m app.collecteur_ted_continu \
      --base /tmp/frontiere-ted/avis.sqlite3 rechercher "Université"

Un traitement historique plus long se déroule par tranches successives
de 31 jours. Les recherches de journées antérieures n'effacent pas les
variantes historiques enregistrées.

## Contrats de fonctionnement

Une date n'est déclarée couverte que si tous les résultats annoncés ont
été récupérés et si les numéros de publication sont cohérents. Un délai
d'attente, une réponse invalide, un décompte fluctuant ou un jeton répété
interrompent la journée, sans l'enregistrer comme complète.

Les libellés multilingues sont projetés en français s'il est disponible,
sinon en anglais ou dans une autre langue fournie. La représentation
originale du document de recherche est conservée.

Cette première tranche ne télécharge pas les dossiers de consultation,
ne normalise pas encore toutes les informations eForms et ne rapproche
pas les avis européens des contrats français. Le moteur de recherche reste
local au volume TED : la consultation fédérée est une contribution suivante.

## État de vérification

Les essais du dépôt couvrent la pagination, les versions, les reprises,
les dates incohérentes, les réponses incomplètes et la recherche. La
connexion à l'interface réelle doit être éprouvée depuis le serveur
permanent avant d'affirmer une couverture nationale ou une fraîcheur
mesurée. Le collecteur n'est pas déployé par la fusion du code.
