# Ingestion du Référentiel de l'organisation administrative de l'État

## Objet

Cette ingestion constitue la colonne vertébrale du graphe institutionnel de FRONTIÈRE.

La source est le Référentiel de l'organisation administrative de l'État produit par la Direction de l'information légale et administrative. La DILA indique que ce référentiel couvre environ six mille organismes, les services centraux jusqu'au niveau des bureaux, leurs missions, leur hiérarchie, leurs coordonnées et leurs responsables.

Source officielle :

https://www.data.gouv.fr/datasets/referentiel-de-lorganisation-administrative-de-letat

Fichier courant :

https://echanges.dila.gouv.fr/OPENDATA/RefOrgaAdminEtat/FluxAnneeCourante/dila_refOrga_admin_Etat_fr_latest.zip

## Reproduction

```bash
python scripts/ingerer_roae.py
```

L'importeur télécharge la dernière archive DILA, exige un fichier JSON unique, vérifie l'unicité des identifiants et produit des données canoniques partitionnées.

## Sorties

```text
institutionnel/
  entites/roae/
    roae_00.jsonl
    ...
    roae_31.jsonl
  relations/roae/
    roae_hierarchie_00.jsonl
    ...
    roae_hierarchie_15.jsonl
  instantanes/
    roae_manifest.json
  statistiques_roae.json
```

Les partitions servent à maintenir des fichiers de taille raisonnable et à limiter les différences Git lors des mises à jour.

## Transformation sans perte

Chaque entité comporte deux représentations complémentaires.

La première est canonique : identité, identifiants, mission, responsables, coordonnées, fondements juridiques et provenance.

La seconde, `source_dila`, conserve l'enregistrement DILA original. L'ingestion ne supprime donc pas silencieusement un champ du producteur. Les améliorations futures du modèle canonique peuvent être recalculées depuis les enregistrements conservés.

## Identité

L'identifiant canonique est construit à partir de l'identifiant DILA :

```text
FRONTIERE-INST-DILA-<IDENTIFIANT DILA>
```

Les SIREN, SIRET, anciens identifiants et identifiants partenaires restent enregistrés séparément. Aucun rapprochement entre organismes n'est effectué sur la seule similarité de leur nom.

## Hiérarchie

Les spécifications DILA décrivent le champ `hierarchie` comme l'ensemble des services fils et des autres liens hiérarchiques fils.

FRONTIÈRE représente un lien direct sous la forme :

```text
service enfant --DEPEND_DE--> service parent
```

Le type de hiérarchie publié par la DILA est conservé comme qualificatif de la relation.

Une relation dont la cible ne peut pas être résolue par identifiant reste comptée dans `liens_hierarchiques_non_resolus`. Elle n'est pas inventée à partir du nom.

## Temporalité

La date d'observation de FRONTIÈRE est enregistrée dans `observe_le`.

Les dates DILA de création, modification et diffusion sont conservées dans `metadata_dila`. Elles ne sont pas automatiquement transformées en période de validité juridique de l'organisme, car leur signification est celle du référentiel source.

## Provenance et attribution

Le manifeste conserve :

- le producteur ;
- la paternité demandée par la DILA ;
- la Licence Ouverte 2.0 ;
- la page du jeu de données ;
- l'adresse longue de téléchargement ;
- le nom du fichier ;
- le nom du JSON contenu dans l'archive ;
- la date d'observation ;
- la dernière modification HTTP ;
- l'empreinte SHA-256 de l'archive ;
- les empreintes de toutes les partitions.

Chaque entité conserve également une empreinte de son enregistrement source.

## Mise à jour

Une action GitHub exécute l'ingestion quotidiennement. Elle ne crée un commit que si les données canoniques ont changé.

Le référentiel DILA devient ainsi un état versionné de l'organisation administrative de l'État, avec historique des transformations dans Git.

## Limites de cette première ingestion

Cette source constitue la colonne vertébrale de l'État. Elle ne représente pas à elle seule l'intégralité de l'écosystème public français.

Les vagues suivantes doivent relier au même graphe :

- collectivités et intercommunalités ;
- opérateurs budgétaires ;
- structures de recherche ;
- établissements d'enseignement supérieur ;
- santé et médico-social ;
- participations publiques ;
- textes et événements juridiques.

La mesure de couverture reste le critère permettant de distinguer une source ingérée d'un périmètre réellement complet.
