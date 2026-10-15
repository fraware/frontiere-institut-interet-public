# FRONTIÈRE — Recherche statique étendue

La recherche initiale limitée à 1 900 résultats reste disponible sur la page d'accueil. La page `recherche-etendue.html` consulte une nouvelle collection **bornée à 5 000 documents par source**, segmentée par **source et année de publication**. Les trois familles sont BOAMP, offres d'emploi public et marchés attribués DECP. Les sources sans territoire explicite ne reçoivent aucune localisation inférée.

## Index et provenance

La commande `node scripts/construire_partitions_statiques.mjs` parcourt les archives versionnées et écrit `site_frontiere/partitions/manifeste.json` ainsi que les lots `part-<source>-<année>-<numéro>.json`. Chaque lot contient au plus 700 documents et un mégaoctet. Le manifeste déclare ses tailles, son nombre de documents, son empreinte SHA-256 et la révision Git de la source lorsqu'elle est disponible.

Chaque publication construit les données depuis le dépôt sans appel réseau vers les producteurs. Les archives ne sont pas exhaustives. Le chiffre maximal de 15 000 résultats ne représente donc ni le nombre national réel de marchés ni celui des offres disponibles.

L'interface charge uniquement les lots de la source et de la période demandées. L'utilisateur peut choisir une année, toutes les années disponibles, ou préciser des dates de publication de début et de fin. Les lots couvrant une année entièrement extérieure à l'intervalle ne sont pas téléchargés ; les documents sont ensuite filtrés à la date exacte. Un intervalle inversé est refusé avant tout téléchargement. Elle affiche au plus 100 correspondances par recherche, tout en comptant l'ensemble des résultats identifiés dans les lots sélectionnés. Le traitement s'exécute dans le navigateur ; aucun serveur ou stockage persistant payant n'est ajouté.

La consultation vérifie la taille des lots, leur empreinte cryptographique SHA-256 avec l'interface native du navigateur et la cohérence du contenu avec le manifeste. Cette vérification est également répétée sur les archives réelles par les contrôles GitHub. Si le navigateur ne permet pas le contrôle d'empreinte, ou si un seul lot échoue, aucun résultat de la recherche demandée n'est affiché. Toute erreur de lecture interrompt la restitution pour éviter de présenter des résultats partiels comme complets.

## Contrôles

```sh
node --test tests/test_partitions_statiques.mjs
node scripts/construire_partitions_statiques.mjs
```

Le contrôle CI vérifie, sur les véritables archives, l'empreinte, le nombre de documents et la taille de chaque lot, ainsi que la présence de plus de 1 900 documents au total.

La segmentation territoriale exige des champs géographiques fiables des producteurs et reste à préparer séparément. Le filtre de période accepte les années et les intervalles de dates présents dans les archives ; aucune date absente n'est inventée. La sélection par territoire reste exclue en l'absence d'identifiants géographiques comparables entre sources.

## Bilan de sélection publié

Le manifeste `site_frontiere/partitions/manifeste.json` comprend désormais
`selection`, calculé pendant la construction à partir des documents effectivement
retenus et des lots produits. La page `recherche-etendue.html` permet de
consulter, pour BOAMP, emplois publics et DECP :

- le nombre de documents indexés et le plafond de 5 000 par source ;
- les années documentaires représentées et leur nombre de documents ;
- le nombre d'enregistrements parcourus dans les fichiers locaux ainsi que
  l'unité utilisée par chaque collecteur.

Les enregistrements d'origine ne sont pas directement comparables : annonces
BOAMP, variantes d'offres et notices contractuelles DECP. Le plafonnement
à 5 000 documents sélectionne un sous-ensemble récent et ne permet pas de
calculer les omissions uniques exactes ou un taux de couverture nationale.
La présence d'une année indique uniquement qu'au moins un document de cette
année figure dans l'extrait retenu.

Le bilan est déterministe à archives données. Ses totaux sont vérifiés contre
les lots du manifeste et les contrôles fonctionnels du site. Une version du
manifeste antérieure à ce changement reste consultable, avec la mention
explicite « bilan de sélection indisponible ».

Pour reproduire les vérifications :

```sh
node --test tests/test_partitions_statiques.mjs
node scripts/construire_partitions_statiques.mjs
```

La prochaine amélioration scientifique doit mesurer les documents admissibles
écartés par les plafonds, source par source, sur les archives complètes et les
identifiants distincts. Ce travail nécessitera des décomptes adaptés à chaque
producteur ; aucune inférence de couverture nationale n'en découlera à lui seul.

## Regroupements documentaires par SIRET d'acheteur DECP

La recherche étendue comporte désormais un filtre sur l'identifiant **SIRET
déclaré de l'acheteur d'un marché attribué**. Lors de la construction de l'index
DECP, `scripts/construire_index_statique.mjs` crée la référence documentaire
`acheteur_siret/id_marche` à partir des données DECP AIFE et DGFiP. Le
filtre utilise les **14 chiffres exacts** présents dans cette référence,
indépendamment des noms, adresses et ressemblances de textes.

Une notice affichée dans l'extrait DECP contient un lien « Consulter les
marchés indexés du même SIRET déclaré ». Ce lien ouvre une adresse partageable
de la forme `recherche-etendue.html?acheteur=12345678901234`, sélectionne
automatiquement DECP et toutes les années présentes, puis restitue les notices
datées par ordre documentaire décroissant. Les autres filtres de dates et de
termes restent utilisables. Aucune collecte réseau supplémentaire n'est
déclenchée vers les producteurs : le navigateur charge les partitions
statiques sélectionnées avec leurs contrôles d'intégrité existants.

Les données sont limitées aux documents **retenus dans l'index DECP** (au
plus 5 000) ; l'interface affiche au plus 100 résultats et compte les
correspondances du périmètre exploré. En l'absence de correspondance, elle
présente zéro résultat. La date utilisée est la date de notification du
marché, ou à défaut une date de publication déclarée dans le relevé.

### Portée et exclusions

Ce regroupement atteste uniquement que plusieurs notices portent le **même
SIRET d'acheteur déclaré par le producteur**. L'identité administrative et
juridique de ce SIRET n'est pas revérifiée à travers le répertoire Sirene ;
un site, un service et une personne morale ne sont pas automatiquement
assimilés. Le regroupement ne démontre ni projet commun, ni besoin encore
ouvert, ni chronologie de mobilisation des compétences.

Les avis BOAMP et les offres d'emploi public ne sont **pas** reliés par
ressemblance de nom. Ils ne rejoindront ces ensembles que si une correspondance
d'identifiant officiel est vérifiée et sourcée séparément.

### Tests

```sh
node --test tests/test_acheteurs_decp.mjs
node scripts/construire_partitions_statiques.mjs
node --test tests/test_recherche_chromium.mjs
```

Les essais vérifient les égalités exactes, les faux rapprochements par nom,
les identifiants malformés, les dates, le partage d'une adresse de dossier
et la restitution sur le corpus réel dans Chromium. La consultation continue
de refuser les lots altérés. Aucun service persistant ni abonnement payant
n'est ajouté.


## Rattachement aux entités DILA par identifiant exact

L'indexation statique produit désormais `partitions/rattachements-acheteurs.json`,
à partir des SIRET **déclarés dans les seuls documents DECP indexés** et des
partitions vérifiées du Référentiel de l'organisation administrative de l'État
et de l'Annuaire local DILA. La construction n'interroge aucun serveur
extérieur. Les manifestes déjà archivés dans le dépôt délimitent les partitions
lues ; leurs tailles, décomptes et empreintes SHA-256 sont contrôlés à nouveau
avant publication.

Les rapprochements par nom, sigle, commune, SIREN seul, hiérarchie supposée ou
similarité de projet sont interdits. Seule l'égalité de 14 chiffres d'un SIRET
déclaré produit un **rapprochement documentaire**.

Trois situations sont distinguées : un seul enregistrement administratif
actif avec le même SIRET ; plusieurs entités portant le même SIRET (ambiguïté
explicite) ; une entité de statut inactif ou inconnu. Les autres SIRET ne
reçoivent aucun rattachement : leur absence des deux instantanés DILA ne
démontre pas leur inexistence juridique ni leur absence d'autres catalogues.

La page de recherche étendue charge le fichier de rattachement seulement pour
une consultation filtrée par SIRET et vérifie sa taille et son empreinte
cryptographique avant de présenter le résultat. En cas d'altération, aucun
résultat n'est affiché. Les noms et identifiants institutionnels sont
conservés sans contacts nominatifs, responsables ou coordonnées.

**Frontière de preuve :** une concordance de SIRET dans deux publications
ne démontre ni la personnalité morale de l'acheteur, ni son rôle réel dans
l'acte contractuel, ni une continuité de projet, ni un besoin non satisfait.
Pour établir de telles relations, il faudra recouper les pièces primaires,
la chronologie et les répertoires administratifs appropriés.

Le fichier est limité au même extrait DECP plafonné à 5 000 notices que la
recherche étendue ; aucune exhaustivité nationale n'est revendiquée.
L'intégration n'ajoute ni serveur, ni base permanente, ni prestation payante.

Vérifications :

```sh
node --test tests/test_rattachements_institutionnels.mjs
node scripts/construire_partitions_statiques.mjs
node --test tests/test_recherche_chromium.mjs
```

## Avis BOAMP corroborés dans les dossiers DECP

Les recherches par SIRET d'acheteur affichent désormais séparément les
observations de l'enquête indépendante menée sur **17 avis BOAMP**.
Dans cette population restreinte, 16 établissements distincts ont été
retrouvés par recherche administrative exacte. Deux avis possèdent une
concordance documentaire avec des identités de marchés DECP archivées :

- Avis `25-94670` (26 août 2025), SIRET `21060027600013`,
  cinq identités documentaires de marchés portant le même SIRET ;
- avis `26-62030` (25 juin 2026), SIRET `18002002600019`,
  une identité documentaire de marché portant le même SIRET.

Les six identités DECP correspondent aux **relevés historiques utilisés par
l'étude**, et non nécessairement aux 5 000 notices retenues dans la recherche
étendue. La section dédiée reste distincte du résultat de recherche :
ses observations ne sont pas affectées par les filtres d'année, de dates ou
de termes appliqués à l'extrait DECP.

Pour éviter toute attribution contractuelle infondée, la section expose
exclusivement l'avis, la date, le SIRET, le nombre d'identités de marchés
et le registre des preuves. Un SIRET BOAMP était un identifiant à quatorze
chiffres sans schéma déclaré ; sa reconnaissance comme SIRET exact dépend
de la vérification administrative indépendante figurant dans les archives
de l'étude. Aucune liaison d'avis à un marché particulier n'est démontrée.

Le générateur `scripts/construire_avis_boamp_corrobores.mjs` contrôle
l'empreinte SHA-256 figée du registre de 17 avis et son fichier témoin,
valide les 17 observations et publie seulement les deux concordances.
Le résultat `site_frontiere/partitions/avis-boamp-corrobores.json` est
annoncé dans le manifeste avec sa taille et son empreinte. Le navigateur
les vérifie avant affichage. En cas d'altération, les résultats du dossier
ne sont pas publiés.

L'étude est non représentative de la France. L'absence de concordance
sur un SIRET donné parmi 17 avis ne prouve pas l'absence d'autres avis.
Aucun besoin ouvert, contrat commun ou taux de couverture nationale
n'est déduit. L'ensemble fonctionne sans service nouveau ni collecte réseau
au moment de la consultation.

Essais de contrôle :

```sh
node --test tests/test_avis_boamp_corrobores.mjs
node scripts/construire_partitions_statiques.mjs
node --test tests/test_recherche_chromium.mjs
```
