# FRONTIÈRE — Premier état transversal « archives → index → publication »

**Date du constat :** 16 octobre 2026 (UTC). **Révision source interrogée :** [`bc44675b4b30298d9337dda92699c0a4c47bcba2`](https://github.com/fraware/frontiere-institut-interet-public/commit/bc44675b4b30298d9337dda92699c0a4c47bcba2). **Statut :** premier relevé de lecture des manifestes et des vérifications distantes, **non** reproduction locale indépendante de tous les corpus.

Ce relevé lance les travaux [F-001 à F-010](FEUILLE_DE_ROUTE_DIRECTRICE.md). Il distingue l'information déclarée par les fichiers, les contrôles GitHub réellement réussis, l'état observé sur Render et les vérifications encore nécessaires. Aucun besoin institutionnel n'est inféré des volumes.

## 1. Corpus et unités observés

| Source | Référentiel interrogé | Unité et effectif déclarés | Date du dernier état source affiché | Qualification |
| --- | --- | --- | --- | --- |
| BOAMP | `institutionnel/besoins_publics/etat_boamp.json` | **5 196 avis distincts conservés** | Contrôle le 15/10/2026 à 23:44:11 UTC | Réunion cumulative de relevés ; non exhaustif nationalement |
| Recrutements CSP | `institutionnel/besoins_publics/manifest_offres_postes.json` | **268 102 variantes**, **266 139 références distinctes** | Extraction le 12/10/2026 à 11:09:28 UTC | Variantes documentaires, ni postes ouverts ni emplois vacants |
| DECP | `institutionnel/decp/bilan_index_unifie.json` | **5 946 observations**, **5 643 identités de marchés**, **5 665 variantes** | Bilan construit le 14/10/2026 à 22:38:41 UTC | 47 fichiers documentaires ; ni contrats exécutés ni besoins ouverts démontrés |

Les dates désignent des opérations différentes (contrôle de relevé, extraction d'une ressource et calcul d'un index). Elles ne sont pas directement comparables comme dates de publication des documents chez les producteurs.

**Constats de lecture des manifestes.** Le relevé BOAMP déclare une recherche non partielle sur sa fenêtre courante, avec 3 190 enregistrements lus lors du dernier cycle et aucun échec de page rapporté. Cela ne démontre pas une couverture historique complète du BOAMP. Le manifeste CSP indique 16 partitions, 1 168 références à variantes multiples, 3 782 cellules tronquées et `couverture_integrale_du_csv=false`. Le bilan DECP distingue 5 946 attestations de 5 665 variantes et indique explicitement zéro besoin encore ouvert démontré.

## 2. Recherche disponible et périmètre public

**Moteurs intégraux locaux déjà intégrés :**

- [Contribution n° 534](https://github.com/fraware/frontiere-institut-interet-public/pull/534) : index CSP SQLite FTS5, couvrant les 268 102 variantes archivées. [Vérification de la branche principale](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38830382413) et [production de l'archive temporaire](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38830382254) annoncées réussies.
- [Contribution n° 535](https://github.com/fraware/frontiere-institut-interet-public/pull/535) : recherche locale commune BOAMP–DECP sans rapprochement contractuel inventé. [Vérification sur main](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38839185199) et [archive temporaire du moteur](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38839185264) réussies.

**Site statique :** les générateurs `scripts/construire_index_statique.mjs` et `scripts/construire_partitions_statiques.mjs` imposent respectivement un index principal plafonné à **700 avis BOAMP, 700 variantes CSP et 500 notices DECP**, et des partitions étendues plafonnées à **5 000 documents par source**. Ces limites codées ne constituent pas le nombre effectivement publié : les nombres exacts dépendent de la sélection, des dates admissibles et du déploiement. Le manifeste de partition comporte les nombres retenus, les années et les empreintes SHA-256.

**Render vérifié directement :** le service statique `frontiere-observatoire-public` affiche un déploiement `live` sur la révision [`2d48f7012fe36f78456acc79b7085dc991a833ab`](https://github.com/fraware/frontiere-institut-interet-public/commit/2d48f7012fe36f78456acc79b7085dc991a833ab), terminé le **15/10/2026 à 23:32:00 UTC**. Cette version précède le commit de référence `bc44675b`. Les déploiements automatiques du service sont désactivés. Ni les deux bases SQLite intégrales ni le dernier registre de rapprochements ne sont ainsi attestés comme consultables sur le site public ; ils restent accessibles via les outils locaux et leurs archives de procédure selon les conditions documentées.

## 3. Contrôles distants observés

À la révision `bc44675b` :

| Procédure | Résultat observé | Preuve |
| --- | --- | --- |
| Vérifications générales | Terminée, réussite | [Exécution 38839185199](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38839185199) |
| Base BOAMP et DECP intégrale | Terminée, réussite | [Exécution 38839185264](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38839185264) |
| Contrôle transversal de la veille | Terminée, réussite | [Exécution 38850591268](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38850591268) |

Un résultat réussi atteste l'exécution de la procédure définie dans le dépôt. Il ne démontre pas une couverture nationale complète, une disponibilité permanente, ni une validation humaine des besoins.

## 4. File actuelle des travaux concurrents

Huit propositions étaient ouvertes lors du relevé : [n° 530](https://github.com/fraware/frontiere-institut-interet-public/pull/530) (AIFE), [n° 494](https://github.com/fraware/frontiere-institut-interet-public/pull/494) (veille), [n° 487](https://github.com/fraware/frontiere-institut-interet-public/pull/487) (DMTG), [n° 485](https://github.com/fraware/frontiere-institut-interet-public/pull/485) (référentiel), [n° 484](https://github.com/fraware/frontiere-institut-interet-public/pull/484) (sources), [n° 449](https://github.com/fraware/frontiere-institut-interet-public/pull/449) (DGFiP XML), [n° 407](https://github.com/fraware/frontiere-institut-interet-public/pull/407) (délibérations) et [n° 401](https://github.com/fraware/frontiere-institut-interet-public/pull/401) (catalogues). Leur ouverture ne préjuge pas de leur aptitude à être fusionnées ; elles doivent être examinées sur la révision actuelle.

## 5. Vérifications encore ouvertes

1. **Reconstruction indépendante :** exécuter les commandes des deux moteurs depuis un environnement propre, conserver les bilans et comparer les empreintes des sorties.
2. **Consultation réellement publiée :** récupérer les manifestes du site live, leurs SHA-256 et leurs compteurs ; les comparer aux fichiers construits localement à la révision déployée.
3. **Chaîne de dates :** rapprocher date producteur, date d'importation, date du dernier succès des procédures et date de mise en ligne, sans les confondre.
4. **Procédures ouvertes :** réconcilier les huit propositions de source en tenant compte des nouveaux instantanés et conflits éventuels.
5. **Sécurité :** inspecter les chemins de publication, la nature des champs indexés et les autorisations des procédures avant diffusion accrue.
6. **Coût :** confirmer l'absence de nouvelle dépense récurrente ; ne déclencher aucun changement de forfait.

### Commandes de reproduction, à exécuter

```sh
python -m scripts.indexer_recrutements_nationaux_sqlite construire --base /tmp/frontiere-csp.sqlite3
python -m scripts.indexer_recrutements_nationaux_sqlite bilan --base /tmp/frontiere-csp.sqlite3
python -m scripts.indexer_commande_publique_sqlite construire --base /tmp/frontiere-commande.sqlite3
python -m scripts.indexer_commande_publique_sqlite bilan --base /tmp/frontiere-commande.sqlite3
node scripts/construire_index_statique.mjs
node scripts/construire_partitions_statiques.mjs
```

**Limite explicite de ce relevé :** les fichiers du dépôt et les états GitHub/Render ont été examinés à distance, mais aucune reconstruction intégrale indépendante des corpus n'a été exécutée ici. Les six vérifications ouvertes ci-dessus demeurent donc des travaux actifs.

**Décision de suite :** ne pas dupliquer les extracteurs existants. Achever l'audit « archives → index → site » et confronter les trois dénominateurs documentaires à la consultation réellement possible avant d'étendre les relations institutionnelles.
