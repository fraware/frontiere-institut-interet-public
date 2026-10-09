# Collecte régulière des besoins publics publiés

## Objet et première réalisation

Les besoins scientifiques et techniques de l'État sont en partie exprimés dans des annonces de marchés publics et des offres d'emploi. Ces documents fournissent des **indices publiés par les acheteurs et employeurs**, sans établir automatiquement une pénurie de spécialistes, une demande adressée à FRONTIÈRE ou la faisabilité d'une intervention.

Une première collecte spécialisée réunit deux sources officielles.

### Annonces de marchés

Le [Bulletin officiel des annonces des marchés publics](https://www.data.gouv.fr/dataservices/api-bulletin-officiel-des-annonces-des-marches-publics-boamp) expose une interface publique gratuite, soumise à la Licence Ouverte 2.0 et aux conditions d'accès du producteur. Le programme `scripts/collecter_besoins_publics.py` interroge les annonces publiées depuis sept jours, jusqu'à quarante-cinq pages de cent annonces par exécution.

Chaque notice conservée comporte un identifiant, l'objet de l'achat, l'acheteur public, les dates de publication et de réponse, la catégorie, le statut et une référence officielle lorsqu'elle est fournie. Les contacts nominatifs et les textes complets des annonces ne sont pas recopiés. L'index cumule les identifiants rencontrés dans `institutionnel/besoins_publics/annonces_boamp.json` ; son état est enregistré dans `institutionnel/besoins_publics/etat_boamp.json`.

Les documents rectificatifs sont conservés sous leur identifiant propre. La collecte n'assimile pas chaque avis à un nouveau besoin unique : un même marché peut donner lieu à plusieurs annonces. Elle ne déduit aucune compétence disponible à partir d'une annonce.

Le nombre total d'annonces indiqué par la source est enregistré lorsqu'il est fourni. Si la période contient davantage de résultats que le plafond consulté, la collecte signale explicitement `recherche_partielle=true`. La collection cumulative a un plafond initial de 30 000 notices ; la méthode de partition sera adaptée avant d'atteindre ce plafond pour éviter toute perte silencieuse.

### Offres d'emploi public

Le jeu [Les offres diffusées sur Choisir le Service Public](https://www.data.gouv.fr/datasets/les-offres-diffusees-sur-choisir-le-service-public), produit par la Direction générale de l'administration et de la fonction publique, publie des fichiers CSV bruts à fréquence déclarée hebdomadaire et sous Licence Ouverte 2.0. Les fichiers recensent les annonces déposées directement et celles diffusées depuis des sites partenaires.

La collecte conserve d'abord les métadonnées des ressources officielles dans `ressources_emplois_publics.json`, ainsi que le schéma effectivement observé du CSV dans `schema_emplois_publics.json`. **Une seconde opération distincte importe désormais les lignes d'offres individuelles** dans seize partitions `offres_postes/lot_XX.jsonl`, sans conserver le fichier source brut dans Git et sans recopier les coordonnées de contact.

La première extraction réelle datée du 9 octobre 2026 est décrite par `manifest_offres_postes.json` : 120 111 905 octets téléchargés, 261 536 lignes lues, 260 880 enregistrements distincts et 258 947 références distinctes. Elle conserve 1 146 références ayant plusieurs variantes et signale 3 693 cellules tronquées suivant des plafonds de longueur déclarés. Le manifeste fournit l'empreinte SHA-256 du fichier source. Ces nombres correspondent au contenu du fichier consulté, pas à un dénombrement des postes vacants ou des besoins scientifiques démontrés.

Le fichier `etat_emplois_publics.json` décrit la collecte **du catalogue de ressources**, tandis que `manifest_offres_postes.json` décrit l'extraction **des lignes individuelles**. Le champ `actualisation_des_offres_individuelles_constatee` du premier n'atteste pas la seconde opération et ne doit pas être présenté comme le bilan de l'importation.

## Actualisation automatique

Le programme `.github/workflows/collecte-besoins-publics.yml` est programmé quatre fois par jour (3 h 23, 9 h 23, 15 h 23 et 21 h 23 UTC). Une exécution manuelle est également prévue.

Chaque exécution :
1. vérifie les transformations avec des données d'essai ;
2. interroge les deux sources indépendamment et conserve les anciens fichiers si l'une est inaccessible ;
3. ouvre une proposition de mise à jour limitée aux fichiers publics autorisés de cette source, y compris le manifeste et les seize partitions d'offres ;
4. vérifie la réussite des contrôles Python 3.11, Python 3.12 et conteneur sur l'empreinte exacte de la proposition ;
5. **fusionne automatiquement** la proposition uniquement si ces contrôles réussissent et si l'ensemble des fichiers modifiés appartient au périmètre prévu, sans exécuter d'action auprès d'une institution.

Les résultats sont consultables dans l'application sur `/besoins-publics` et par `/api/v1/besoins-publics?source=marches` ou `source=emplois`. La disponibilité sur un site externe dépend d'un déploiement actualisé depuis GitHub ; une nouvelle version du dépôt ne modifie pas à elle seule un serveur déjà installé.

## Conditions de lecture et limites

La première version privilégie la disponibilité des données et l'identification de leurs producteurs. Les annonces BOAMP consultées forment une fenêtre glissante de sept jours, limitée à 4 500 annonces interrogées par exécution, et **ne représentent pas tous les avis historiques**. Les lignes d'offres du fichier DGAFP courant ont été extraites et partitionnées. La donnée ne constitue pas un inventaire instantané de postes ouverts. Une couverture historique complète exige une collecte des fichiers antérieurs, le traitement des modifications et suppressions à la source, le suivi des licences et une stratégie d'archivage des fichiers importants.

Les échecs de réseau ne sont jamais traduits en absence de besoins. Chaque source conserve son propre suivi, avec les dates de consultation et limites de collecte. Aucune validation institutionnelle humaine n'est revendiquée.

## Contrôle local

```bash
python -m pytest -q tests/test_collecte_besoins_publics.py tests/test_publication_besoins_publics.py
python scripts/collecter_besoins_publics.py
```

La seconde commande interroge les interfaces officielles et conserve les résultats dans le répertoire local. Les propositions de fusion distantes relèvent exclusivement de la procédure GitHub autorisée.

Le premier relevé réel du 9 octobre 2026 a reçu 1 200 annonces sur 3 055 annoncées par la source, avec douze pages réussies et aucun échec. La présente révision porte la recherche à quarante-cinq pages ; la couverture effective de la fenêtre sera contrôlée lors de l'exécution suivante.

## Extraction expérimentale des offres individuelles

Après observation effective de trente colonnes du CSV officiel, le programme `scripts/extraire_offres_publiques.py` vérifie l'identifiant de la ressource, son schéma, sa licence déclarée et la taille du fichier. Il télécharge temporairement les octets du CSV courant, calcule leur empreinte SHA-256 et vérifie la taille déclarée avant toute publication.

Il retient les identifiants de poste, les organismes et employeurs, les métiers, intitulés, lieux, modalités contractuelles, dates, niveaux d'études, expérience et compétences attendues. Les autres colonnes, contacts et fichiers originaux ne sont pas recopiés. Les textes longs sont limités à une longueur déclarée, avec un compte explicite des cellules tronquées. Les répétitions de contenu identique sont comptées. Lorsqu'une même référence de poste désigne plusieurs contenus différents, chaque variante des champs retenus reçoit une empreinte distincte. Le manifeste indique les références possédant plusieurs variantes, sans choisir arbitrairement un enregistrement à conserver.

Les offres sont classées dans seize partitions `institutionnel/besoins_publics/offres_postes/lot_XX.jsonl`. Le manifeste `institutionnel/besoins_publics/manifest_offres_postes.json` consigne la source, son empreinte, les nombres de lignes et les limites de la transformation. Ce dispositif suit le **fichier courant** et conserve les états antérieurs dans l'historique des modifications du dépôt ; l'archivage exhaustif des fichiers annuels originaux relève d'un chantier distinct.

La première extraction réelle a été publiée avec son manifeste le 9 octobre 2026 ; son contenu n'a pas fait l'objet d'une relecture institutionnelle indépendante. Si le schéma ou la taille diffère des renseignements publiés, l'extraction échoue et les anciennes partitions sont conservées ; la collecte des marchés poursuit son fonctionnement indépendamment.

À compter de la présente révision, chaque partition publiée possède une empreinte SHA-256 enregistrée dans le manifeste. Lors d'une actualisation ultérieure, **l'absence ou la modification d'une seule des seize partitions interdit de conclure que l'extrait antérieur est inchangé**. Un ancien manifeste sans empreintes de partitions impose une nouvelle extraction depuis la source officielle ; la reconstruction ne constitue pas un nouvel épisode empirique.

Le champ `couverture_integrale_du_csv` exige simultanément l'absence de ligne écartée et l'absence de cellule tronquée. Sa valeur `false` pour le fichier du 9 octobre provient au moins des 3 693 troncatures signalées : elle ne signifie pas que seules certaines lignes du CSV ont été lues. La vérification de l'exactitude de toutes les valeurs extraites demanderait une procédure supplémentaire de rapprochement avec le fichier original.

L'interface `/api/v1/offres-emplois` vérifie également, pendant la lecture, la présence des seize partitions lorsque le manifeste annonce des offres, la conformité des empreintes quand elles existent et le décompte total d'une recherche sans filtre. En présence d'un lot manquant, altéré ou incohérent, elle retourne une erreur de service (503), au lieu de publier silencieusement une liste incomplète. Les anciennes extractions sans empreintes conservent un contrôle de présence et de décompte, mais ne disposent pas d'une vérification cryptographique par partition jusqu'à leur prochaine reconstruction.
