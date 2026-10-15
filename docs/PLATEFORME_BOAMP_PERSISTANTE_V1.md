# Première base persistante des avis BOAMP — FRONTIÈRE

**État : première tranche logicielle, sans service hébergé en fonctionnement.**

## Finalité

Le module app/plateforme_boamp.py importe les captures produites par les
collecteurs historiques existants vers une base opérationnelle durable.
L'architecture des collecteurs n'est pas remplacée. Les fichiers d'origine
demeurent la référence pour les archives déjà constituées.

La projection prend en charge les archives journalières JSONL comprimées et
leurs manifestes, ainsi que le relevé glissant annonces_boamp.json et son
état. Chaque capture est identifiée par son chemin et son empreinte SHA-256.
Les notices distinctes sont consultables, tandis que les différentes versions
normalisées d'un avis sont conservées séparément.

## Démarrer localement

Précondition : Python 3.11+, dépendances du projet installées.

    mkdir -p /tmp/frontiere-persistant
    python -m app.plateforme_boamp --base sqlite:////tmp/frontiere-persistant/boamp.sqlite3 importer --repertoire institutionnel/besoins_publics
    python -m app.plateforme_boamp --base sqlite:////tmp/frontiere-persistant/boamp.sqlite3 etat
    python -m app.plateforme_boamp --base sqlite:////tmp/frontiere-persistant/boamp.sqlite3 rechercher "calcul" --limite 20
    python -m pytest -q tests/test_plateforme_boamp.py

Pour relire périodiquement les fichiers locaux après leur mise à jour :

    python -m app.plateforme_boamp --base sqlite:////tmp/frontiere-persistant/boamp.sqlite3 importer --repertoire institutionnel/besoins_publics --suivre --intervalle 300

La commande de suivi se limite aux fichiers présents sur le disque. Elle ne
télécharge pas de nouveaux avis depuis le BOAMP et ne garantit pas la
publication de données nouvelles toutes les cinq minutes. Un hébergement
persistant et une exécution permanente des collecteurs sont nécessaires pour
assurer l'actualisation opérationnelle de la plateforme.

## PostgreSQL

Le même schéma et les insertions conditionnelles fonctionnent avec PostgreSQL.
Installer un pilote compatible SQLAlchemy, par exemple psycopg version 3, puis
transmettre une URL de type postgresql+psycopg://... via l'argument --base.
Ce chemin PostgreSQL n'est pas encore testé en intégration dans les procédures
automatiques du dépôt ; la première étape utilise SQLite.

La base est locale ou hébergée hors du dépôt Git. Ne pas publier ses fichiers
de données ni les informations de connexion.

## Propriétés de l'importation

- Vérification des empreintes des octets comprimés et décompressés de chaque
  archive journalière.
- Vérification de la date, du nombre et de l'unicité des avis de chaque journée.
- Transaction indivisible par capture, insertions par lots de 400 notices.
- Reprise sur capture déjà enregistrée, sans dupliquer les versions.
- Conservation des anciennes versions même si le relevé courant a changé.
- Un état courant associé à la capture la plus récente connue ; une égalité
  d'horodatage est départagée techniquement par l'empreinte, sans en déduire
  une chronologie de publication.
- Recherche textuelle littérale sur l'objet ou le nom de l'acheteur.

Un enregistrement correspond à une notice documentaire, pas à un besoin
scientifique démontré, un marché unique ou une ressource effectivement
mobilisée. L'absence d'un avis dans les fichiers observés ne prouve pas
l'absence de besoin public.

## Limites et suite

Cette première version n'implémente ni le téléchargement de documents complets,
ni une file de tâches distribuée, ni un ordonnanceur partagé, ni un moteur de
recherche plein texte à grande échelle, ni une interface publique hébergée.
La recherche utilise une condition SQL sur deux champs. Les archives sources
sont limitées par les plafonds des collecteurs existants.

Prochaines tranches : brancher le collecteur quotidien sur un service
persistant, indexer les offres d'emploi, les contrats DECP et les publications
TED dans un référentiel commun des entités et événements, puis publier une
interface de recherche multi-sources. Les volumes, délais et taux de couverture
doivent être mesurés sur des exécutions réelles, sans les présumer acquis.
