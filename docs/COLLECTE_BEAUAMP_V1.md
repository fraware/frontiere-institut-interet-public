# Marchés attribués enrichis : archivage quotidien BeauAMP

## Origine et portée

Le jeu [Base Étendue, Améliorée et Unifiée des Annonces des Marchés Publics (BeauAMP)](https://www.data.gouv.fr/datasets/base-etendue-amelioree-et-unifiee-des-annonces-des-marches-publics) est publié par Adrien Deschamps, chercheur à Avignon Université, sous licence Creative Commons Attribution – Partage dans les Mêmes Conditions.

Ses données croisent les avis BOAMP avec des informations SIRENE et comprennent des rapprochements et estimations, notamment pour les identifiants des acheteurs et titulaires. **La source avertit que ses résultats ont une valeur indicative**. Les annonces officielles initiales constituent la référence pour vérifier une attribution.

Citation de référence : Adrien Deschamps, « Updating “processing and consolidation of open data on public procurement in France (2015–2023)” with daily refresh », *Data in Brief*, vol. 64, 2026, article 112362, DOI [10.1016/j.dib.2025.112362](https://doi.org/10.1016/j.dib.2025.112362).

## Première réalisation

Le programme `scripts/collecter_beauamp.py` consulte l'interface publique du jeu de données sur data.gouv.fr, vérifie la licence déclarée et sélectionne uniquement les fichiers quotidiens CSV au format `beauamp-JJ-MM-AAAA.csv`, publiés durant les 31 derniers jours et pesant au maximum 1,5 Mo chacun.

Il conserve **les octets exacts** des fichiers sélectionnés dans `institutionnel/marches_attribues/quotidiens/AAAA-MM-JJ.csv`. Chaque fichier est contrôlé par sa taille attendue, une empreinte SHA-256 et son adresse officielle d'origine.

Le manifeste `institutionnel/marches_attribues/manifest.json` consigne pour chaque fichier sa date, son identifiant public, sa taille, son empreinte, son adresse et la mention de l'auteur et de la licence. Les échecs par fichier sont consignés sans effacer les archives déjà présentes. Les données archivées conservent leur licence d'origine et doivent être réutilisées avec attribution et respect du partage dans les mêmes conditions.

Le programme **n'aspire pas** les fichiers historiques de centaines de mégaoctets ou de plusieurs gigaoctets, ni les mois entiers ; leur archivage devra être conçu par lots adaptés. Il n'établit aucune preuve de capacité scientifique mobilisable.

## Fréquence et publication

La procédure `.github/workflows/collecte-beauamp.yml` exécute la collecte à 4 h 47 et 16 h 47 UTC et lors de l'intégration de modifications du collecteur. Les nouveaux fichiers passent par une proposition de fusion limitée au répertoire BeauAMP. Leur publication automatique est conditionnée à trois vérifications GitHub Actions réussies sur le commit exact.

Le programme doit produire une première collecte réelle réussie et une proposition effectivement fusionnée avant de présenter les fichiers comme archivés. Une licence différente de celle attendue, un format inconnu ou un fichier dont la taille diffère de la déclaration source interrompt la publication de ce fichier.

## Conditions de réutilisation

Les fichiers copiés restent des documents produits par BeauAMP sous Creative Commons Attribution – Partage dans les Mêmes Conditions. Les citations et la source doivent accompagner leur diffusion. Les approximations signalées par le producteur empêchent de les substituer aux avis BOAMP officiels.

Il convient de distinguer trois univers :
- les annonces publiées au BOAMP, qui recensent les procédures et leurs avis ;
- les marchés attribués et enrichis par BeauAMP, avec une couverture et des transformations spécifiques ;
- les besoins d'expertise scientifique, qui nécessitent une interprétation supplémentaire des deux précédents.

Aucune exhaustivité des marchés ni aucun rapprochement parfait entre ces univers n'est revendiqué.
