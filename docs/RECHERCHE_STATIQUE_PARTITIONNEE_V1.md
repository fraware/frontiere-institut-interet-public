# FRONTIÈRE — Recherche statique étendue

La recherche initiale limitée à 1 900 résultats reste disponible sur la page d'accueil. La page `recherche-etendue.html` consulte une nouvelle collection **bornée à 5 000 documents par source**, segmentée par **source et année de publication**. Les trois familles sont BOAMP, offres d'emploi public et marchés attribués DECP. Les sources sans territoire explicite ne reçoivent aucune localisation inférée.

## Index et provenance

La commande `node scripts/construire_partitions_statiques.mjs` parcourt les archives versionnées et écrit `site_frontiere/partitions/manifeste.json` ainsi que les lots `part-<source>-<année>-<numéro>.json`. Chaque lot contient au plus 700 documents et un mégaoctet. Le manifeste déclare ses tailles, son nombre de documents, son empreinte SHA-256 et la révision Git de la source lorsqu'elle est disponible.

Chaque publication construit les données depuis le dépôt sans appel réseau vers les producteurs. Les archives ne sont pas exhaustives. Le chiffre maximal de 15 000 résultats ne représente donc ni le nombre national réel de marchés ni celui des offres disponibles.

L'interface charge uniquement les lots de l'année et de la source demandées par l'utilisateur. Elle affiche au plus 100 correspondances par recherche, tout en comptant l'ensemble des résultats identifiés dans les lots sélectionnés. Le traitement s'exécute dans le navigateur ; aucun serveur ou stockage persistant payant n'est ajouté.

La consultation vérifie la taille des lots, leur empreinte cryptographique SHA-256 avec l'interface native du navigateur et la cohérence du contenu avec le manifeste. Cette vérification est également répétée sur les archives réelles par les contrôles GitHub. Si le navigateur ne permet pas le contrôle d'empreinte, ou si un seul lot échoue, aucun résultat de la recherche demandée n'est affiché. Toute erreur de lecture interrompt la restitution pour éviter de présenter des résultats partiels comme complets.

## Contrôles

```sh
node --test tests/test_partitions_statiques.mjs
node scripts/construire_partitions_statiques.mjs
```

Le contrôle CI vérifie, sur les véritables archives, l'empreinte, le nombre de documents et la taille de chaque lot, ainsi que la présence de plus de 1 900 documents au total.

La segmentation territoriale exige des champs géographiques fiables des producteurs et reste à préparer séparément. Le filtre de période est annuel, fondé sur les dates documentaires analysables ; aucune date absente n'est inventée.
