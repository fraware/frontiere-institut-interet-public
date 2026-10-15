# FRONTIÈRE — Premier déploiement sur Render sans serveur administré

Cette option transpose les six services actuels vers **une seule instance Web
Render** équipée d'un disque persistant. L'interface et les cinq collecteurs
fonctionnent dans une image Docker unique, avec un ordonnanceur qui exécute
les acquisitions l'une après l'autre pour limiter la mémoire simultanée.

## Avant de créer la ressource payante

La configuration déclarative est \`render.yaml\`, à la racine du dépôt.
Elle prévoit un service payant de 1 processeur / 2 Go de mémoire
(\`1c-2g\`) et un disque de 50 Go monté sur
\`/var/lib/frontiere\`. La région déclarée est **Francfort, en Allemagne**,
ce qui situe l'hébergement initial dans l'Union européenne sans
prétendre à une implantation sur le territoire français. Les tarifs de référence consultés en octobre
2026 donnent 25 USD/mois pour cette puissance et 0,25 USD par Go de
disque et par mois. Le coût de base illustratif est donc de **37,50 USD
par mois**, hors autres frais éventuels, transferts et taxes.

Le forfait gratuit Render ne permet pas d'attacher de disque persistant.
Un disque Render est attaché à **une seule instance**, ce qui explique
la consolidation des cinq collecteurs et de l'interface dans ce premier
service. Pour une architecture répartie sur plusieurs machines, une
base commune PostgreSQL et un stockage d'objets seront nécessaires.

Références techniques officielles :

- https://render.com/docs/disks
- https://render.com/docs/blueprint-spec
- https://render.com/docs/health-checks
- https://render.com/docs/compute-plans

## Mise en ligne par le compte Render

1. Raccorder le compte Render au dépôt GitHub
   \`fraware/frontiere-institut-interet-public\`.
2. Dans Render, choisir un nouveau déploiement à partir d'une
   configuration de services et sélectionner ce dépôt.
3. Vérifier le contenu de \`render.yaml\`, son forfait, le disque de
   50 Go et le montant estimé par Render avant d'autoriser la création.
4. Lancer le déploiement et lire les journaux du service
   \`frontiere-observatoire-public\`.

Aucune dépense ni aucune ressource Render n'est créée par une fusion Git.
La création effective nécessite une autorisation sur un compte Render.

## Comportement du premier démarrage

Le serveur HTTP Uvicorn écoute sur le port défini par Render. La sonde
\`/sante\` mesure uniquement la disponibilité du processus HTTP. Elle
est volontairement indépendante de l'importation initiale : un corpus
de centaines de milliers d'enregistrements peut prendre plusieurs
minutes à importer.

Parallèlement, l'ordonnanceur :

- vérifie et importe les archives BOAMP, les seize partitions d'offres
  publiques et les relevés AIFE/DGFiP copiés dans l'image ;
- conserve des marqueurs d'amorçage sur le disque Render et les réutilise
  lors des redémarrages ;
- exécute ensuite BOAMP, emplois publics, DECP AIFE/DGFiP, DECP
  consolidés et TED à leurs intervalles configurés ;
- ne lance qu'une acquisition coûteuse à la fois, en limitant à un fichier
  national DECP consolidé chaque fois.

La constitution de l'historique national complet continue sur plusieurs
cycles. La disponibilité de l'interface ne signifie pas que les archives
sont déjà intégralement importées.

L'endpoint \`/exploitation\` décrit les quatre bases. L'endpoint
\`/pret\` devient disponible seulement si les quatre corpus sont
alimentés. Il s'agit de la disponibilité documentaire, distincte de
la réussite récente de chaque téléchargement.

## Persistance et redémarrage

Toutes les données produites sont écrites sous
\`/var/lib/frontiere\`. Le disque Render conserve les bases et les
fichiers source même si le service redémarre ou est reconstruit.

Les ressources archivées dans le dépôt sont incluses dans l'image comme
source de premier amorçage, sans copie de leur contenu brut dans Git lors
des nouvelles collectes. L'image peut être volumineuse ; les temps de
construction seront mesurés en conditions réelles.

Le délai de terminaison est allongé à 300 secondes pour réduire les
interruptions brutales. Les fichiers incomplets ne sont pas validés.
Une nouvelle exécution peut reprendre les importations déjà attestées.

Un disque persistant ne peut pas être partagé entre plusieurs instances
Render, n'autorise pas la mise à l'échelle horizontale et entraîne une
interruption du service pendant la substitution d'image.

## Limites du premier hébergement

La première instance est prévue pour un usage initial et un faible
nombre de consultations simultanées. Les grands fichiers consolidés
peuvent dépasser la mémoire ou le temps autorisé par cette capacité.
Dans ce cas, ralentir l'acquisition, augmenter le forfait ou déplacer
les index dans PostgreSQL.

Render fournit des instantanés périodiques de disques mais ceux-ci ne
remplacent pas les sauvegardes SQLite vérifiées ni la conservation des
fichiers originaux sur un autre service de stockage.

## Accès à l'interface hébergée

Le service Render impose maintenant la variable
\`FRONTIERE_CONTROLE_ACCES_OBLIGATOIRE=1\` et un secret
\`FRONTIERE_JETON_ACCES\` qui est saisi dans le tableau de bord Render
au moment de la création de l'infrastructure. Sa valeur n'est jamais
enregistrée dans GitHub.

Produire un secret localement :

    python3 -c 'import secrets; print(secrets.token_urlsafe(32))'

La valeur doit comporter au moins 32 caractères ASCII. En l'absence
de cette valeur, les routes de consultation renvoient HTTP 503 et
aucune recherche n'est accessible. Un mauvais secret renvoie HTTP 401.

L'accès autorisé utilise l'en-tête HTTP Authorization :

    curl -H "Authorization: Bearer VOTRE_JETON" \
      "https://ADRESSE_RENDER/recherche?q=informatique"

La sonde /sante reste accessible sans secret ; elle ne donne alors
que l'état du processus HTTP, sans volumes documentaires. Les routes
/sources, /exploitation, /pret, /recherche, /docs et /openapi.json
restent privées.

La conservation du jeton dans un terminal ou dans un fichier externe
au dépôt appartient à l'administrateur du service. Le secret ne doit
pas apparaître dans les liens partagés ni les journaux applicatifs.

En configuration locale Docker Compose, le contrôle d'accès demeure
facultatif tant que ces variables ne sont pas définies. Cette
compatibilité préserve les usages existants sur 127.0.0.1.

Les consultations publiques et l'authentification d'utilisateurs
distincts relèvent d'une évolution suivante.

## Vérification avant branchement au compte

Les essais GitHub contrôlent la constitution de l'image, le démarrage du
service HTTP avec collecteurs désactivés, la configuration déclarative
Render et les modules de supervision. Les vérifications ne constituent
ni un test de facturation, ni un test de capacité, ni une preuve que les
sources officielles sont accessibles depuis l'environnement Render.
