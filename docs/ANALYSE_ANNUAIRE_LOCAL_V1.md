# Caractérisation de l’Annuaire local DILA — version 1

## Objet

Cette étape caractérise la Base de données locales de l’Annuaire de l’administration avant toute ingestion canonique.

Elle établit quatre points sur la publication réelle : le nombre de guichets et de relations territoriales, le recouvrement exact des identifiants DILA avec le ROAE déjà intégré, la résolution éventuelle des références hiérarchiques ROAE actuellement orphelines, et la structure à retenir pour représenter séparément les guichets et la compétence géographique des services.

Cette étape ne crée aucune entité canonique et ne modifie aucune anomalie ROAE existante.

## Source

La source est la ressource officielle « Base de données locales de Service-public.gouv.fr », publiée par la DILA sur data.gouv.fr.

Le programme découvre la ressource par son identifiant data.gouv.fr stable :

    73302880-e4df-4d4c-8676-1a61bb997f3d

Il conserve dans le rapport l’adresse longue effectivement publiée, les métadonnées disponibles, l’empreinte SHA-256 de l’archive et les informations HTTP observées lors du téléchargement.

## Doctrine de cette phase

La base locale contient deux objets différents : des guichets publics locaux et des fichiers communaux exprimant la compétence géographique des organismes selon le type de service.

La caractérisation les mesure séparément. Un fichier communal n’est jamais interprété comme une institution.

Les rapprochements avec le ROAE utilisent uniquement l’identifiant DILA exact. Aucune fusion ne repose sur une similarité de nom.

Les 158 références hiérarchiques actuellement conservées dans institutionnel/anomalies_roae.json restent inchangées. Le rapport indique séparément lesquelles trouvent une cible exacte dans le flux local.

## Exécution

Depuis la racine du dépôt :

    python scripts/analyser_annuaire_local.py

Le programme interroge les métadonnées officielles data.gouv.fr, sélectionne la ressource attendue par son identifiant stable, télécharge l’archive dans un fichier temporaire en calculant son empreinte, inspecte le TAR sans extraction libre, parcourt progressivement le grand fichier JSON des guichets, analyse le ZIP communal dans un espace temporaire borné, croise les identifiants avec les partitions ROAE existantes, produit un rapport JSON puis supprime l’archive temporaire.

Une archive déjà téléchargée peut être analysée hors ligne :

    python scripts/analyser_annuaire_local.py --archive /chemin/vers/all_latest.tar.bz2 --sortie institutionnel/analyses/annuaire_local_test.json

## Contrôles de sécurité et de robustesse

Le programme impose des limites explicites sur la taille du téléchargement, du ZIP communal, du tampon JSON et de chaque fichier communal.

Les chemins absolus, traversées de répertoire, liens symboliques et liens internes dans le TAR sont refusés. Les chemins dangereux dans le ZIP sont également refusés. Les membres de l’archive sont lus directement ou dans un espace temporaire ; aucune extraction libre de l’archive n’est effectuée.

La structure du fichier principal doit être un tableau JSON de premier niveau. Une modification de format déclenche une erreur explicite afin d’éviter une interprétation silencieuse d’une nouvelle structure source.

## Mesures produites

Le rapport contient le nombre de guichets source et d’identifiants uniques, les doublons éventuels, les distributions de catégories et types, la couverture SIREN, SIRET, mission, textes de référence, responsables, adresses et géolocalisation, les liens hiérarchiques résolus localement, vers le ROAE et non résolus, les recouvrements exacts entre identifiants locaux et identifiants ROAE, la résolution exacte éventuelle des anomalies ROAE, le nombre de fichiers communaux, codes Insee distincts et associations de compétence, la taille décompressée du JSON principal, ainsi que la durée de traitement et la mémoire maximale observée.

## Temporalité et empreintes

Chaque guichet reçoit pendant l’analyse une empreinte brute de son enregistrement source.

Une seconde empreinte, qualifiée explicitement de semantique_candidate, exclut uniquement date_diffusion, version_type, version_etat_modification et version_source. Cette empreinte constitue un instrument de comparaison entre observations. Elle ne constitue pas une règle de validité et une seule exécution ne permet pas d’affirmer qu’un champ évolue quotidiennement.

Une décision sur l’empreinte canonique n’interviendra qu’après comparaison de plusieurs publications.

## Condition de passage à l’ingestion

La phase d’ingestion commence seulement après examen du rapport réel et décision explicite sur l’espace d’identité entre ROAE et Annuaire local, la représentation des guichets recouvrant éventuellement une entité déjà connue, la représentation séparée de la compétence géographique, le traitement des relations traversant les deux sous-référentiels, la politique d’empreinte et de temporalité, et les références encore non résolues.

Le résultat attendu de cette étape est une décision de modèle, pas une augmentation immédiate du nombre d’entités du graphe.
