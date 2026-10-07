# Annuaire de l’administration — services et guichets locaux

## Objet

Ce document décrit l’importation des services et guichets locaux publiés dans l’Annuaire de l’administration par la Direction de l’information légale et administrative.

Source officielle :

https://api-lannuaire.service-public.gouv.fr/

Page de référence :

https://www.data.gouv.fr/datasets/service-public-gouv-fr-annuaire-de-ladministration-base-de-donnees-locales

## État observé le 7 octobre 2026

L’export contient **93 782 enregistrements**.

La source utilise trois codes techniques de catégorie. FRONTIÈRE ne demande pas au lecteur de les mémoriser : la catégorie `SI` correspond à la partie déjà couverte par le Référentiel de l’organisation administrative de l’État ; les catégories `SL` et `SIL` constituent les deux ensembles locaux importés ici.

| Ensemble | Nombre | Traitement |
| --- | ---: | --- |
| Partie déjà couverte par le référentiel de l’organisation de l’État | 7 905 | réutilisée |
| Premier ensemble local de l’Annuaire | 79 583 | importé ici |
| Second ensemble local de l’Annuaire | 6 294 | importé ici |
| **Total de l’export** | **93 782** | **couvert par l’union des deux importations** |

Les deux ensembles locaux produisent **85 877 objets normalisés**.

Cette couverture est complète pour cet export précis. Elle ne signifie pas que ces 93 782 enregistrements représentent toutes les personnes morales, collectivités, opérateurs, établissements de santé ou structures de recherche du secteur public français.

### Informations disponibles sur les 85 877 objets locaux

| Information publiée | Objets concernés |
| --- | ---: |
| Coordonnées | 85 694 |
| Territoire indiqué directement | 85 579 |
| Numéro SIRET | 54 651 |
| Numéro SIREN | 44 050 |
| Mission | 29 903 |
| Responsable | 5 201 |
| Fondement juridique | 1 546 |

Un champ absent reste absent. FRONTIÈRE ne complète pas silencieusement la source par une supposition.

## Hiérarchie et raccordement avec l’organisation de l’État

L’importation produit **4 155 relations hiérarchiques résolues**. **3 536 objets locaux** disposent d’un parent principal directement justifié par un lien publié.

Il reste **100 références hiérarchiques non résolues**. Elles sont conservées dans `institutionnel/anomalies_annuaire_local.json`.

Le croisement entre les deux publications DILA résout également les **158 références** qui manquaient dans la seule publication consacrée à l’organisation de l’État. Cette résolution utilise des identifiants exacts, jamais une simple ressemblance de nom.

Le résultat du croisement figure dans `institutionnel/resolution_roae_local.json`.

## Compétence géographique

La DILA publie un jeu séparé qui relie une commune, un type de service et les services compétents pour cette commune.

Ce jeu contient plusieurs millions d’enregistrements. FRONTIÈRE l’interroge directement au moment d’une recherche au lieu d’en copier l’intégralité dans Git.

Exemple :

```bash
python scripts/rechercher_competence_geographique.py --commune 75056 --type mairie
```

La réponse est reliée aux objets institutionnels déjà présents grâce aux identifiants publiés par la source.

## Identité et provenance

Chaque objet local reçoit un identifiant technique de la forme :

```text
FRONTIERE-INST-DILA-LOCAL-<IDENTIFIANT DILA>
```

L’identifiant de la source, les numéros SIREN et SIRET, les territoires, les coordonnées, les missions et les autres champs disponibles restent conservés séparément.

Chaque objet conserve son identifiant dans la source, l’adresse de la source, la date de collecte, une empreinte de l’enregistrement et les champs structurés nécessaires à l’utilisation du référentiel.

## Détecter un vrai changement

L’ordre des enregistrements dans l’export peut varier sans que le contenu institutionnel change.

FRONTIÈRE calcule une empreinte du fichier téléchargé et une seconde empreinte construite à partir du contenu des enregistrements indépendamment de leur ordre. Cette seconde mesure évite qu’un simple réordonnancement crée un faux changement dans Git.

L’état local dépend aussi de la publication consacrée à l’organisation de l’État. Une modification de cette source déclenche un nouveau calcul des raccordements, même si l’export local est inchangé.

## Fichiers produits

```text
institutionnel/
  entites/locales/
  relations/locales/
  instantanes/annuaire_local_manifest.json
  statistiques_annuaire_local.json
  anomalies_annuaire_local.json
  resolution_roae_local.json
```

Les 85 877 objets locaux sont répartis dans 128 fichiers et les relations dans 32 fichiers afin de garder des tailles de fichier raisonnables.

## Vérifications automatiques

Les tests contrôlent notamment les empreintes, les nombres d’objets et de relations, l’unicité des identifiants, l’existence des deux extrémités de chaque relation, la provenance et la résolution des 158 références manquantes dans la publication de l’organisation de l’État.

## Mise à jour

L’actualisation de l’Annuaire est déclenchée après la réussite de l’actualisation de l’organisation de l’État. Les deux opérations sont sérialisées afin d’éviter des écritures concurrentes sur la branche principale.

## Limite de conservation historique

L’export brut complet n’est pas copié dans Git. Le dépôt conserve son empreinte, une empreinte indépendante de l’ordre des enregistrements et les objets normalisés produits par la transformation.

Une conservation probante de chaque export historique exigerait un stockage d’archives externe et immuable.

## Prochaines sources possibles

Les extensions possibles comprennent le référentiel territorial de l’Insee, la base nationale des intercommunalités, les données budgétaires des opérateurs de l’État, les structures publiques d’enseignement supérieur et de recherche, le répertoire des établissements sanitaires et médico-sociaux, les participations publiques et les textes juridiques.

Aucune nouvelle source n’est intégrée uniquement pour augmenter le volume. Elle doit apporter une information utile à un cas, améliorer une couverture mesurée ou résoudre une inconnue clairement identifiée.
