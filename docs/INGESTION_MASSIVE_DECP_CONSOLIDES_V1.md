# FRONTIÈRE — Importation massive des données DECP consolidées

**État : logiciel intégré au dépôt ; aucune collecte nationale hébergée n'est encore constatée.**

## Changement d'échelle

FRONTIÈRE sait déjà suivre les petits fichiers AIFE et les lots XML DGFiP.
Cette extension ajoute l'importation progressive des fichiers mensuels JSON
consolidés publiés par les ministères économiques et financiers sur data.gouv.fr.

Le référentiel de sources du dépôt, consulté le 14 octobre 2026, décrivait
42 ressources dont 34 fichiers de type « decp-AAAA-MM.json ». Certains
fichiers dépassent 100 ou 200 Mo. Il s'agit de ressources disponibles dans
le catalogue à cette date, pas de ressources déjà téléchargées ou indexées
par le nouveau service.

## Architecture

1. Interrogation du catalogue officiel des fichiers consolidés.
2. Découverte automatique de tous les fichiers mensuels de nom reconnu.
3. Tri par mois décroissant ; deux ressources non traitées par cycle par défaut.
4. Téléchargement progressif vers le stockage local persistant, avec
   comparaison à la taille officielle et calcul SHA-256.
5. Conservation immuable du JSON brut sous un nom contenant l'empreinte.
6. Lecture des notices en flux, normalisation du profil réduit existant.
7. Ajout dans l'index SQL DECP existant, en transaction indivisible par fichier :
   identités acheteur SIRET + marché, variantes, provenance, recherche FTS5.
8. Conservation du curseur de chaque ressource dans la base et reprise sans
   téléchargement répété tant que les métadonnées ne changent pas.

Le stockage est partagé avec le service AIFE/DGFiP, dans le volume nommé
stockage-frontiere-decp. Il est ainsi possible de chercher les données de
ces trois producteurs à partir d'un seul fichier SQLite.

Le programme traite les notices successivement, sans construire de liste
nationale d'enregistrements en mémoire. L'analyseur existant borne à
2 millions de caractères la taille d'un objet JSON isolé. Les fichiers
sont plafonnés à 2 milliards d'octets et le nombre de notices par fichier
à 2 millions dans cette première version. Tout dépassement interrompt le
fichier sans publier une importation partielle.

Les concessions sont comptées séparément sans être assimilées à des marchés.
Les notices de marché qui ne satisfont pas au profil normalisé existant
sont dénombrées comme rejets. Le compteur ne vaut pas conformité complète
au schéma réglementaire.

## Lancement sur une machine disposant de Docker

    docker compose -f compose.collecte.yml up -d --build collecte-decp-consolides

Le service démarre sans exposer de port public. Par défaut, il reprend
jusqu'à deux fichiers mensuels nouveaux par cycle, toutes les six heures.
L'importation historique des mois plus anciens continue aux cycles suivants.

Journal des collectes :

    docker compose -f compose.collecte.yml logs -f collecte-decp-consolides

La quantité de stockage disque nécessaire doit être prévue pour les fichiers
originaux bruts et leur index SQLite. Plusieurs gigaoctets peuvent être
nécessaires. Le stockage durable des fichiers est voulu ; aucune archive
n'est ajoutée à GitHub.

## Exécution ponctuelle et recherche

    python -m app.collecteur_decp_consolides \
      --base /tmp/frontiere-decp/marches.sqlite3 \
      --repertoire /tmp/frontiere-decp/originaux \
      collecter --maximum 2

    python -m app.collecteur_decp_consolides \
      --base /tmp/frontiere-decp/marches.sqlite3 \
      --repertoire /tmp/frontiere-decp/originaux \
      etat

    python -m app.collecteur_decp_consolides \
      --base /tmp/frontiere-decp/marches.sqlite3 \
      --repertoire /tmp/frontiere-decp/originaux \
      rechercher "informatique" --limite 25

Pour exécuter tous les services prévus sur une machine :

    docker compose -f compose.collecte.yml up -d --build

## Interprétation et limites réelles

Le nombre d'annonces DECP importées est distinct du nombre de marchés
uniques. Des descriptions provenant de sources différentes et des versions
d'un même marché sont conservées comme observations séparées.

Un marché attribué ne démontre pas l'existence d'un besoin encore ouvert.
Une ressemblance de référence BOAMP et DECP constitue une hypothèse de lien
à examiner, pas une identité juridique déjà établie.

Les changements de fichiers publiés avec des métadonnées entièrement
inchangées ne sont pas encore recherchés de manière systématique. Les
ressources non mensuelles, les concessions et les fichiers XML consolidés
hors des analyseurs existants sont également hors de cette première phase.

Un cycle qui a téléchargé un fichier valide mais rencontré un échec de
transformation conserve son fichier brut ; il n'inscrit pas d'importation
incomplète dans la base. Le prochain cycle pourra retraiter la ressource.

La concurrence entre les deux services DECP dans le même SQLite est
sérialisée par le moteur. Pour augmenter considérablement le débit et le
nombre d'ouvriers, le développement suivant portera sur PostgreSQL,
l'ordonnancement réparti et une recherche nationale centralisée.

**À développer ensuite :** extension des formes de ressources prises en
charge, campagnes de relecture des ressources anciennes, intégration TED
et rapprochements inter-sources en suivant les identifiants institutionnels.
