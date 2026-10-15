# FRONTIÈRE — Verrou de cohérence du bilan DECP

## Contrat

Le rapport public `institutionnel/decp/bilan_index_unifie.json`
atteste un état précis de deux relevés versionnés :

- `institutionnel/decp/sonde_aife_json.json` ;
- `institutionnel/decp/lot_dgfip_xml.json`.

Un changement de notices, de source, de taille déclarée ou de métadonnées
dans ces relevés risque de rendre les résultats calculés précédemment
incohérents. La vérification reconstruit **en lecture seule des archives**
un index SQLite temporaire, puis compare les 17 indicateurs du rapport
publié aux valeurs recalculées, notamment les identités SIRET–marché,
versions, attestations et empreintes canoniques des deux relevés.

Commande :

```sh
python -m scripts.verifier_coherence_bilan_decp
```

Elle est désormais exécutée en tant qu'étape explicite de la
procédure GitHub de vérification et en tant que test d'intégration.
Un écart fait échouer la procédure et empêche de considérer la
publication comme un état cohérent.

## Cas des contributions anciennes

La demande [#449](https://github.com/fraware/frontiere-institut-interet-public/pull/449)
propose une modification substantielle du registre DGFiP.
Avant toute fusion, reconstruire le bilan sur la version proposée,
examiner les nouveaux identifiants et attestations et publier le bilan
recalculé **avec le relevé correspondant dans la même contribution**.

La demande [#448](https://github.com/fraware/frontiere-institut-interet-public/pull/448)
n'actualisait que des dates d'observation de catalogue, sans nouvel
inventaire documentaire démontré. Elle a été close sans fusion.

## Ce que ce contrôle démontre

Ce contrôle prouve que le bilan publié dérive effectivement des deux
fichiers archivés, selon les règles de normalisation et de dédoublonnage
du projet. Le contrôle d'intégrité SQLite est également effectué.

**Il ne prouve ni l'authenticité externe des ressources, ni leur couverture
nationale exhaustive, ni l'actualité des procédures, ni la disponibilité
d'un marché.** La vérification des téléchargements officiels, des
identifiants producteurs, des empreintes des fichiers bruts et de leur
date de modification constitue un contrôle indépendant.

Toute augmentation des chiffres de FRONTIÈRE doit reposer sur ces
deux familles de preuves.
