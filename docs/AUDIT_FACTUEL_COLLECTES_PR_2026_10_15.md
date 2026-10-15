# FRONTIÈRE — Examen des relevés et contributions ouvertes du 15 octobre 2026

**Périmètre :** BOAMP, emplois publics, DECP. **TED retiré.** Cet examen porte sur les fichiers et différences constatés dans GitHub. Il ne constitue pas une nouvelle collecte externe ni une validation des sources officielles en direct.

## 1. État effectivement enregistré dans les manifestes

| Corpus | Fait vérifiable dans le dépôt | Dernier horodatage du bilan | Limite explicite |
|---|---|---|---|
| BOAMP | 5 127 annonces distinctes conservées ; dernier contrôle de 3 121 enregistrements valides, 32 pages réussies et 0 page échouée | 2026-10-15 14:15:29 UTC | `couverture_exhaustive_du_boamp=false` : aucune affirmation d'exhaustivité |
| Emplois publics | 268 102 variantes extraites, 266 139 références distinctes | 2026-10-12 11:09:28 UTC | `couverture_integrale_du_csv=false` : extraction partielle du fichier producteur |
| DECP | 47 fichiers documentaires, 5 643 identités acheteur–marché et 5 665 variantes documentaires | 2026-10-14 22:38:41 UTC | `deux_releves_publics_complets_sans_couverture_nationale` |

**Sources conservées :** `institutionnel/besoins_publics/etat_boamp.json`, `institutionnel/besoins_publics/manifest_offres_postes.json`, `institutionnel/decp/bilan_index_unifie.json`.

Le fait qu'un contrôle BOAMP enregistre zéro erreur de page ne démontre aucune couverture nationale exhaustive. Les 268 102 variantes d'emplois ne désignent pas 268 102 emplois actuellement ouverts. Les 5 643 identités DECP sont les marchés distincts de l'index existant, pas toutes les attributions françaises.

## 2. Revue réelle des fichiers modifiés par les PR anciennes

Ces éléments proviennent des différences de fichiers GitHub observées lors de la revue. Les chiffres ci-dessous sont des **lignes modifiées dans les demandes de fusion**, pas des annonces ou des contrats ajoutés.

| PR | Observations du contenu du changement | Risque principal | Décision |
|---|---|---|---|
| [#448](https://github.com/fraware/frontiere-institut-interet-public/pull/448) | Un fichier, `institutionnel/decp/etat_ressources.json`, huit lignes modifiées ; modifications observées des dates de contrôle | Mise à jour d'une date sans enrichissement démontré du catalogue | Ne pas fusionner pour augmenter la couverture annoncée |
| [#449](https://github.com/fraware/frontiere-institut-interet-public/pull/449) | Un fichier, `institutionnel/decp/lot_dgfip_xml.json`, 9 266 lignes modifiées | Lot substantiel exigeant contrôle des empreintes, tailles, notices et éventuels doublons | Revue des pièces brutes obligatoire avant fusion |
| [#484](https://github.com/fraware/frontiere-institut-interet-public/pull/484) | `institutionnel/alertes_sources.json` et `institutionnel/etat_sources.json` | Les changements de signatures ne prouvent pas automatiquement un changement sémantique des sources | Recouper les URLs officielles et les empreintes |
| [#485](https://github.com/fraware/frontiere-institut-interet-public/pull/485) | Référentiel, documentation, anomalie et nombreuses partitions `annuaire_local_*.jsonl` | Réorganisation d'institutions, disparition d'entrées, coordonnées publiques et éventuelles données personnelles | Vérification des écarts d'identité et de confidentialité avant toute publication |
| [#487](https://github.com/fraware/frontiere-institut-interet-public/pull/487) | Un état `etat_veille_dmtg_v1.json`, 33 lignes ajoutées | Confusion entre actualisation de signature et nouvelle publication scientifique | Vérifier la nature exacte du changement |
| [#494](https://github.com/fraware/frontiere-institut-interet-public/pull/494) | Un fichier de propositions de découverte, 53 lignes ajoutées | Présenter une proposition comme une source collectée | Conserver le statut « découverte » |
| [#407](https://github.com/fraware/frontiere-institut-interet-public/pull/407) | Quatre fichiers, documentation, qualification JSON et tests | Présenter les délibérations candidates comme des usages attestés | Conserver le statut « qualification » en l'absence de preuve d'usage |
| [#401](https://github.com/fraware/frontiere-institut-interet-public/pull/401) | Huit fichiers de propositions officielles, 155 lignes ajoutées | Catalogue de découverte confondu avec une ingestion | Conserver au stade de prospection documentaire |

La revue des différences de fichiers n'atteste pas leur validité scientifique. La **PR #449** est prioritaire pour un audit de données complet. Un volume important de lignes modifiées ne prouve pas que de nouveaux marchés distincts ont été acquis.

## 3. Conduite à tenir

Pour chaque contribution DECP, l'ordre de vérification est le suivant : comparer le fichier observé à l'URL officielle et à la ressource identifiée ; contrôler les tailles et empreintes ; confirmer le nombre de notices valides, rejetées et dupliquées ; reconstruire les décomptes d'identités et de versions ; vérifier l'absence de régression par rapport à `main` ; puis exécuter les contrôles complets GitHub.

Les contributions de référentiel doivent en outre conserver les identifiants stables des institutions, documenter les suppressions ou changements de hiérarchie et protéger les coordonnées de personnes physiques.

Aucune des huit PR précédentes n'a été fusionnée dans le cadre de cet examen. Le registre original de tri préalable figure dans `docs/AUDIT_PR_OUVERTES_2026_10_15.md`.

## 4. Séparer exploitation et couverture documentaire

Un service Render marqué `live` prouve que la plateforme statique a été déployée ; cela ne prouve pas qu'un collecteur a tourné. Un contrôle GitHub vert atteste la réussite d'une procédure définie ; cela ne démontre pas que tous les producteurs ont répondu. L'index statique consultable expose un échantillon borné : 1 900 notices initiales et 15 000 documents répartis en 26 fichiers sur le jeu étendu constaté le 15 octobre.

Les prochaines décisions d'élargissement dépendent de cette séparation entre **archives disponibles, extraction valide, consultation publique et couverture du phénomène national**.
