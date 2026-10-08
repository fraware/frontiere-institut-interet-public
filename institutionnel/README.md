# Référentiel institutionnel

Ce répertoire contient les données normalisées utilisées par FRONTIÈRE pour retrouver des organismes publics, leurs relations et les territoires auxquels ils sont rattachés.

## État courant

<!-- FRONTIERE:ETAT_INSTITUTIONNEL:DEBUT -->
Dernier cycle complet observé le **2026-10-08** :

- **7 907 services ou organismes** issus du Référentiel de l’organisation administrative de l’État, avec **8 075 relations hiérarchiques résolues** ;
- **85 879 services et guichets locaux** issus de l’Annuaire de l’administration, avec **4 158 relations hiérarchiques locales ou croisées** ;
- **40 345 unités territoriales** issues du Code officiel géographique de l’Insee, reliées par **150 421 relations territoriales**.

L’Annuaire contient **305 557 références à des codes Insee**. **305 550** correspondent à une unité territoriale actuelle. Les **7** références restantes correspondent à d’anciens codes attestés par l’historique officiel. **0** référence reste inexpliquée et **0** cas est ambigu.

Le croisement des deux publications de la Direction de l’information légale et administrative résout également les **158 références hiérarchiques** dont la cible manquait dans la publication consacrée à l’organisation de l’État. Il reste **100 références hiérarchiques locales** dont la cible n’apparaît dans aucune catégorie courante de l’Annuaire.
<!-- FRONTIERE:ETAT_INSTITUTIONNEL:FIN -->

Le jeu de compétence géographique de l’Annuaire contient plusieurs millions d’enregistrements. Il est interrogé directement auprès de la source officielle au moment d’une recherche et n’est pas copié intégralement dans Git.

Les territoires de l’Insee restent séparés des organisations. Une commune constitue un territoire ; une mairie constitue une organisation.

→ [Organisation administrative de l’État](../docs/INGESTION_ROAE_V1.md)  
→ [Services et guichets locaux](../docs/INGESTION_ANNUAIRE_LOCAL_V1.md)  
→ [Territoires de référence de l’Insee](../docs/INGESTION_COG_V1.md)  
→ [Recherche locale de missions et capacités publiées](../docs/RECHERCHE_CAPACITES_INSTITUTIONNELLES_V1.md)

## Fichiers de contrôle

- `sources_v1.json` : liste des sources officielles et fréquence attendue de mise à jour ;
- `schema_entite_v1.json` : structure d’un objet institutionnel ;
- `schema_relation_v1.json` : structure d’une relation entre organisations ;
- `couverture_cible_v1.json` : familles d’organisations attendues et mesures de couverture ;
- `etat_sources.json` : état des sources après la dernière vérification ;
- `alertes_sources.json` : changements ou erreurs détectés ;
- `statistiques_roae.json` : statistiques de la source sur l’organisation administrative de l’État ;
- `anomalies_roae.json` : références hiérarchiques absentes de cette source isolée ;
- `statistiques_annuaire_local.json` : statistiques des services et guichets locaux ;
- `anomalies_annuaire_local.json` : références hiérarchiques locales non résolues ;
- `resolution_roae_local.json` : résultat du croisement entre les deux publications DILA ;
- `statistiques_cog.json` : statistiques des territoires de référence ;
- `anomalies_cog.json` : relations territoriales dont une cible exacte manque ;
- `resolution_annuaire_cog.json` : raccordement des codes Insee de l’Annuaire aux territoires.

Les répertoires `entites/`, `relations/`, `territoires/` et `instantanes/` contiennent les données normalisées et les informations permettant de vérifier leur provenance.

## Principes

- une organisation n’est jamais identifiée par son seul nom ;
- chaque fait important conserve sa provenance ;
- les états historiques restent reconstructibles ;
- une information déduite reste distincte d’une information publiée ;
- les fichiers bruts très volumineux ne sont pas recopiés inutilement dans l’historique Git.

La conception détaillée figure dans [le document de référence](../docs/REFERENTIEL_INSTITUTIONNEL_V1.md).
