# Référentiel territorial COG — version 1

## Objet

Cette ingestion ajoute à FRONTIÈRE un référentiel territorial distinct du référentiel institutionnel. Le Code officiel géographique de l’Insee décrit des unités géographiques et administratives. Une commune, un département ou une région au sens du COG ne doit donc pas être confondu silencieusement avec une mairie, une préfecture, un conseil départemental ou une autre organisation présente dans l’Annuaire de l’administration.

Le COG sert de système d’identité territoriale. Les institutions restent des objets institutionnels. Les liens futurs `COMPETENT_SUR` et `IMPLANTE_DANS` relieront explicitement ces deux familles d’objets.

## Source

Source de référence : Code officiel géographique au 1er janvier 2026, Insee.

Page officielle :

https://www.insee.fr/fr/information/8740222

Archive CSV :

https://www.insee.fr/fr/statistiques/fichier/8740222/cog_ensemble_2026_csv.zip

Le millésime 2026 est daté du 1er janvier 2026. La page Insee a été mise à jour le 24 février 2026. L’Insee indique notamment qu’aucune commune nouvelle n’a été créée entre le 2 janvier 2025 et le 1er janvier 2026, que 19 communes ont changé de nom et que 40 communes déléguées ou associées ont été supprimées.

## État courant

<!-- FRONTIERE:ETAT_COG:DEBUT -->
État du dernier cycle complet, observé le **2026-10-07**.

L’archive officielle produit **40 345 unités territoriales courantes** et **150 421 relations territoriales** dans FRONTIÈRE, avec **0 relation territoriale non résolue**.

La répartition courante comprend 34 875 communes, 2 105 communes déléguées, 2 293 cantons ou pseudo-cantons, 471 communes associées, 333 arrondissements, 101 départements, 45 arrondissements municipaux, 18 régions, 9 collectivités ou territoires français d’outre-mer, 95 zonages communaux associés à ces territoires.

Le croisement avec l’Annuaire DILA examine **305 454 références à des codes Insee** portées par **85 579 entités locales**. **305 447 références** correspondent exactement à une unité du COG courant. Les **7 références restantes** sont attestées par l’historique officiel du COG comme des codes ayant cessé d’être courants ; **0** reste sans trace historique et **0** cas est ambigu. Le taux de résolution vers le COG courant est de **99,9977 %** et le taux de références expliquées par le COG courant ou son historique est de **100,0 %**.

Les écarts historiques ne sont pas réécrits. `resolution_annuaire_cog.json` conserve pour chacun le code DILA, l’entité concernée, la dernière période historique connue et le dernier événement communal publié par l’Insee.
<!-- FRONTIERE:ETAT_COG:FIN -->

## Modèle

Les objets territoriaux utilisent l’espace d’identifiants `FRONTIERE-TERR-COG-*` et sont stockés séparément des objets `FRONTIERE-INST-*`.

La version 1 ingère les unités territoriales courantes suivantes : régions, départements, arrondissements, cantons et pseudo-cantons, communes, arrondissements municipaux, communes associées, communes déléguées, collectivités et territoires français d’outre-mer, ainsi que leurs communes ou zonages équivalents.

Le fichier COG des collectivités territoriales exerçant les compétences départementales (`CTCD`) est volontairement traité autrement. Il décrit des collectivités publiques — par exemple un département en tant que collectivité — et non une subdivision géographique homogène avec `REG`, `DEP` ou `COM`. FRONTIÈRE conserve ce fichier dans le manifeste source et les codes CTCD dans les lignes Insee originales, sans créer de nœud `FRONTIERE-TERR-*` pour ces objets. Leur rapprochement avec les entités institutionnelles fera l’objet d’un croisement dédié fondé sur des identifiants et des sources officielles supplémentaires.

Chaque objet conserve la ligne CSV Insee originale dans `source_insee`, son code, son type, le millésime, la date de référence, une empreinte cryptographique, la date de collecte et la date d’observation FRONTIÈRE.

`reference_le = 2026-01-01` signifie que le territoire appartient au millésime courant. Cette date n’est pas utilisée comme date de création juridique du territoire. Les tables « communes depuis 1943 » et « événements sur les communes » sont également lues comme sources auxiliaires de diagnostic. Elles ne créent aucun nœud territorial historique dans cette version. Elles servent à distinguer un code DILA absent du COG courant parce qu’il appartient à l’histoire administrative d’un code sans trace dans les tables historiques officielles.

Une référence historique reste une référence historique. FRONTIÈRE conserve la dernière période connue et le dernier événement sortant publié par l’Insee, sans remplacer silencieusement l’ancien code par le code postérieur. La matérialisation d’un graphe temporel complet des successions communales constitue une extension séparée.

## Relations territoriales

Trois relations sont matérialisées dans cette première version.

`APPARTIENT_A` représente les rattachements explicitement publiés dans le COG, par exemple commune vers département, département vers région ou zonage d’outre-mer vers sa collectivité.

`PARTIE_DE` représente le rattachement explicite d’un arrondissement municipal, d’une commune associée ou d’une commune déléguée à sa commune parente.

`A_POUR_CHEF_LIEU` représente les codes de chef-lieu ou de bureau centralisateur publiés par l’Insee.

Une relation n’est créée que si sa cible est résolue par un code COG exact. Les références non résolues sont conservées dans `institutionnel/anomalies_cog.json`.

## Croisement avec l’Annuaire DILA

Les entités locales déjà ingérées conservent les codes Insee publiés par la DILA dans leur champ `territoires`. L’ingestion COG mesure leur résolution vers le nouveau référentiel territorial et écrit `institutionnel/resolution_annuaire_cog.json`.

La résolution suit une règle stricte. Une commune courante `TYPECOM=COM` est prioritaire. À défaut, un zonage d’outre-mer `COMER-COM` unique est accepté. Un autre code n’est résolu que s’il possède une cible unique. Les cas ambigus et absents restent explicitement signalés. Aucun rapprochement par nom n’est autorisé.

Lorsqu’un code n’existe plus dans le millésime courant, l’importeur consulte les deux tables historiques officielles présentes dans la même archive. Le rapport distingue alors `CODE_HISTORIQUE_ABSENT_DU_COG_COURANT` de `CODE_ABSENT_SANS_TRACE_HISTORIQUE_COG`. Cette classification explique la provenance de l’écart sans transformer une ancienne référence territoriale en référence courante. Le taux de résolution courante et le taux de références expliquées restent deux métriques distinctes.

Le manifeste COG conserve une empreinte de dépendance de l’Annuaire local. Une modification du snapshot DILA force donc le recalcul du rapport de résolution même si le millésime COG n’a pas changé.

## Découverte des fichiers

L’importeur n’est pas couplé à des noms de fichiers fragiles. Il inspecte les en-têtes CSV et identifie chaque table par son schéma de colonnes. Les tables courantes, la table des communes depuis 1943 et la table des événements communaux sont des familles distinctes. Les tables historiques enrichissent le diagnostic sans entrer dans le stock territorial courant.

Une modification incompatible de la structure de l’archive produit une erreur explicite. Les chemins ZIP dangereux, les liens symboliques et les membres anormalement volumineux sont refusés.

## Sorties

```text
institutionnel/
  schema_territoire_v1.json
  schema_relation_territoriale_v1.json
  territoires/cog/
  relations/territoriales/cog/
  instantanes/cog_manifest.json
  statistiques_cog.json
  anomalies_cog.json
  resolution_annuaire_cog.json
```

## Actualisation

Le COG est une source annuelle, avec possibilité de correction de publication. FRONTIÈRE vérifie donc la source chaque semaine et lors d’une exécution manuelle. Le recalcul est également déclenché après une actualisation réussie de l’Annuaire local afin de maintenir le rapport de résolution croisée.

Aucun commit n’est créé lorsque l’archive, la version de transformation et la dépendance Annuaire sont inchangées.

## Étape suivante

BANATIC utilisera ce référentiel comme ancrage territorial. Les EPCI, syndicats et autres groupements resteront des entités institutionnelles identifiées notamment par SIREN. Leur périmètre sera relié aux communes COG par des relations explicites. Cette séparation évite d’assimiler un territoire à l’organisation qui l’administre.