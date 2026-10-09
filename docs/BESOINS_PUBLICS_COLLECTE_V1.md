# Collecte régulière des besoins publics publiés

## Objet et première réalisation

Les besoins scientifiques et techniques de l'État sont en partie exprimés dans des annonces de marchés publics et des offres d'emploi. Ces documents fournissent des **indices publiés par les acheteurs et employeurs**, sans établir automatiquement une pénurie de spécialistes, une demande adressée à FRONTIÈRE ou la faisabilité d'une intervention.

Une première collecte spécialisée réunit deux sources officielles.

### Annonces de marchés

Le [Bulletin officiel des annonces des marchés publics](https://www.data.gouv.fr/dataservices/api-bulletin-officiel-des-annonces-des-marches-publics-boamp) expose une interface publique gratuite, soumise à la Licence Ouverte 2.0 et aux conditions d'accès du producteur. Le programme `scripts/collecter_besoins_publics.py` interroge les annonces publiées depuis sept jours, jusqu'à douze pages de cent annonces par exécution.

Chaque notice conservée comporte un identifiant, l'objet de l'achat, l'acheteur public, les dates de publication et de réponse, la catégorie, le statut et une référence officielle lorsqu'elle est fournie. Les contacts nominatifs et les textes complets des annonces ne sont pas recopiés. L'index cumule les identifiants rencontrés dans `institutionnel/besoins_publics/annonces_boamp.json` ; son état est enregistré dans `institutionnel/besoins_publics/etat_boamp.json`.

Les documents rectificatifs sont conservés sous leur identifiant propre. La collecte n'assimile pas chaque avis à un nouveau besoin unique : un même marché peut donner lieu à plusieurs annonces. Elle ne déduit aucune compétence disponible à partir d'une annonce.

Le nombre total d'annonces indiqué par la source est enregistré lorsqu'il est fourni. Si la période contient davantage de résultats que le plafond consulté, la collecte signale explicitement `recherche_partielle=true`. La collection cumulative a un plafond initial de 30 000 notices ; la méthode de partition sera adaptée avant d'atteindre ce plafond pour éviter toute perte silencieuse.

### Offres d'emploi public

Le jeu [Les offres diffusées sur Choisir le Service Public](https://www.data.gouv.fr/datasets/les-offres-diffusees-sur-choisir-le-service-public), produit par la Direction générale de l'administration et de la fonction publique, publie des fichiers CSV bruts à fréquence déclarée hebdomadaire et sous Licence Ouverte 2.0. Les fichiers recensent les annonces déposées directement et celles diffusées depuis des sites partenaires.

La première étape spécialisée conserve la **liste vérifiée des ressources du jeu**, leurs identifiants, dates, formats, tailles et adresses officielles. Les fichiers originaux sont actuellement volumineux et ne sont pas encore copiés. L'index n'identifie donc encore aucun poste individuel : les deux fichiers `ressources_emplois_publics.json` et `etat_emplois_publics.json` signalent explicitement cette limite.

Un programme expérimental de lecture partielle inspecte désormais l'en-tête du CSV le plus récent et conserve uniquement les noms de colonnes, le séparateur et l'identifiant du fichier, sous réserve que la source accepte le téléchargement borné. Il ne conserve aucune ligne d'offre d'emploi. Cette observation de schéma devra réussir sur le fichier officiel avant toute extraction de lignes.

L'étape suivante consistera à extraire les annonces pertinentes avec identifiants stables, intitulés, employeurs publics, domaines, dates et géographie, en excluant les contacts individuels et en enregistrant les règles de réutilisation. L'étendue du fichier téléchargé et la couverture obtenue devront être mesurées.

## Actualisation automatique

Le programme `.github/workflows/collecte-besoins-publics.yml` est programmé quatre fois par jour (3 h 23, 9 h 23, 15 h 23 et 21 h 23 UTC). Une exécution manuelle est également prévue.

Chaque exécution :
1. vérifie les transformations avec des données d'essai ;
2. interroge les deux sources indépendamment et conserve les anciens fichiers si l'une est inaccessible ;
3. ouvre une proposition de mise à jour limitée aux quatre fichiers de résultats ;
4. vérifie la réussite des trois essais automatisés sur l'empreinte exacte de la proposition ;
5. fusionne les seules notices admissibles, sans exécuter d'action auprès d'une institution.

Les résultats sont consultables dans l'application sur `/besoins-publics` et par `/api/v1/besoins-publics?source=marches` ou `source=emplois`. La disponibilité sur un site externe dépend d'un déploiement actualisé depuis GitHub ; une nouvelle version du dépôt ne modifie pas à elle seule un serveur déjà installé.

## Conditions de lecture et limites

La première version privilégie la disponibilité des données et l'identification de leurs producteurs. Les annonces BOAMP consultées forment une fenêtre glissante de sept jours, limitée en volume, et **ne représentent pas tous les avis historiques**. Les ressources d'emploi sont référencées mais leurs lignes ne sont pas encore importées. Une couverture totale exige des partitions historiques, le traitement des modifications et suppressions à la source, le suivi des licences et une stratégie adaptée aux fichiers importants.

Les échecs de réseau ne sont jamais traduits en absence de besoins. Chaque source conserve son propre suivi, avec les dates de consultation et limites de collecte. Aucune validation institutionnelle humaine n'est revendiquée.

## Contrôle local

```bash
python -m pytest -q tests/test_collecte_besoins_publics.py tests/test_publication_besoins_publics.py
python scripts/collecter_besoins_publics.py
```

La seconde commande interroge les interfaces officielles et conserve les résultats dans le répertoire local. Les propositions de fusion distantes relèvent exclusivement de la procédure GitHub autorisée.
