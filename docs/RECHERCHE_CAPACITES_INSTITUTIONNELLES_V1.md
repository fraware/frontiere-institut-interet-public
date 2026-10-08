# Recherche locale de capacités institutionnelles — première version

**État : instrument documentaire expérimental.** Le programme dresse une première liste de notices institutionnelles à examiner. Il ne conclut ni à l'existence de compétences spécialisées accessibles, ni à leur disponibilité, ni à l'opportunité d'une mobilisation.

## Finalité et données utilisées

Le référentiel de FRONTIÈRE rassemble les notices normalisées de la Direction de l'information légale et administrative relatives à l'organisation administrative de l'État et aux services locaux. Ces notices portent notamment l'identité des organismes, leurs missions publiées, la provenance de l'enregistrement, sa date de collecte et son état déclaré.

La recherche exploite uniquement quatre familles de champs : le nom officiel, les anciens noms, les textes de **missions expressément déclarées comme publiées et munies d'une référence de source**, et, si la notice en contient, les capacités expressément publiées et sourcées. Les conclusions analytiques, notes libres, noms de responsables et coordonnées individuelles ne participent pas à l'indexation.

Une source de mission ou une mention de capacité publiée constitue un **indice documentaire**. L'établissement de la disponibilité, de la possibilité juridique de mobilisation et de l'utilité pour le besoin considéré exige d'autres éléments qui ne sont pas contenus dans ces notices.

Les index sont calculés **localement** à partir des fichiers déjà présents dans le dépôt. Aucune interrogation à distance et aucun service d'intelligence artificielle externe n'interviennent.

## Construction et interrogation

Depuis la racine du dépôt, avec Python 3.11 ou une version ultérieure :

```bash
python scripts/rechercher_capacites_institutionnelles.py --construire
python scripts/rechercher_capacites_institutionnelles.py --verifier-index
python scripts/rechercher_capacites_institutionnelles.py --requete "chimie analytique des eaux" --limite 10
```

L'index est écrit par défaut dans `data/recherche_institutionnelle.sqlite3`. Ce fichier local est ignoré par Git et ne doit pas être publié dans le dépôt. Sa construction utilise SQLite et son moteur de recherche textuelle intégré.

Le programme accepte `--famille organisation_administrative_etat` pour limiter la recherche à une famille institutionnelle précise. Les résultats appartiennent aux notices marquées actives dans la source indexée. Un ancien statut actif ne démontre pas l'activité actuelle.

Les recherches portent sur des termes normalisés (casse, accents et ponctuation) et conservent la distinction entre :

- **Correspondance avec une mission ou capacité publiée** : la notice contient effectivement un ou plusieurs mots de la demande dans des passages sourcés.
- **Correspondance uniquement nominale** : les mots existent dans le nom ou dans un ancien nom, sans passage de mission ou de capacité publié correspondant.

Les deux ensembles sont séparés dans la sortie. Les correspondances documentaires sont classées à partir du nombre de termes recoupés et d'une pertinence textuelle calculée par le moteur ; ce classement ne constitue pas une probabilité de capacité opérationnelle. Les correspondances uniquement nominales ne sont jamais promues au rang de capacité identifiée.

Chaque résultat contient l'identifiant canonique de l'organisme, son nom, sa famille, son type institutionnel, le fichier source indexé, la date de la notice, les mots effectivement retrouvés, au plus deux passages publiés et la provenance de la notice. Les champs de disponibilité et de mobilisation restent explicitement **inconnus ou non établis**.

## Intégrité et reproductibilité

À la construction, le programme calcule une empreinte SHA-256 de chaque fichier institutionnel d'entrée, puis une empreinte ordonnée de l'ensemble. Chaque organisme conserve son identifiant et son fichier d'origine. Les identifiants dupliqués ou les notices dépourvues de provenance entraînent l'échec de la construction.

La nouvelle base est construite dans un fichier temporaire, puis remplace l'ancien index uniquement à la fin d'une construction complète. Une erreur ne doit donc pas détruire l'index précédemment utilisable.

La commande de recherche recalcule les empreintes des sources locales avant de restituer un résultat. Si un fichier a été ajouté, modifié ou retiré, elle refuse la recherche jusqu'à reconstruction. Cette vérification porte sur la correspondance des fichiers avec l'index ; elle n'établit pas leur origine historique indépendante ni la véracité des assertions.

Pour des essais isolés ou une application locale, les chemins sont paramétrables :

```bash
python scripts/rechercher_capacites_institutionnelles.py \
  --construire \
  --entites /chemin/vers/entites \
  --index /chemin/prive/recherche.sqlite3

python scripts/rechercher_capacites_institutionnelles.py \
  --requete "analyse des eaux" \
  --entites /chemin/vers/entites \
  --index /chemin/prive/recherche.sqlite3
```

Les tests utilisent des **notices artificielles** et vérifient notamment les missions non publiées, les identifiants répétés, les sources modifiées, les notices historiques non actives et la séparation entre proximité nominale et mission publiée. Aucun score sur des besoins institutionnels réels n'est revendiqué.

## Limites de cette première version

La recherche est **lexicale** : elle ne reconnaît pas toutes les synonymies et ne comprend pas les opérations scientifiques décrites implicitement. Chaque classe de preuve est désormais interrogée séparément avec un plafond de mille candidats pour borner le calcul. Le moteur conserve jusqu'à mille candidats pour les capacités publiées, mille pour les missions, mille pour les disciplines et mille pour les noms. Cette séparation empêche que de très nombreuses ressemblances de noms saturent le quota et fassent disparaître toutes les disciplines ou missions. Les plafonds effectivement atteints sont signalés par champ et les catégories restent descriptives, sans classement commun de capacité réelle. Une recherche vide ou trop générale est refusée. Les familles et les états suivent les notices actuelles du dépôt, avec leurs limites de couverture.

Les liens fournis identifient la provenance des notices ; ils ne désignent pas nécessairement le passage exact d'un document original. Une absence de résultat signifie seulement qu'aucune concordance suffisante n'a été trouvée dans le périmètre textuel exploré. Elle **ne constitue pas** une démonstration qu'aucune capacité publique n'existe.

Les jeux de compétence géographique de l'Annuaire sont distincts. Pour retrouver un organisme officiellement compétent pour un type de service sur une commune, utiliser l'outil prévu dans `scripts/rechercher_competence_geographique.py`. La présence d'un organisme dans une commune ne prouve pas qu'il détient la capacité scientifique demandée.

## Étapes techniques ultérieures

Les premières améliorations reproductibles seront un jeu de requêtes de développement assorti de jugements de référence dont les limites sont explicites, la gestion des noms officiels et des changements de périmètre, la recherche de passages précis dans les documents sources et un couplage documenté avec le répertoire de compétence géographique.

La création d'un classement n'autorise aucune affirmation de mobilisation effective. Les règles générales de distinction entre capacité identifiée, capacité pertinente et capacité disponible restent celles de `docs/REGLES_DECISION.md`.


## Vérification automatisée sur la totalité des notices

Le fichier `.github/workflows/recherche_missions.yml` définit un essai complémentaire distinct des tests unitaires. Il construit un index à partir de **tous les fichiers institutionnels présents dans la révision examinée**, dans un répertoire temporaire du système d'intégration, puis vérifie leurs empreintes et exécute une requête documentaire. Ce contrôle se déclenche lors d'une modification du moteur, de ses fichiers sources ou de sa configuration.

Des seuils conservateurs signalent une perte importante de couverture lors d'un changement de données. Le bilan affiche uniquement des **effectifs techniques et une empreinte**, sans prétendre que les missions sont scientifiquement pertinentes pour une demande, ni que des organismes sont disponibles. La requête d'essai vérifie le fonctionnement sur les fichiers réels ; elle n'est pas une mesure de précision ou de rappel.

Le résultat du contrôle dépend de la révision du référentiel. Les fichiers originaux sont conservés dans Git ; l'index temporaire est recréé, puis détruit avec l'environnement d'exécution. Aucune donnée individuelle nouvelle et aucun résultat empirique indépendant ne sont produits.


## Classements scientifiques des structures de recherche

La deuxième version de l'index intègre les `domaines_recherche` du répertoire ministériel des structures de recherche publiques actives. Ces descriptions et classifications doivent être explicitement publiées, associées à une référence de source et déclarées comme telles dans la notice normalisée.

Les réponses sont réparties en **trois ensembles** : correspondances avec des missions ou capacités explicitement publiées, correspondances avec des domaines scientifiques publiés, et correspondances exclusivement fondées sur le nom de l'organisme. Cette distinction évite qu'un laboratoire classé dans une discipline soit automatiquement traité comme détenteur d'une capacité opérationnelle ou comme organisme disponible. Chaque famille de résultats possède sa propre limite et le classement textuel n'établit aucune priorité institutionnelle.

L'index porte la version technique `recherche-missions-institutionnelles-v2` et les réponses `orientation-documentaire-v2`. L'ancien index local est incompatible avec cette structure : exécuter à nouveau la commande `--construire` pour incorporer les domaines scientifiques et les huit partitions du RNSR. La comparaison des empreintes des fichiers reste obligatoire avant chaque interrogation.

Les structures sans domaine indiqué restent retrouvables par leur nom, mais aucune discipline n'est ajoutée par supposition. Les classifications ministérielles doivent être confrontées à des preuves distinctes pour conclure sur les instruments, les personnels, les compétences effectivement présentes ou leur disponibilité.


Une requête à laquelle correspondent plus de mille notices dans une même classe reste **incomplète pour cette classe**. Le programme expose les effectifs examinés par champ, les catégories tronquées et le nombre total de candidats uniques retenus. Ces nombres ne correspondent ni au nombre total d'organismes compétents, ni à un rappel mesuré. Toute conclusion d'absence exige une démarche indépendante et des pièces adaptées.


## Comptabilité des résultats écartés par la restitution

Le résultat de la recherche publie désormais `restitution_par_classe`. Pour chacun des trois niveaux de preuve, il indique le nombre de candidats examinés dans la classe, le nombre effectivement restitué, le nombre écarté par la limite de présentation et l'existence éventuelle d'une troncature. Ces effectifs sont distincts des limites internes à l'interrogation de l'index, signalées dans `champs_dont_les_resultats_sont_tronques`.

Un candidat écarté par un plafond de restitution n'est pas une ressource absente du référentiel. L'effectif observé ne mesure pas l'exhaustivité réelle des structures publiques, notamment en présence de synonymes et de descriptions manquantes. Une catégorie dont la restitution est tronquée exige une recherche plus précise pour son exploitation opérationnelle.
