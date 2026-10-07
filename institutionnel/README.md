# Référentiel institutionnel

Ce répertoire contient la représentation canonique et la surveillance de l'écosystème institutionnel français utilisée par FRONTIÈRE.

## État courant

Le snapshot de l'Annuaire DILA observé le 6 octobre 2026 contient **93 782 enregistrements**. Le graphe FRONTIÈRE couvre les trois catégories du snapshot :

- **7 903 SI** par le Référentiel de l'organisation administrative de l'État ;
- **79 585 SL** et **6 294 SIL**, soit **85 879 entités locales**, par l'API de l'Annuaire.

Le sous-graphe SI contient **8 071 relations hiérarchiques**. Le sous-graphe local et ses relations croisées contiennent **4 155 relations**.

Le croisement avec les entités locales résout les **158 références du ROAE** qui étaient impossibles à fermer dans le seul snapshot SI. Le flux local contient encore **100 références hiérarchiques** dont la cible n'apparaît dans aucune des trois catégories courantes de l'Annuaire. Elles restent explicitement enregistrées comme anomalies.

La compétence géographique massive est interrogée directement auprès de l'API DILA au moment de la requête. Elle n'est pas copiée intégralement dans Git.

Le Code officiel géographique de l’Insee fournit un espace d’identité distinct pour les unités territoriales. Le millésime 2026 produit **40 345 unités territoriales** et **150 421 relations territoriales**. Les nœuds `FRONTIERE-TERR-COG-*` restent séparés des organisations `FRONTIERE-INST-*`. Les codes CTCD sont conservés comme données source sans être assimilés à des territoires, car le fichier Insee correspondant décrit des collectivités publiques exerçant les compétences départementales.

Le croisement Annuaire–COG résout **305 449 / 305 456** références vers le COG courant. Les **7 références résiduelles** sont toutes expliquées par les tables historiques officielles du COG ; aucune ne reste sans trace historique et aucune résolution ambiguë n’est observée.

→ [Référentiel territorial COG](../docs/INGESTION_COG_V1.md)

→ [Ingestion du ROAE](../docs/INGESTION_ROAE_V1.md)  
→ [Ingestion de l'Annuaire local](../docs/INGESTION_ANNUAIRE_LOCAL_V1.md)

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
- `relations/roae/` : 16 partitions des relations hiérarchiques ;
- `statistiques_annuaire_local.json` : couverture des catégories SL et SIL ;
- `anomalies_annuaire_local.json` : références hiérarchiques locales non résolues ;
- `resolution_roae_local.json` : résolution croisée des références SI vers les objets locaux ;
- `instantanes/annuaire_local_manifest.json` : provenance et empreinte sémantique de l'export local ;
- `entites/locales/` : 128 partitions des entités SL/SIL ;
- `relations/locales/` : 32 partitions des relations locales et croisées ;
- `schema_territoire_v1.json` : schéma des unités territoriales de référence ;
- `schema_relation_territoriale_v1.json` : schéma des relations entre territoires ;
- `instantanes/cog_manifest.json` : provenance et empreintes du millésime COG courant ;
- `statistiques_cog.json` : couverture du référentiel territorial ;
- `anomalies_cog.json` : relations territoriales dont une cible exacte reste absente ;
- `resolution_annuaire_cog.json` : mesure du raccordement des codes Insee publiés par l’Annuaire ;
- `territoires/cog/` et `relations/territoriales/cog/` : partitions du graphe territorial.

## Principes

Une entité canonique n'est jamais identifiée par son seul nom.

Chaque fait important conserve sa provenance.

Les états historiques restent reconstructibles.

Une information inférée reste distinguée d'une information explicitement publiée.

Les fichiers bruts volumineux ne sont pas recopiés inutilement dans l'historique Git. Le dépôt conserve la représentation canonique, les références de source, les empreintes et les événements de changement.

La conception détaillée figure dans [le document de référence](../docs/REFERENTIEL_INSTITUTIONNEL_V1.md).
