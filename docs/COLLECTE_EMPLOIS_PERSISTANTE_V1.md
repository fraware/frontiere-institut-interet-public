# FRONTIÈRE — Collecte persistante des offres d'emploi public

**Livraison logicielle expérimentale, sans serveur hébergé activé.**

## Objectif et source

Ce circuit ajoute à la veille BOAMP les offres de postes publiées dans le
jeu officiel « Les offres diffusées sur Choisir le service public », diffusé
par la DGAFP sur data.gouv.fr.

Le corpus déjà versionné dans le dépôt comprend un manifeste établi le
12 octobre 2026 : 268 787 lignes lues, 268 102 variantes d'offres et
266 139 références distinctes. Il s'agit de chiffres documentaires datés,
pas du nombre de postes ouverts en temps réel.

Le dispositif réutilise directement :

- scripts.collecter_besoins_publics.relever_emplois (catalogue officiel) ;
- scripts.sonder_structure_offres_publiques (colonnes du CSV) ;
- scripts.extraire_offres_publiques (extraction et partitions) ;
- app.plateforme_emplois (index SQL persistant et versions historiques).

Une nouvelle version déclarée du CSV entraîne le contrôle de l'en-tête,
le téléchargement borné et la génération des partitions, puis leur ingestion
transactionnelle dans SQLite ou PostgreSQL. Un fichier inchangé ne provoque
pas de nouveau téléchargement si les partitions sont toujours conformes.

## Lancer les deux collecteurs

Exiger un hôte Docker avec un disque persistant et un accès réseau aux sources
officielles. Depuis la racine du dépôt :

    docker compose -f compose.collecte.yml up --detach --build

Le service collecte-boamp conserve ses propres fichiers BOAMP.
Le service collecte-emplois consulte toutes les six heures le catalogue
des offres publiques et met à jour sa base lorsque le producteur a publié
un fichier différent. Ce délai est un intervalle de contrôle, pas une
fréquence de publication promise par la DGAFP.

Les deux services disposent de volumes de données persistants séparés en
configuration SQLite, afin d'éviter des transactions concurrentes longues
sur un même fichier. L'architecture relationnelle de ces deux modules prend
aussi en charge PostgreSQL, sans que leur déploiement sur PostgreSQL ait été
testé de bout en bout.

Les données archivées localement peuvent être intégrées directement avant
la première connexion réseau :

    docker compose -f compose.collecte.yml run --rm collecte-emplois \
      python -m app.plateforme_emplois \
      --base sqlite:////var/lib/frontiere/offres_emplois.sqlite3 \
      importer --repertoire /opt/frontiere/archives

Interroger les dernières offres :

    docker compose -f compose.collecte.yml run --rm collecte-emplois \
      python -m app.plateforme_emplois \
      --base sqlite:////var/lib/frontiere/offres_emplois.sqlite3 \
      rechercher "cybersécurité" --limite 30

Consulter les comptes de captures :

    docker compose -f compose.collecte.yml run --rm collecte-emplois \
      python -m app.plateforme_emplois \
      --base sqlite:////var/lib/frontiere/offres_emplois.sqlite3 etat

## Identité des données

Une même référence d'offre peut apparaître avec plusieurs contenus dans
un même fichier. Le stockage n'en retient pas un arbitrairement : chaque
variante possède son empreinte, et sa présence dans chaque cliché est
enregistrée séparément. La recherche du cliché le plus récent présente
toutes les variantes encore présentes dans ce cliché.

Chaque partition est analysée de manière progressive : les octets sont
hachés et chaque enregistrement est contrôlé avec son empreinte.
L'importation des seize partitions et des identifiants distincts constitue
une transaction indivisible : une partition tronquée ou altérée provoque
le retour à l'état précédent.

Les fichiers originaux téléchargés ne sont pas recopiés dans GitHub.
Les anciens clichés déjà importés demeurent en base même si les partitions
locales ont été remplacées par le dernier fichier diffusé.

## Contraintes actuelles

Le collecteur DGAFP déjà existant est limité à 190 Mo de téléchargement
et à 300 000 lignes CSV. Ces limites peuvent demander une nouvelle méthode
d'extraction lorsque le producteur dépasse ces plafonds.

L'extraction actuelle matérialise en mémoire les offres d'un CSV avant de
publier ses partitions ; cette consommation mémoire doit être observée en
conditions réelles. La nouvelle ingestion SQL, elle, lit les partitions
progressivement.

La recherche du premier service utilise des filtres SQL textuels. La
pertinence sémantique, les rapprochements inter-sources, l'accès Web, la
détection automatique des besoins latents, l'ingestion DECP et TED et
l'hébergement permanent correspondent à des travaux ultérieurs.

Le succès de la construction d'une image ne prouve pas qu'un collecteur
hébergé dispose déjà d'une couverture et d'une fraîcheur mesurées.
