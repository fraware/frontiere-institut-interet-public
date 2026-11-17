# FRONTIÈRE — Auditer les infrastructures existantes d'intermédiation avant d'en créer une autre

**Recherche publique arrêtée au 7 novembre 2026.** Complément à l'[évaluation critique de la Mission adaptation](EVALUATION_CRITIQUE_MISSION_ADAPTATION_INGENIERIE_2026_11_07.md) et aux [cas territoriaux](MISSION_ADAPTATION_ET_CAS_TERRITORIAUX_CONTROLES_2026_11_07.md). Périmètre documentaire ouvert uniquement ; aucun entretien, contenu privé, consultation de dossiers des collectivités ou prise de contact n'est intégré. Un résultat produit par une équipe sur son propre outil demeure une **déclaration institutionnelle**, non une mesure indépendante d'effet causal.

## 1. Le fait institutionnel nouveau : Mission adaptation repose déjà sur un logiciel public mutualisé

**Recommandations-collaboratives (Reco-co)** est développé par le Cerema avec l'écosystème beta.gouv.fr / DINUM. Il fournit aux services publics une application multi-portails : création d'un dossier, qualification des besoins, conversations entre agents de plusieurs administrations, émission de recommandations, référencement de ressources et suivi de l'avancement des projets au fil du temps. La fiche officielle mentionne des projets pouvant durer de **un à dix ans**, ce qui explique l'importance de l'historisation des décisions et des changements d'interlocuteurs.

Le service est utilisé notamment par **UrbanVitaliz, SOS Ponts, ÉcoQuartiers, Mission adaptation, Mon Espace Collectivité**, un dispositif de conseil au sein de l'**Alliance Sorbonne Université**, et des portails thématiques spécialisés. Cette généralité intersectorielle est déterminante : il serait inexact de présenter une simple plateforme d'aiguillage multi-expertise comme une fonction absente de l'administration française.

Le dépôt public **[betagouv/recommandations-collaboratives](https://github.com/betagouv/recommandations-collaboratives)** a été vérifié directement dans GitHub le 7 novembre 2026. Branche principale **develop**, code **Python/Django** et interface **Alpine.js / Bootstrap / DSFR**, architecture **multi-portails**, licence **GNU AGPL-3.0** dans le README et fichier LICENSE. Il existe donc une base publique, développée activement, à auditer avant toute duplication technique. **Nous n'avons ni installé, ni audité statiquement l'intégralité du code, ni validé sa sécurité ou son adéquation à des données confidentielles.** Les obligations de licence et d'hébergement sont à examiner avant tout réemploi.

Sources : [Reco-co, fiche beta.gouv.fr](https://beta.gouv.fr/startups/recommandations-collaboratives.html) ; [architecture du portail Mission adaptation](https://recommandations-collaboratives.beta.gouv.fr/cas-dusage/mission-adaptation/) ; [README et licence GitHub](https://github.com/betagouv/recommandations-collaboratives) ; [présentation croisée Reco-co / Expertises-Territoires du 8 octobre 2026](https://recommandations-collaboratives.beta.gouv.fr/actualites/d%C3%A9mo-recommandations-collaboratives-expertises-territoires/).

## 2. Les dénominateurs publics : un nouveau jeu de mesures documenté

La [page officielle de statistiques de Reco-co](https://recommandations-collaboratives.beta.gouv.fr/stats-impact/) affiche les valeurs **« données de décembre 2025 »**. Son modèle d'impact défini par l'équipe privilégie la mise en relation, puis le passage à l'action sur des recommandations.

| Périmètre | Valeurs publiées avec leur statut | Interprétation admissible |
| --- | --- | --- |
| Ensemble Reco-co, décembre 2025 | **12 portails ; 2 700 projets ; 1 400 conseillers ; 6 120 recommandations** | Activité technique déclarée sur l'ensemble des usages, pas impact causal |
| Mission adaptation, dans le même tableau | **162 dossiers ; 220 conseillers** | Dossiers et conseillers de portail ; pas « 162 collectivités distinctes accompagnées » |
| UrbanVitaliz | **610 projets** et **77 %** de collectivités utilisatrices déclarées passées à l'action ; **673 conseillers locaux** | Résultat d'usage déclaré par l'équipe, périmètre et enquête à contrôler |
| SOS Ponts | **660 questions depuis décembre 2022**, **70 %** de passage à l'action déclarés et **2 177 recommandations** | Questions ≠ projets ≠ collectivités ; effet du conseil à corroborer |
| Bilan PNACC-3 / Cerema sur 2025 | **184 collectivités** / **200 territoires** | Définitions et dates de mesure divergentes ; à réconcilier dans une table de correspondance |

Les **162 dossiers du portail en décembre 2025** constituent un nouvel indicateur, mais ne réconcilient pas les **184 collectivités** du bilan PNACC-3 et les **200 territoires** du Cerema : une même collectivité peut ouvrir plusieurs dossiers, certaines collectivités bénéficient d'actions hors portail, et les dates peuvent différer. Ces explications sont **hypothèses**, pas constats démontrés. Aucun ratio 162/184, 184/200, 77/70 ne doit être utilisé comme taux de traitement ou effet comparatif.

**Audit minimum du tableau 2025** : date exacte de photographie, identifiant pseudonymisé du dossier, nombre de collectivités distinctes, voie d'entrée, stade, délai, catégorie de conseil, clôture, abandon, réception par l'opérateur, mise en œuvre citée, dédoublonnage et dénominateurs d'enquête. Pas besoin d'informations nominatives dans le registre de recherche.

## 3. De la coordination humaine à l'IA : SofIA et Booster Conseil existent déjà

La **feuille de route ministérielle Numérique et IA de septembre 2025** décrit **SofIA**, un agent conversationnel conçu par l'ADEME, le Cerema et le **CGDD/Ecolab** pour interroger leurs corpus documentaires de référence. Elle rapporte **plus de 14 400 requêtes enregistrées au 30 avril 2025**, détaille une gouvernance multipartite et identifie comme défis la standardisation des documents, l'intégration de nouveaux corpus, l'industrialisation et la modularité de l'outil. Ce chiffre est un **volume de requêtes**, ni un nombre d'utilisateurs uniques, ni une évaluation de validité des réponses, ni un gain de productivité établi.

Le code de l'expérimentation SofIA est publiquement référencé par **[l'ADEME sur GitLab](https://git.ademe.fr/open-source/sofia/sofia-app)**. Cette présence ne prouve ni fonctionnement actuel, ni audit de cybersécurité, ni autorisation de réutiliser des corpus internes. La documentation publique rappelle que les réponses d'un modèle génératif peuvent être erronées et que l'usage de l'outil est réservé aux établissements partenaires dans la version décrite.

**Booster Conseil**, fiche beta.gouv.fr, réutilise SofIA comme base pour assister **les référents humains de la Mission adaptation**. Une expérimentation allant de **juillet à décembre 2025** est déclarée par l'équipe comme facilitant et accélérant les réponses. La fiche ne publie toutefois pas les effectifs de l'étude, le protocole d'affectation, les temps avant/après harmonisés, la qualité vérifiée des recommandations, le coût de calcul ni les résultats négatifs. La phase **janvier–avril 2026** vise les formats et l'accès aux retours d'expérience. **Ne pas convertir cette autoévaluation qualitative en preuve de performance causale ou de conformité.**

Sources : [feuille de route Numérique et IA, septembre 2025, fiche SofIA p. 30](https://www.ecologie.gouv.fr/sites/default/files/documents/fdr_numerique_ia_092025.pdf) ; [Booster Conseil](https://beta.gouv.fr/startups/adaptation-au-changement-climatique-acc.html) ; [SofIA, GitLab ADEME](https://git.ademe.fr/open-source/sofia/sofia-app).

### Protocole pour évaluer une assistance scientifique automatisée

**Conditions de confiance** : provenance et version des sources, citations réellement reliées aux passages, politique de confidentialité et d'hébergement, droit d'accès des agents, distinction entre information scientifique et décision administrative, journal d'erreurs, correction humaine et voie de recours. Un taux de rapidité sans évaluation aveugle de la correction et de la complétude des réponses serait un résultat incomplet.

Comparer les tâches de conseil humain **sans outil** et **avec outil**, en tenant constants l'échéance, le domaine, le niveau de complexité, la formation et le corpus. Faire relire les réponses par des spécialistes indépendants des développeurs, contrôler les tâches contaminées par des exemples d'entraînement et ne pas utiliser des données administratives sensibles hors de l'environnement autorisé.

## 4. Un premier bilan régional a été publiquement présenté, sans disponibilité du jeu de données

Le [compte rendu de la COP Provence-Alpes-Côte d'Azur](https://infolettre.developpement-durable.gouv.fr/cop-regionale-provence-alpes-cote-d-azur/annee-2025/lettre-d-information-cop-regionale-provence-alpes/rubrique1287.html) indique que **Cerema et Ademe ont présenté un bilan de la première année de la Mission adaptation lors du comité stratégique du 2 décembre 2025**. Un autre [programme du ministère au Salon des maires 2025](https://www.ecologie.gouv.fr/rendez-vous/salon-maires-collectivites-locales-rendez-vous-village-territoires-ecologie/conferences) annonce un bilan et des retours de communes bénéficiaires en novembre 2025.

**Ce qui est prouvé** : existence de restitutions publiques ou institutionnelles. **Ce qui reste inconnu** : tableaux complets, mécanisme de décompte, résultats par stade, taux de non-réponse, effectifs réellement disponibles, transmission formelle du bilan prévu par la mesure 25 à la DGEC et au CGDD. Il serait incorrect de conclure à l'absence de bilan au seul motif qu'aucun PDF intégral n'a été identifié dans les résultats de recherche.

**Demande documentaire prioritaire** : diaporama Cerema–Ademe du 2 décembre 2025, compte rendu technique, tableau des indicateurs par région et sa version diffusée à DGEC/CGDD, métadonnées de date et définitions. Une version agrégée suffit pour le premier contrôle scientifique.

## 5. SIGERLy, FNCCR et démonstration technique : un progrès documentaire à dater

La **FNCCR**, dans son bilan de la [demi-journée du 9 avril et du webinaire SIGERLy du 28 avril 2026](https://www.fnccr.asso.fr/actualites/demi-journee-detudes-eclairage-public-reemploi-jeudi-9-avril-2026-2/), renvoie vers [un support du 28 avril](https://www.fnccr.asso.fr/wp-content/uploads/2026/04/presentation_reemploi_.pdf) qui présente la chaîne de valeur, cinq groupes de travail sur la normalisation, la responsabilité, l'économie, l'assurantiel et les données, ainsi qu'une URL de **démonstration d'un outil d'intermédiation**.

Une [interview de la direction du SIGERLy en mai 2026](https://www.clesdelatransition.org/acteurs-des-territoires/eclairage-public-la-region-lyonnaise-structure-une-filiere-de-reemploi) confirme publiquement une organisation en consortium avec le Cerema et la recherche de sites pilotes. Une [fiche de candidature MATEUS au Salon des maires 2026](https://www.salondesmaires.com/fiches-projets-produits/a47b2166-6dd4-f111-b8f7-005056a8e1f2/) déclare **quatre opérations de terrain testées** et une phase de réplication nationale. La date de publication de cette fiche et les résultats indépendants des essais n'ont pas été validés ; il faut la traiter comme **déclaration du porteur de projet sur une page de candidature**, et non comme rapport de réception certifié.

**Enjeu de preuve** : déterminer si la démonstration présentée au webinaire est la même version que le prototype du marché SIGERLy–Cerema, obtenir les identifiants et dates des essais, le registre d'acceptation technique, les procès-verbaux de réception, les indicateurs de réemploi et le coût complet. Une URL de démonstration ne prouve ni la signature de la convention, ni la conformité contractuelle, ni le nombre de matériels réellement réemployés.

## 6. Programme de collecte et critères de décision

| Priorité | Document à demander ou contrôler | Organisme / source | Décision conditionnée |
| --- | --- | --- | --- |
| priorité 0 | Bilan régional PACA du 2 décembre 2025, tableaux et compte rendu | Cerema–Ademe / COP régionale / DGEC–CGDD | Déterminer ce qui est déjà mesuré |
| priorité 0 | Export **agrégé** et daté des stades du portail Mission adaptation | Équipe Reco-co et référents publics | Réconcilier 162 dossiers / 184 collectivités / 200 territoires |
| priorité 0 | Définitions exactes des taux de passage à l'action et questionnaires | Équipe UrbanVitaliz / SOS Ponts | Vérifier la mesure d'impact avant imitation |
| priorité 0 | Protocole et mesures anonymisées de Booster Conseil | Accélérema / Cerema / Ademe | Tester l'effet du conseil augmenté par IA |
| priorité 0 | Signature, réception et résultats de SIGERLy–Cerema | SIGERLy / Cerema | Dépasser la preuve de démonstration |
| priorité 1 | Documentation des coûts et statuts du réemploi MATEUS | SIGERLy et consortium / FNCCR | Vérifier une généralisation déclarée |
| priorité 1 | Convention et livrables du marché Périgord–Limousin | Acheteur public / titulaire si attribué | Vérifier prestation et éventuel usage |
| priorité 1 | Cartographie des autres portails fondés sur Reco-co | Équipe produit / dépôt open source | Éviter de créer une fonction déjà mutualisée |

**Règle de décision** : ne pas construire de nouveau portail public ou un agent de conseil générique avant d'avoir examiné les outils Reco-co, SofIA et Booster Conseil, leurs conditions de réemploi, leurs garanties et leurs limites. Une fonction indépendante pourrait avoir sa place **uniquement sur un besoin résiduel défini** : recherche de capacités rares non couvertes, financement ciblé, traduction de demandes complexes hors périmètre actuel, ou évaluation indépendante des résultats ; aucun de ces déficits n'est encore quantifié.

**Plan comparatif prospectif** : définir avant observation l'unité « besoin administratif daté » et les résultats « qualification complète », « première réponse recevable », « usage dans décision », « coût complet », « équité territoriale ». Conserver en parallèle quatre options : fonctionnement courant, amélioration de Reco-co/coordination, capacité interne financée, appui extérieur limité. Mesurer les refus, abandons et parcours négatifs. Ne jamais inférer une valeur ajoutée à partir de taux d'usage auto-déclarés ou de simples volumes de requêtes.

**Confidentialité** : aucune donnée issue de réunions privées, de conversations enregistrées, de dossiers de collectivités non publics ou de correspondances personnelles n'est incluse dans cette note publique.
