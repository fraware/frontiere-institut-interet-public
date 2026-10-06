# Référentiel institutionnel

Ce répertoire contient la représentation canonique et la surveillance de l'écosystème institutionnel français utilisée par FRONTIÈRE.

## État courant

Le snapshot DILA du 6 octobre 2026 contient **7 903 entités canoniques** et **8 071 relations hiérarchiques résolues**. **7 898 entités** disposent d'un parent principal. **158 références hiérarchiques** restent explicitement non résolues et sont conservées dans `anomalies_roae.json`.

L'état détaillé et la méthode de reproduction figurent dans [INGESTION_ROAE_V1.md](../docs/INGESTION_ROAE_V1.md).

## Fichiers de contrôle

- `sources_v1.json` : registre des sources officielles ;
- `schema_entite_v1.json` : schéma d'une entité institutionnelle ;
- `schema_relation_v1.json` : schéma d'une relation institutionnelle ;
- `couverture_cible_v1.json` : périmètres attendus et critères de couverture ;
- `etat_sources.json` : état courant des sources après surveillance ;
- `alertes_sources.json` : changements ou erreurs détectés ;
- `statistiques_roae.json` : couverture du snapshot DILA courant ;
- `anomalies_roae.json` : références hiérarchiques qui ne peuvent pas être résolues dans le snapshot SI ;
- `instantanes/roae_manifest.json` : provenance, empreinte de l'archive et empreintes des partitions ;
- `entites/roae/` : 32 partitions des entités canoniques ;
- `relations/roae/` : 16 partitions des relations hiérarchiques.

## Principes

Une entité canonique n'est jamais identifiée par son seul nom.

Chaque fait important conserve sa provenance.

Les états historiques restent reconstructibles.

Une information inférée reste distinguée d'une information explicitement publiée.

Les fichiers bruts volumineux ne sont pas recopiés inutilement dans l'historique Git. Le dépôt conserve la représentation canonique, les références de source, les empreintes et les événements de changement.

La conception détaillée figure dans [le document de référence](../docs/REFERENTIEL_INSTITUTIONNEL_V1.md).
