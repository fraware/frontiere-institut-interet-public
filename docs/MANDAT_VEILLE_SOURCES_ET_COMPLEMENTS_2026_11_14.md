# FRONTIÈRE — Mandat public de veille et règles de mise à jour

**État documentaire :** 14 novembre 2026 (UTC). **Périmètre :** FRONTIÈRE / Horizon France.
Ce mandat formalise les contrôles attendus. Son dépôt ne démontre aucune exécution future, ingestion de données ni couverture exhaustive du Web. Le dépôt GitHub constitue le registre durable ; les observations ponctuelles conservent leur provenance et leurs limites.

## 1. Veille générale des sources officielles

Examiner les catalogues, jeux de données, API, flux et publications des administrations françaises et européennes, des organismes scientifiques, des laboratoires, des infrastructures de recherche, des organismes de recrutement, de la commande publique, des budgets et des politiques scientifiques.

Référentiels de comparaison :
- [Sources opérationnelles](../institutionnel/sources_v1.json) : sources de référence et collectes déclarées.
- [Catalogues officiels découverts](../institutionnel/decouverte/catalogues_officiels_v1.json) : découverte documentaire, indépendamment de l'ingestion.
- [Proposition de consolidation n° 685](https://github.com/fraware/frontiere-institut-interet-public/pull/685) : entrées complémentaires à examiner jusqu'à fusion.
- [Contrôle de veille et d'intégration](CONTROLE_VEILLE_ET_INTEGRATION_V1.md) : distinction des stades techniques.

Pour chaque candidat substantiel, enregistrer le producteur, l'URL primaire, la date constatée, la date de mise à jour publiée, la licence ou les restrictions, les formats, le point d'accès, les conditions d'authentification, les limites de volume et de fréquence, le périmètre, puis les identifiants et liens déjà présents dans les deux registres. Dédupliquer par producteur, objet, identifiants et URL normalisées ; préserver les divergences significatives entre deux versions.

États à distinguer explicitement : **source repérée**, **documentation officielle consultée**, **point d'accès vérifié**, **requête de métadonnées testée**, **contenu métier acquis**, **schéma et provenance validés**, **intégration en production vérifiée**. Chaque état supérieur appelle une preuve distincte (réponse conservée, exécution, empreinte, manifeste et/ou révision). Une annonce, une fiche ou une possibilité théorique d'accès ne justifie aucun état d'ingestion.

Alerter uniquement en présence d'une nouvelle source importante et dédupliquée, d'échecs récurrents attestés pour un même traitement ou d'une variation de couverture significative. Une simple date de mise à jour d'une source existante ne justifie pas une alerte. Ne jamais attribuer un téléchargement, une validation de licence ou une intégration à une vérification purement documentaire.

## 2. Revue directrice du lundi

Chaque lundi, consulter [la feuille de route](FEUILLE_DE_ROUTE_DIRECTRICE.md) et [son journal](SUIVI_FEUILLE_ROUTE.md), puis établir :
1. La révision exacte de `main`, les PR ouvertes, leurs dépendances, conflits et examens humains.
2. Les contrôles GitHub Actions obligatoires pour les commits concernés, leurs conclusions et les causes établies des échecs.
3. Les manifestes de données et rapports d'exécution consultables, leur fraîcheur et leurs limites de couverture.
4. L'état de déploiement Render **uniquement si l'espace de travail et le service ont été identifiés et consultés**, avec correspondance à un commit.
5. Les modifications d'état justifiées dans la feuille de route, le journal, les blocages et les **trois priorités suivantes**.

Faire passer toute modification publique par une branche et une PR traçable. « Terminé » suppose une preuve propre à l'étape. Aucune réécriture silencieuse des états, aucun coût nouveau. Fusionner exclusivement une PR documentaire sans conflit, après réussite de tous les contrôles obligatoires et vérifications requises. Une PR comportant du code, un workflow ou des données doit conserver son examen technique approprié. En l'absence de changement justifié, ne créer aucun commit artificiel.

## 3. Complément ponctuel — Alexandre Pointier

**Période : jusqu'au 16 novembre 2026 inclus.** L'article recherché est désormais **confirmé** : Alexandre Pointier, « La France a besoin d’une révolution bureaucratique. L’IA pourrait la rendre possible », *Le Grand Continent*, **3 novembre 2026** :
https://legrandcontinent.eu/fr/2026/11/03/la-france-a-besoin-dune-revolution-bureaucratique-lia-pourrait-la-rendre-possible/

Il s'agit d'une tribune publique, **pas d'une source officielle démontrant un déploiement gouvernemental**. Le signalement initial n'est à répéter ni lors des contrôles suivants ni au-delà du 16 novembre. Trois questions techniques pour FRONTIÈRE :
- Interfaces publiques ouvertes, interopérabilité et réversibilité des fournisseurs, avec responsabilités administratives explicites.
- Contrôle d'autorisation par finalité et cloisonnement des usages des données, notamment séparation entre accès au service et contrôle des personnes.
- Journalisation attribuable des consultations et actions automatisées, consultation par les personnes concernées et voies de contestation.

Ce sont des implications à étudier et à tester, sans attribution de mise en œuvre effective.

## 4. Complément PEPR Quantique — lundis jusqu'au 30 juin 2027 inclus

Suivre exclusivement les publications publiques du [PEPR Quantique](https://www.pepr-quantique.fr/), du [portail national quantique](https://quantique.france2030.gouv.fr/), du CNRS, du CEA, d'Inria et de Campus France concernant :
- AMI Nouvelle Génération 2026 : lauréats, montants effectivement attribués et premières réalisations documentées ;
- chaires Early-Stage Researchers : bénéficiaires, allocation, contributions et résultats documentés ;
- Raise Quantum Talents : cohortes, recrutements et installations établis.

Comparer au [registre PEPR daté du 2 novembre](../institutionnel/programmes_scientifiques/pepr_quantique_competences_sources_2026_11_02_v1.json) (intégré via [PR #666](https://github.com/fraware/frontiere-institut-interet-public/pull/666)). Une offre ne démontre aucune pénurie ; un financement ou une installation ne démontre aucun effet causal. Publier une alerte seulement pour une nouveauté officielle substantielle, avec date, lien, degré de preuve, inconnues et proposition d'intégration. Cesser ce complément après le 30 juin 2027, sans interrompre les autres suivis.

## 5. Complément science–action — lundis

Examiner les éléments publics de mise en œuvre effective des recommandations **5, 6, 8 et 10** de l'[IGEDD n° 016247-01](SUIVI_RECOMMANDATIONS_IGEDD_2026_11_04.md), les livrables et diagnostics publics EIPM 2.0 coordonnés en France par l'INRAE, ainsi que les dispositifs d'appui aux politiques publiques de l'INRAE, du BRGM et de l'Université Gustave Eiffel.

Comparer aux trois documents [qualification des besoins](QUALIFICATION_BESOINS_SCIENTIFIQUES_2026_11_04.md), [cartographie des interfaces](CARTOGRAPHIE_INTERFACES_SCIENCE_ACTION_2026_11_04.md), [suivi IGEDD](SUIVI_RECOMMANDATIONS_IGEDD_2026_11_04.md) et aux tickets [#672](https://github.com/fraware/frontiere-institut-interet-public/issues/672), [#673](https://github.com/fraware/frontiere-institut-interet-public/issues/673), [#674](https://github.com/fraware/frontiere-institut-interet-public/issues/674). En cas de nouveauté substantielle, exiger date, source primaire, conséquence empirique et action vérifiable. Une annonce, une orientation et une réalisation sont des stades distincts.

## 6. Complément observation associative — lundis jusqu'au 31 janvier 2027 inclus

Examiner les nouvelles publications officielles de l'enquête **Associations 2024** de l'Insee, de l'enquête **têtes de réseau 2026** (Mouvement associatif et Paris Dauphine–PSL), de **PARAD 2026** (INJEP), des **OLVA 2026–2027** (RNMA), de **Recherches & Solidarités**, de **NOURA/F3E**, ainsi que du document budgétaire « jaune » associations et de **Data.Subvention**.

Comparer au [protocole d'observation associative proposé par la PR #682](https://github.com/fraware/frontiere-institut-interet-public/pull/682), repris dans la proposition [#685](https://github.com/fraware/frontiere-institut-interet-public/pull/685). Réserver les alertes aux nouveautés substantielles avec date, lien primaire, implication méthodologique et limites de preuve. Terminer uniquement ce complément après le 31 janvier 2027.

## 7. Protection des informations et règles de publication

Seules les pièces déjà publiques et nécessaires à l'analyse entrent dans GitHub. Aucun verbatim, échange privé, transcription, renseignement confidentiel ou donnée nominative non publique d'entretien. Conserver le statut « non vérifié » des observations incomplètes. Chaque PR indique les fichiers affectés, les déduplications, les tests réellement exécutés, les exclusions, les conflits possibles et les informations restant à confirmer. Le silence est la sortie attendue d'une veille sans signal substantiel.
