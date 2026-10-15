# FRONTIÈRE — Procédure de premier déploiement permanent

Ce document décrit l'installation des cinq services existants sur un hôte
Linux disposant de Docker Compose, avec persistance des données.

**La fusion du dépôt ne crée pas de serveur et n'engage aucun fournisseur
d'hébergement.** Cette procédure devra être exécutée sur la machine
réellement destinée à héberger FRONTIÈRE. Aucune exécution de cette
procédure n'est présumée accomplie.

## Prérequis techniques

Une machine Linux durable avec Docker Engine et Docker Compose,
l'accès réseau sortant aux sources publiques et un disque persistant.
Prévoir une réserve de plusieurs dizaines de gigaoctets pour les archives
DECP consolidées, les historiques BOAMP, les offres d'emploi et les bases
SQLite. Mesurer les besoins exacts en mémoire, débit et stockage sur les
premiers fichiers avant de dimensionner définitivement.

La configuration courante emploie trois volumes persistants. Les
collecteurs AIFE/DGFiP et consolidés DECP partagent leur volume et leur
base SQLite sur le même hôte. Une infrastructure hébergeant chaque
conteneur sur un hôte isolé sans volume partagé ne correspond pas à cette
topologie ; un basculement vers PostgreSQL serait alors nécessaire.

La consultation HTTP écoute uniquement sur 127.0.0.1:8765 sur la
machine. Pour accéder à distance, utiliser une connexion SSH :

    ssh -L 8765:127.0.0.1:8765 utilisateur@serveur

Depuis le poste local, la consultation répond alors sur
http://127.0.0.1:8765/recherche, sans publication générale du port.

## Préparation du dépôt

Sur le serveur :

    git clone https://github.com/fraware/frontiere-institut-interet-public.git
    cd frontiere-institut-interet-public
    git checkout main

Inspecter les étapes prévues, **sans exécuter Docker** :

    python3 scripts/amorcer_deploiement.py

La sortie JSON précise la présence des archives attendues, le nombre
de partitions d'emploi et de manifestes BOAMP ainsi que les sept étapes
d'exécution.

Le fichier manifeste CSP et ses 16 partitions, les archives historiques
BOAMP, le relevé AIFE et les relevés DGFiP doivent être présents.
Une erreur d'amorçage arrête la procédure avant le démarrage des services.

## Amorçage et démarrage

Exécuter le plan sur l'hôte équipé de Docker Compose :

    python3 scripts/amorcer_deploiement.py --executer

Les opérations sont réalisées dans cet ordre :

1. Contrôler la configuration Docker Compose.
2. Construire les images des cinq services.
3. Importer les archives BOAMP dans leur volume persistant.
4. Importer les variantes d'emploi public dans leur volume persistant.
5. Importer le corpus documentaire DECP AIFE/DGFiP existant dans la
   base partagée avec les fichiers consolidés.
6. Démarrer les quatre collecteurs et la consultation locale.
7. Afficher l'état des conteneurs.

L'extraction nationale DECP consolidée se poursuit ensuite
selon les horaires paramétrés dans compose.collecte.yml. La première
constitution de ces deux historiques nécessite un délai mesuré après le
démarrage. Une exécution du script ne démontre pas leur couverture
effective.

Une option permet de construire et de préparer les bases, tout en
différant le lancement des collecteurs :

    python3 scripts/amorcer_deploiement.py --executer --sans-demarrage

Sur un serveur dont les données ont déjà été importées, pour reconstruire
les images et redémarrer les services sans réimporter l'historique :

    git pull --ff-only
    python3 scripts/amorcer_deploiement.py --executer --sans-amorcage

Les opérations d'amorçage sont conçues pour être rejouables : les
importateurs existants reconnaissent les fichiers déjà intégrés, tandis
que les volumes sont conservés lors des renouvellements de conteneurs.

## Première vérification

Sur le serveur :

    docker compose -f compose.collecte.yml ps
    docker compose -f compose.collecte.yml logs --tail=80 collecte-boamp
    docker compose -f compose.collecte.yml logs --tail=80 collecte-emplois
    docker compose -f compose.collecte.yml logs --tail=80 collecte-decp
    docker compose -f compose.collecte.yml logs --tail=80 collecte-decp-consolides

    curl http://127.0.0.1:8765/exploitation
    curl --fail http://127.0.0.1:8765/pret

Le second appel est indisponible tant que les trois bases ne sont pas
effectivement alimentées. L'état de santé d'un conteneur n'établit pas
à lui seul la réussite d'un passage récent sur toutes les sources.

## Données, sauvegarde et exploitation

Aucune suppression de volume ne doit faire partie d'une mise à jour
ordinaire. La commande « docker compose down --volumes » effacerait
les trois volumes locaux : elle est exclue de cette procédure.

Les fichiers et bases présents dans les volumes ont une valeur
documentaire propre. Il faut définir une sauvegarde cohérente des
bases SQLite et des fichiers sources volumineux vers un stockage
extérieur à la machine. Cette sauvegarde, avec essai de restauration,
fait l'objet d'une contribution distincte.

Pour l'analyse de la fraîcheur, distinguer la date d'une nouvelle
publication officielle, le passage du collecteur et la date
d'importation du fichier. Le diagnostic disponible dans
docs/SUIVI_EXPLOITATION_SOURCES_V1.md mesure à ce stade l'état des
bases et la dernière observation documentaire importée.

## Prochaines décisions

La suite dépend de l'accès à l'hôte réel ou à un service de déploiement
pouvant lancer les conteneurs et conserver les trois volumes. Les mesures
de couverture, de débit et d'actualisation seront établies uniquement
après exécution et observation de cette infrastructure.
