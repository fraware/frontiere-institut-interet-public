# Référentiel institutionnel

Ce répertoire contient la représentation canonique et la surveillance de l'écosystème institutionnel français utilisée par FRONTIÈRE.

## Fichiers de contrôle

- `sources_v1.json` : registre des sources officielles ;
- `schema_entite_v1.json` : schéma d'une entité institutionnelle ;
- `schema_relation_v1.json` : schéma d'une relation institutionnelle ;
- `couverture_cible_v1.json` : périmètres attendus et critères de couverture ;
- `etat_sources.json` : état courant des sources après surveillance ;
- `alertes_sources.json` : changements ou erreurs détectés.

## Principes

Une entité canonique n'est jamais identifiée par son seul nom.

Chaque fait important conserve sa provenance.

Les états historiques restent reconstructibles.

Une information inférée reste distinguée d'une information explicitement publiée.

Les fichiers bruts volumineux ne sont pas recopiés inutilement dans l'historique Git. Le dépôt conserve la représentation canonique, les références de source, les empreintes et les événements de changement.

La conception détaillée figure dans [le document de référence](../docs/REFERENTIEL_INSTITUTIONNEL_V1.md).
