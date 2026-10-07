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

## Modèle

Les objets territoriaux utilisent l’espace d’identifiants `FRONTIERE-TERR-COG-*` et sont stockés séparément des objets `FRONTIERE-INST-*`.

La version 1 ingère les unités territoriales courantes suivantes : régions, départements, arrondissements, cantons et pseudo-cantons, communes, arrondissements municipaux, communes associées, communes déléguées, collectivités et territoires français d’outre-mer, ainsi que leurs communes ou zonages équivalents.

Le fichier COG des collectivités territoriales exerçant les compétences départementales (`CTCD`) est volontairement traité autrement. Il décrit des collectivités publiques — par exemple un département en tant que collectivité — et non une subdivision géographique homogène avec `REG`, `DEP` ou `COM`. FRONTIÈRE conserve ce fichier dans le manifeste source et les codes CTCD dans les lignes Insee originales, sans créer de nœud `FRONTIERE-TERR-*` pour ces objets. Leur rapprochement avec les entités institutionnelles fera l’objet d’un croisement dédié fondé sur des identifiants et des sources officielles supplémentaires.

Chaque objet conserve la ligne CSV Insee originale dans `source_insee`, son code, son type, le millésime, la date de référence, une empreinte cryptographique, la date de collecte et la date d’observation FRONTIÈRE.

`reference_le = 2026-01-01` signifie que le territoire appartient au millésime courant. Cette date n’est pas utilisée comme date de création juridique du territoire. Les périodes historiques seront ajoutées à partir des fichiers historiques et des événements du COG dans une étape distincte.

## Relations territoriales

Trois relations sont matérialisées dans cette première version.

`APPARTIENT_A` représente les rattachements explicitement publiés dans le COG, par exemple commune vers département, département vers région ou zonage d’outre-mer vers sa collectivité.

`PARTIE_DE` représente le rattachement explicite d’un arrondissement municipal, d’une commune associée ou d’une commune déléguée à sa commune parente.

`A_POUR_CHEF_LIEU` représente les codes de chef-lieu ou de bureau centralisateur publiés par l’Insee.

Une relation n’est créée que si sa cible est résolue par un code COG exact. Les références non résolues sont conservées dans `institutionnel/anomalies_cog.json`.

## Croisement avec l’Annuaire DILA

Les entités locales déjà ingérées conservent les codes Insee publiés par la DILA dans leur champ `territoires`. L’ingestion COG mesure leur résolution vers le nouveau référentiel territorial et écrit `institutionnel/resolution_annuaire_cog.json`.

La résolution suit une règle stricte. Une commune courante `TYPECOM=COM` est prioritaire. À défaut, un zonage d’outre-mer `COMER-COM` unique est accepté. Un autre code n’est résolu que s’il possède une cible unique. Les cas ambigus et absents restent explicitement signalés. Aucun rapprochement par nom n’est autorisé.

Le manifeste COG conserve une empreinte de dépendance de l’Annuaire local. Une modification du snapshot DILA force donc le recalcul du rapport de résolution même si le millésime COG n’a pas changé.

## Découverte des fichiers

L’importeur n’est pas couplé à des noms de fichiers fragiles. Il inspecte les en-têtes CSV et identifie chaque table courante par son schéma de colonnes. Les fichiers historiques présents dans l’archive ne sont pas confondus avec les tables courantes.

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