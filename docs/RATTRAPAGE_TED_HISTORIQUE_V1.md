# FRONTIÈRE — Rattrapage de l'historique TED français

Le collecteur TED courant interroge régulièrement les quatre derniers
jours. Ce mécanisme ne découvre pas les publications antérieures à son
démarrage. La présente extension ajoute un **rattrapage documentaire
progressif**, couvrant à partir du **1er janvier 2024** les journées
qui ne figurent pas encore dans le calendrier des captures TED.

## Contrat de reprise

La table \`captures_ted\` dans la base commune conserve uniquement les
journées récupérées complètement. L'outil parcourt ce calendrier par
ordre chronologique, recherche les dates absentes et soumet chacune à
\`collecter_jour\`, qui avait été confronté à l'interface réelle TED sur
une journée de 404 avis en octobre 2026.

Une journée dépourvue d'annonces est également mémorisée comme couverte
si le serveur renvoie un décompte officiel nul et des pages cohérentes.
Une journée ayant échoué à la récupération intégrale reste absente du
calendrier : son acquisition est réessayée au passage suivant.

Le rattrapage va seulement jusqu'à **quatre jours avant la date courante**,
pour laisser les dernières publications au collecteur périodique existant.
Ce choix conserve deux parcours indépendants, sur la même base SQLite.

## Exécution ponctuelle

Depuis la racine du dépôt et avec les dépendances Python installées :

    python -m app.rattrapage_ted \
      --base /tmp/frontiere-ted/avis_ted.sqlite3 \
      --depuis 2024-01-01 --maximum 3 collecter

Pour suivre les journées restantes :

    python -m app.rattrapage_ted \
      --base /tmp/frontiere-ted/avis_ted.sqlite3 \
      --depuis 2024-01-01 --maximum 3 suivre --intervalle 21600

Le nombre maximal de journées par passage est de douze. Par défaut,
l'instance Render ajoute une sixième tâche à l'ordonnanceur : trois
journées historiques par passage, toutes les six heures, avec une seule
acquisition exécutée à la fois. La tranche historique est conservée
au fil des redémarrages.

Le bilan décrit les journées déjà couvertes, les jours encore absents,
les nouvelles journées récupérées et la prochaine date à traiter. Une
source indisponible est identifiée par son type d'erreur et son jour ;
elle ne conduit pas à inscrire une capture incomplète.

## Limites et interprétation

**Ce mécanisme n'atteste pas une couverture européenne exhaustive ni
une importation déjà exécutée sur Render.** Le périmètre initial porte
sur les publications TED attribuées par la recherche aux acheteurs
français, pour les journées à partir du 1er janvier 2024. Les archives
plus anciennes pourront être ajoutées en étendant la date de départ.

La précision de la recherche et la limite officielle de 15 000 avis
par requête TED sont celles du collecteur existant. Les jours
supérieurs à ce plafond restent en échec jusqu'à leur subdivision.

La couverture chronologique mesure des jours documentaires entièrement
interrogés ; elle ne prouve pas que chaque avis est un marché encore
ouvert, ni une correspondance avec un avis BOAMP ou une attribution DECP.

La tranche suivante portera sur l'identification explicite des
institutions et les hypothèses de rapprochement inter-sources, avec
conservation des provenances.
