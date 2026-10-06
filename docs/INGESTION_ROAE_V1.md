# Ingestion du Référentiel de l'organisation administrative de l'État

## Objet

Cette ingestion constitue la colonne vertébrale du graphe institutionnel de FRONTIÈRE.

La source est le Référentiel de l'organisation administrative de l'État produit par la Direction de l'information légale et administrative. La DILA indique que ce référentiel couvre environ six mille organismes, les services centraux jusqu'au niveau des bureaux, leurs missions, leur hiérarchie, leurs coordonnées et leurs responsables.

Source officielle :

https://www.data.gouv.fr/datasets/referentiel-de-lorganisation-administrative-de-letat

Fichier courant :

https://echanges.dila.gouv.fr/OPENDATA/RefOrgaAdminEtat/FluxAnneeCourante/dila_refOrga_admin_Etat_fr_latest.zip

## État observé au 6 octobre 2026

La publication DILA ingérée le 6 octobre 2026 contient **7 903 services institutionnels**. FRONTIÈRE en produit **7 903 entités canoniques** et **8 071 relations hiérarchiques résolues**.

Parmi ces entités :

- **7 898** disposent d'un parent principal dérivé d'un lien DILA `Service Fils` ;
- **5** n'ont pas de parent principal dans ce sous-graphe ;
- **7 797** disposent d'au moins une coordonnée ;
- **7 549** disposent d'au moins un responsable ;
- **1 568** disposent d'une mission publiée dans le flux ;
- **1 169** disposent d'au moins un texte de référence ;
- **416** exposent un SIREN dans ce flux ;
- **414** exposent un SIRET.

Le flux contient également **158 références hiérarchiques dont l'identifiant cible n'est pas présent dans le snapshot SI courant**. Elles sont conservées intégralement dans `institutionnel/anomalies_roae.json`. FRONTIÈRE ne crée aucune relation de remplacement par rapprochement de nom. Une partie de ces références pourra être résolue lors de l'ingestion des catégories locales de l'Annuaire de l'administration ; leur cause exacte reste à établir cas par cas.

Archive observée :

```text
dila_refOrga_admin_Etat_fr_20261006.json
SHA-256 ZIP: d9150c4e9ff5551019a02f4beefaeff956fb2fa3e3beb4c022b038204920c332
```

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
  anomalies_roae.json
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

La date d'observation de FRONTIÈRE est enregistrée dans `observe_le`. Une entité dont l'enregistrement source reste inchangé conserve sa date d'observation précédente. Le système compare l'empreinte de chaque enregistrement afin d'éviter de transformer une simple nouvelle exécution en faux changement institutionnel.

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

Une action GitHub exécute l'ingestion quotidiennement. L'empreinte de l'archive et la version de transformation sont vérifiées avant recalcul. Elle ne crée un commit que si la source ou la transformation produit un état canonique différent.

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
