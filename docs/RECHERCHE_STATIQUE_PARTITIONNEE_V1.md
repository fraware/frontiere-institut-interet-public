# FRONTIÈRE — Recherche statique étendue

La recherche initiale limitée à 1 900 résultats reste disponible sur la page d'accueil. La page `recherche-etendue.html` consulte une nouvelle collection **bornée à 5 000 documents par source**, segmentée par **source et année de publication**. Les trois familles sont BOAMP, offres d'emploi public et marchés attribués DECP. Les sources sans territoire explicite ne reçoivent aucune localisation inférée.

## Index et provenance

La commande `node scripts/construire_partitions_statiques.mjs` parcourt les archives versionnées et écrit `site_frontiere/partitions/manifeste.json` ainsi que les lots `part-<source>-<année>-<numéro>.json`. Chaque lot contient au plus 700 documents et un mégaoctet. Le manifeste déclare ses tailles, son nombre de documents, son empreinte SHA-256 et la révision Git de la source lorsqu'elle est disponible.

Chaque publication construit les données depuis le dépôt sans appel réseau vers les producteurs. Les archives ne sont pas exhaustives. Le chiffre maximal de 15 000 résultats ne représente donc ni le nombre national réel de marchés ni celui des offres disponibles.

L'interface charge uniquement les lots de la source et de la période demandées. L'utilisateur peut choisir une année, toutes les années disponibles, ou préciser des dates de publication de début et de fin. Les lots couvrant une année entièrement extérieure à l'intervalle ne sont pas téléchargés ; les documents sont ensuite filtrés à la date exacte. Un intervalle inversé est refusé avant tout téléchargement. Elle affiche au plus 100 correspondances par recherche, tout en comptant l'ensemble des résultats identifiés dans les lots sélectionnés. Le traitement s'exécute dans le navigateur ; aucun serveur ou stockage persistant payant n'est ajouté.

La consultation vérifie la taille des lots, leur empreinte cryptographique SHA-256 avec l'interface native du navigateur et la cohérence du contenu avec le manifeste. Cette vérification est également répétée sur les archives réelles par les contrôles GitHub. Si le navigateur ne permet pas le contrôle d'empreinte, ou si un seul lot échoue, aucun résultat de la recherche demandée n'est affiché. Toute erreur de lecture interrompt la restitution pour éviter de présenter des résultats partiels comme complets.

## Contrôles

```sh
node --test tests/test_partitions_statiques.mjs
node scripts/construire_partitions_statiques.mjs
```

Le contrôle CI vérifie, sur les véritables archives, l'empreinte, le nombre de documents et la taille de chaque lot, ainsi que la présence de plus de 1 900 documents au total.

La segmentation territoriale exige des champs géographiques fiables des producteurs et reste à préparer séparément. Le filtre de période accepte les années et les intervalles de dates présents dans les archives ; aucune date absente n'est inventée. La sélection par territoire reste exclue en l'absence d'identifiants géographiques comparables entre sources.

## Bilan de sélection publié

Le manifeste `site_frontiere/partitions/manifeste.json` comprend désormais
`selection`, calculé pendant la construction à partir des documents effectivement
retenus et des lots produits. La page `recherche-etendue.html` permet de
consulter, pour BOAMP, emplois publics et DECP :

- le nombre de documents indexés et le plafond de 5 000 par source ;
- les années documentaires représentées et leur nombre de documents ;
- le nombre d'enregistrements parcourus dans les fichiers locaux ainsi que
  l'unité utilisée par chaque collecteur.

Les enregistrements d'origine ne sont pas directement comparables : annonces
BOAMP, variantes d'offres et notices contractuelles DECP. Le plafonnement
à 5 000 documents sélectionne un sous-ensemble récent et ne permet pas de
calculer les omissions uniques exactes ou un taux de couverture nationale.
La présence d'une année indique uniquement qu'au moins un document de cette
année figure dans l'extrait retenu.

Le bilan est déterministe à archives données. Ses totaux sont vérifiés contre
les lots du manifeste et les contrôles fonctionnels du site. Une version du
manifeste antérieure à ce changement reste consultable, avec la mention
explicite « bilan de sélection indisponible ».

Pour reproduire les vérifications :

```sh
node --test tests/test_partitions_statiques.mjs
node scripts/construire_partitions_statiques.mjs
```

La prochaine amélioration scientifique doit mesurer les documents admissibles
écartés par les plafonds, source par source, sur les archives complètes et les
identifiants distincts. Ce travail nécessitera des décomptes adaptés à chaque
producteur ; aucune inférence de couverture nationale n'en découlera à lui seul.
