# FRONTIÈRE — Réconciliation documentaire et contrôles observés le 14 novembre 2026

**Nature :** constat ponctuel, sans modification du code, des collecteurs ou des données métier. **Date :** 14 novembre 2026 (UTC). **Révision de `main` examinée :** [`b34cb3542385c6a759fe5fc56fdb640721f509e5`](https://github.com/fraware/frontiere-institut-interet-public/commit/b34cb3542385c6a759fe5fc56fdb640721f509e5).

## Couverture réellement présente et proposée

- [`institutionnel/sources_v1.json`](../institutionnel/sources_v1.json) : **15** sources de référence opérationnelles déclarées dans ce registre, sans revalidation d'exécution des collecteurs lors du présent audit.
- [`institutionnel/decouverte/catalogues_officiels_v1.json`](../institutionnel/decouverte/catalogues_officiels_v1.json) : **23** entrées documentaires sur `main`. Ce registre n'est pas un inventaire d'ingestions réussies.
- [PR #685](https://github.com/fraware/frontiere-institut-interet-public/pull/685), branche `veille/consolidation-sources-2026-11-12` : **81 identifiants documentaires**, dont **58 ajouts proposés**, accompagnés d'un index, d'un manifeste de déduplication et d'archives de découvertes. **PR ouverte, non intégrée**.
- [PR #682](https://github.com/fraware/frontiere-institut-interet-public/pull/682) : protocole d'observation associative non fusionné ; une copie est également proposée dans #685. Éviter de fusionner deux versions divergentes.
- [PR #666](https://github.com/fraware/frontiere-institut-interet-public/pull/666) : dossier PEPR Quantique fusionné, [registre présent sur `main`](../institutionnel/programmes_scientifiques/pepr_quantique_competences_sources_2026_11_02_v1.json).
- Les [documents science–action](SUIVI_RECOMMANDATIONS_IGEDD_2026_11_04.md) sont déjà sur `main` ; [#672](https://github.com/fraware/frontiere-institut-interet-public/issues/672), [#673](https://github.com/fraware/frontiere-institut-interet-public/issues/673) et [#674](https://github.com/fraware/frontiere-institut-interet-public/issues/674) demeurent ouverts.

Ces décomptes concernent des structures de registre distinctes. Ne pas additionner 15, 23 et 81 comme des producteurs uniques.

## Recontrôles documentaires des interfaces officielles

1. [Export national du catalogue data.gouv.fr](https://www.data.gouv.fr/datasets/catalogue-des-donnees-de-data-gouv-fr) : publication datée du **14 novembre 2026**, licence **Licence Ouverte 2.0**, exports CSV de jeux, ressources, services, producteurs et autres objets. Périodicité hebdomadaire annoncée. Source **déjà identifiée** sous `data_gouv_ensemble`. Aucun CSV volumineux téléchargé ni examiné ligne à ligne ici.
2. [Catalogue Recherche Data Gouv](https://recherche.data.gouv.fr/fr/page/catalogue-recherche-data-gouv) : documentation datée du **16 octobre 2026**, interface **MCP** décrite à `https://catalogue.recherche.data.gouv.fr/mcp`. La source de catalogue est **déjà identifiée** sous `recherche_data_gouv`. Aucune session MCP, aucun moissonnage et aucune lecture de contenu métier testés ici.

3. [Structures de recherche publiques actives (MESRE/RNSR)](https://www.data.gouv.fr/datasets/structures-de-recherche-publiques-actives-1) : fiche datée du **5 novembre 2026**, Licence Ouverte 2.0, sorties CSV, JSON, GeoJSON et ancien Shapefile. Jeu **déjà répertorié** via `rnsr_mesr` ; aucun fichier acquis dans cette revue. Les dates des exports et du Shapefile ne sont pas interchangeables.
4. [Explore API v2.1 du MESRE](https://data.enseignementsup-recherche.gouv.fr/api-console/explore/v2.1/) : service officiel ouvert de consultation REST `GET`, réponses JSON, catalogue interrogeable, exports CSV, Parquet et DCAT selon routes documentées ; [fiche de service sur data.gouv.fr](https://www.data.gouv.fr/dataservices/explore-api-v2-68). Accès transversal à des sources MESRE déjà couvertes. **Interface supplémentaire à rapprocher de leurs fiches, sans compter un nouveau producteur.** Licence de chaque jeu distincte de la documentation de l'API.
5. [EURIO — European Research Information Ontology](https://op.europa.eu/en/web/eu-vocabularies/eurio) : modèle officiel CORDIS de projets, acteurs et financements européens ; distribution **Turtle (`.ttl`)** et [notice européenne de réutilisation CC BY 4.0](https://interoperable-europe.ec.europa.eu/collection/eu-semantic-interoperability-catalogue/solution/eurio). À rapprocher des entrées `cordis_projets_recherche` et `eu_vocabularies_portail_reference` de #685 ; utilité sémantique potentielle, **ni nouveau flux métier ni ingestion démontrés**.
6. [Transition INSPIRE vers data.europa.eu](https://data.europa.eu/en/news-events/news/inspire-datasets-move-european-data-portal) : annonce officielle du **22 juin 2026**, bascule annoncée le **1er juillet 2026**, remplacement du géoportail de recherche par data.europa.eu et transfert du registre de terminologies vers EU Vocabularies. Évolution d'accès à qualifier dans les entrées `eu_data_europa_federated_catalogue` et `eu_vocabularies_portail_reference` de #685 ; **ne pas compter deux nouveaux catalogues** et ne pas inférer la réussite des migrations à partir de l'annonce.

La mise à jour d'une source existante et l'apparition d'un mode d'accès documenté ne constituent pas deux producteurs nouveaux. Les licences propres aux jeux scientifiques et les droits de redistribution ne sont pas déduits de l'accès libre à leur catalogue. Le présent contrôle ne prétend pas vérifier tous les 81 liens ni l'exhaustivité de la recherche.

## Article public nouvellement confirmé

Alexandre Pointier, [« La France a besoin d’une révolution bureaucratique. L’IA pourrait la rendre possible »](https://legrandcontinent.eu/fr/2026/11/03/la-france-a-besoin-dune-revolution-bureaucratique-lia-pourrait-la-rendre-possible/), *Le Grand Continent*, **3 novembre 2026**. Publication directement constatée le 14 novembre. Ce texte défend une proposition de gouvernement agentique ; il ne constitue pas une annonce officielle de déploiement. Implications techniques à soumettre à analyse : interopérabilité et réversibilité des interfaces ; politique d'autorisation par finalité, sans réemploi transversal implicite ; journalisation attribuable et consultation des accès par les personnes concernées. **Signal ponctuel confirmé une fois ; pas d'alerte récurrente.**

## Vérifications GitHub réellement observées

- [PR #685 — exécution 43262189427](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/43262189427) : échecs des jobs Python 3.11, Python 3.12 et Chromium ; quatre autres jobs réussis. **Ne pas fusionner** cette PR dans cet état.
- [PR #686 — exécution 43262645623](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/43262645623) : **sept jobs réussis** ; correctif encore **ouvert**, comportant des fichiers techniques et des tests. Sa réussite ne valide pas automatiquement #685.
- Plusieurs procédures automatisées de `main` ont terminé en échec le 14 novembre : [publication des métadonnées des catalogues](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/43628136198), [publication des signaux et flux](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/43632226373), [publication des canaux officiels](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/43632232884), [publication de la sonde AIFE](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/43634949834). Les étapes signalées en échec sont des **étapes de publication** : leurs causes précises et l'état réel des acquisitions en amont restent à examiner. Ne pas en inférer une panne de collecte métier.
- La branche `main` était signalée comme **non protégée** par la réponse GitHub consultée. Ne présumer aucune politique effective de contrôle des fusions.
- **Render non vérifié** : aucun espace de travail sélectionné dans la connexion disponible ; aucun service, déploiement ou commit publié n'a pu être contrôlé. Cette absence de vérification n'est pas une panne établie.

## État de la feuille de route et trois priorités

Aucun statut `Terminé` attribué ; aucune modification des étapes F-001 à F-091. Aucun manifeste reconstruit et aucune donnée métier téléchargée. Aucune dépense engagée.

1. **Faire examiner techniquement #686** et confirmer son intégration après revue humaine, sans contourner les règles de fusion.
2. **Réévaluer #685 sur une base actualisée**, relancer ses contrôles obligatoires et résoudre le chevauchement documentaire avec #682 avant toute fusion.
3. **Diagnostiquer les échecs des étapes de publication**, comparer les manifestes aux exécutions et examiner le déploiement Render une fois le bon espace de travail explicitement identifié.

L'existence de cette note sur une branche ne démontre ni son intégration sur `main` ni la résolution des blocages qu'elle décrit.
