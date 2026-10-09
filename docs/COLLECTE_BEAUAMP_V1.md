# Marchés attribués enrichis : archivage quotidien BeauAMP

## Origine et portée

Le jeu [Base Étendue, Améliorée et Unifiée des Annonces des Marchés Publics (BeauAMP)](https://www.data.gouv.fr/datasets/base-etendue-amelioree-et-unifiee-des-annonces-des-marches-publics) est publié par Adrien Deschamps, chercheur à Avignon Université, sous licence Creative Commons Attribution – Partage dans les Mêmes Conditions.

Ses données croisent les avis BOAMP avec des informations SIRENE et comprennent des rapprochements et estimations, notamment pour les identifiants des acheteurs et titulaires. **La source avertit que ses résultats ont une valeur indicative**. Les annonces officielles initiales constituent la référence pour vérifier une attribution.

Citation de référence : Adrien Deschamps, « Updating “processing and consolidation of open data on public procurement in France (2015–2023)” with daily refresh », *Data in Brief*, vol. 64, 2026, article 112362, DOI [10.1016/j.dib.2025.112362](https://doi.org/10.1016/j.dib.2025.112362).

## Première réalisation

Le programme `scripts/collecter_beauamp.py` consulte l'interface publique du jeu de données sur data.gouv.fr, vérifie la licence déclarée et sélectionne les fichiers quotidiens CSV au format `beauamp-JJ-MM-AAAA.csv`, de taille inférieure ou égale à 1,5 Mo chacun. Il privilégie les fichiers des 31 derniers jours, puis utilise les places restantes dans un lot de 60 fichiers au maximum pour remonter progressivement vers des journées antérieures qui ne figurent pas dans les archives déjà vérifiées. Le catalogue officiel du producteur détermine les dates effectivement disponibles.

Il conserve **les octets exacts** des fichiers sélectionnés dans `institutionnel/marches_attribues/quotidiens/AAAA-MM-JJ.csv`. Chaque fichier est contrôlé par sa taille attendue, une empreinte SHA-256 et son adresse officielle d'origine.

Le manifeste `institutionnel/marches_attribues/manifest.json` consigne pour chaque fichier sa date, son identifiant public, sa taille, son empreinte, son adresse et la mention de l'auteur et de la licence. Chaque nouvelle collecte vérifie **les octets des archives déclarées dans le manifeste précédent** avant de poursuivre. Une archive manquante, modifiée ou une date répétée interrompt la publication, afin de préserver une chaîne de provenance explicite. Les journées déjà archivées restent inscrites au manifeste lorsque leur date sort de la fenêtre récente. Les échecs de téléchargement par fichier sont signalés sans supprimer les archives antérieures. Les données archivées conservent leur licence d'origine et doivent être réutilisées avec attribution et respect du partage dans les mêmes conditions.

Le programme récupère progressivement les petits fichiers quotidiens historiques accessibles dans le catalogue, tout en refusant les fichiers de plus de 1,5 Mo. Il **n'aspire pas** les fichiers historiques de centaines de mégaoctets ou de plusieurs gigaoctets, ni les mois entiers ; leur archivage devra être conçu par lots adaptés. Il n'établit aucune preuve de capacité scientifique mobilisable.

## Fréquence et publication

La procédure `.github/workflows/collecte-beauamp.yml` exécute la collecte à 4 h 47 et 16 h 47 UTC et lors de l'intégration de modifications du collecteur. Les nouveaux fichiers passent par une proposition de fusion limitée au répertoire BeauAMP. Leur publication automatique est conditionnée à trois vérifications GitHub Actions réussies sur le commit exact.

La première collecte réelle et sa publication ont déjà été constatées en octobre 2026. L'extension historique doit, à son tour, être vérifiée lors d'une exécution effective : les contrôles hors connexion ne démontrent pas que les fichiers anciens du catalogue ont été récupérés. Une licence différente de celle attendue, un format inconnu ou un fichier dont la taille diffère de la déclaration source interrompt la publication de ce fichier.

## Conditions de réutilisation

Les fichiers copiés restent des documents produits par BeauAMP sous Creative Commons Attribution – Partage dans les Mêmes Conditions. Les citations et la source doivent accompagner leur diffusion. Les approximations signalées par le producteur empêchent de les substituer aux avis BOAMP officiels.

Il convient de distinguer trois univers :
- les annonces publiées au BOAMP, qui recensent les procédures et leurs avis ;
- les marchés attribués et enrichis par BeauAMP, avec une couverture et des transformations spécifiques ;
- les besoins d'expertise scientifique, qui nécessitent une interprétation supplémentaire des deux précédents.

Aucune exhaustivité des marchés ni aucun rapprochement parfait entre ces univers n'est revendiqué.
