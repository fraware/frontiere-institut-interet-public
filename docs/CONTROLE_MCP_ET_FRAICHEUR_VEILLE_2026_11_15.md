# FRONTIÈRE — Interface scientifique et état des collectes au 15 novembre 2026

**Nature :** audit documentaire ciblé et analyse des journaux publics d'exécution. **UTC :** 15 novembre 2026. **Révision de référence de `main` :** [`b34cb3542385c6a759fe5fc56fdb640721f509e5`](https://github.com/fraware/frontiere-institut-interet-public/commit/b34cb3542385c6a759fe5fc56fdb640721f509e5).

Ce document établit ce qui a été consulté. Aucun fichier métier n'a été téléchargé dans cette revue ; aucun processus de récupération ni aucune ingestion supplémentaire ne sont déclarés réussis.

## 1. Recherche Data Gouv : qualification de l'interface MCP

| Propriété | Constat et source primaire |
| --- | --- |
| Producteur et rôle | Recherche Data Gouv, plateforme opérée par l'INRAE ; le catalogue signale des métadonnées de jeux présents dans des entrepôts de recherche extérieurs ou fédérés, sans héberger lui-même leurs fichiers ([conditions générales, actualisées le 4 novembre](https://recherche.data.gouv.fr/fr/page/conditions-generales-d-utilisation-de-la-plateforme-de-recherche-data-gouv)). |
| Interface déclarée | `https://catalogue.recherche.data.gouv.fr/mcp`, présentée par la [documentation officielle, datée du 16 octobre](https://recherche.data.gouv.fr/fr/page/catalogue-recherche-data-gouv). Accès direct annoncé pour les assistants utilisant le protocole MCP. |
| Guide d'accès | Recherche sémantique, recherche par mot-clé et filtres ; [guide officiel, mis à jour le 4 septembre 2026 (date vérifiée sur la page le 16 novembre)](https://recherche.data.gouv.fr/fr/page/guide-d-utilisation-du-catalogue-recherche-data-gouv). |
| Formats de sortie documentés | Les exports de références du catalogue sont **BibTeX**, **RIS**, **EndNote XML**. Ce constat ne spécifie aucun schéma de réponse ni aucun outil du serveur MCP. |
| Périmètre | Catalogue de métadonnées indexées à partir d'entrepôts sources ; leurs listes sont évolutives, des règles de sélection spécifiques s'appliquent. Les champs affiliation harmonisée, discipline et pays peuvent provenir d'enrichissements automatiques. Préserver les affiliations brutes et les identifiants d'origine pour les rapprochements. |
| Droits | Les [conditions générales du 4 novembre](https://recherche.data.gouv.fr/fr/page/conditions-generales-d-utilisation-de-la-plateforme-de-recherche-data-gouv) renvoient aux licences et conditions des entrepôts sources pour la réutilisation des données. **Aucune licence globale de redistribution des fichiers scientifiques n'est déduite de l'accès au catalogue.** |
| Authentification, quota, pagination MCP | **Non vérifiés** sur le serveur MCP. La documentation consultée ne suffit pas à fixer les outils exposés, leur schéma, les limites, les codes d'erreur ou les garanties de service. |
| Essai technique | L'ouverture directe de l'URL MCP via l'outil de consultation a échoué ; le conteneur de vérification n'a pas résolu son nom DNS. **Aucune session MCP initialisée, aucune liste d'outils obtenue et aucune requête métier envoyée.** Ces limites d'environnement ne prouvent pas une indisponibilité du service distant. |

La [présentation publique du 15 octobre](https://recherche.data.gouv.fr/fr/actualite/recherche-data-gouv-explorer-le-catalogue-de-jeux-de-donnees-en-dialogue-avec-un-assistant-ia) mentionne une phase de test d'assistant conversationnel et une rétention possible de **200 fiches par session**. Ce chiffre concerne la fonctionnalité décrite ; il ne doit pas être converti en quota contractuel du serveur MCP.

**Déduplication :** la source `recherche_data_gouv` figure déjà dans [les catalogues identifiés](../institutionnel/decouverte/catalogues_officiels_v1.json). Son interface est également décrite par la [PR #647](https://github.com/fraware/frontiere-institut-interet-public/pull/647) et reprise par la [PR de consolidation #685](https://github.com/fraware/frontiere-institut-interet-public/pull/685). **Pas de nouvelle entrée ni de nouvelle ingestion à enregistrer.**

**Prochain test reproductible, à autoriser dans un environnement réseau adapté :** vérifier la négociation de session MCP, inventorier les outils et schémas retournés, interroger une fiche de métadonnées non sensible, confronter l'identifiant, la source, la date et les enrichissements à la fiche originelle, conserver les codes de réponse et la provenance. Aucune étape n'est ici présentée comme accomplie.

## 2. Fraîcheur des manifestes effectivement présents sur main

Les états suivants proviennent des fichiers sous `main`, et **non** des données sorties au cours des exécutions programmées du jour.

| Contrôle | Dernier état publié sur main | Observation |
| --- | --- | --- |
| Référentiel des sources institutionnelles | [`institutionnel/etat_sources.json`](../institutionnel/etat_sources.json) : 15 octobre 2026 | 15 sources suivies, avec erreurs ou valeurs de fraîcheur incertaines selon les entrées |
| Catalogues découverts | [`institutionnel/decouverte/etat_collecte.json`](../institutionnel/decouverte/etat_collecte.json) : 20 octobre 2026 | Relevé partiel : 47 pages tentées, 45 réussies, 2 échouées ; 0 fichier source original téléchargé dans ce relevé |
| Balayage national | [`institutionnel/decouverte/balayage_etat.json`](../institutionnel/decouverte/balayage_etat.json) : 20 octobre 2026 | 24 pages examinées dans le dernier cycle, 0 copie de fichier brut, sans prétention d'exhaustivité du Web |
| Flux officiels | [`institutionnel/flux_publics/etat_collecte.json`](../institutionnel/flux_publics/etat_collecte.json) : 19 octobre 2026 | 300 signaux distincts déclarés lors du cycle ; qualification de besoin non effectuée |
| Inventaire DECP | [`institutionnel/decp/etat_ressources.json`](../institutionnel/decp/etat_ressources.json) : observation du 20 octobre 2026 | Inventaires de ressources ; pas d'acquisition des fichiers métiers dans cet inventaire |
| Archives des marchés attribués | [`institutionnel/marches_attribues/etat.json`](../institutionnel/marches_attribues/etat.json) : 20 octobre 2026 | 18 fichiers déclarés téléchargés et vérifiés, sans couverture nationale intégrale |
| Index intersources DECP | [`institutionnel/decp/bilan_index_unifie.json`](../institutionnel/decp/bilan_index_unifie.json) : 14 octobre 2026 | 5 643 identités distinctes déclarées ; 47 fichiers sources, 0 correspondance BOAMP vérifiée |

Le [contrôle transversal exécuté le 15 novembre à 06:20 UTC](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/43684985948) a constaté le retard des **dix relevés surveillés** de `main`. Pour le référentiel institutionnel : **740,4 h** depuis le dernier relevé, seuil configuré **72 h**. Pour les flux : **646,3 h**, seuil **36 h**. Pour le catalogue : **608,1 h**, seuil **48 h**. Ces écarts portent sur la date des états intégrés, pas nécessairement sur la date de toute tentative d'acquisition externe.

## 3. Échecs récurrents et étapes vérifiées

Les rapports consultés montrent un motif commun : le script [`scripts/publier_mise_a_jour_institutionnelle.py`](../scripts/publier_mise_a_jour_institutionnelle.py) **refuse délibérément** d'ouvrir une deuxième proposition `automatisation/<source>-...` tant qu'une PR de la même source reste ouverte. La validation préserve la cohérence des modifications concurrentes ; la contourner masquerait les conflits.

| Exécution GitHub Actions du 15 novembre | Ce qui a été exécuté | Blocage établi |
| --- | --- | --- |
| [Veille ANR, 43726595062](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/43726595062) | 6/6 points officiels accessibles, certaines modifications à relire | Publication refusée : proposition de même source déjà ouverte |
| [Veille DMTG, 43727176372](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/43727176372) | 5/5 sources consultées, 0 échec d'accès, 2 modifications à qualifier | Même refus de publication |
| [Référentiel institutionnel, 43715306954](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/43715306954) | 15 sources inspectées, 14 alertes déclarées ; 10 essais ciblés réussis | Même refus de publication |
| [Découverte des catalogues, 43691593769](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/43691593769) | Essai de catalogue scientifique **en échec** : aucune page officielle reçue ; état précédent préservé | Même refus supplémentaire de publication |
| [Contrôle transversal, 43684985948](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/43684985948) | Tests internes réussis, relevés et exécutions inspectés | Écart de fraîcheur déclaré, sortie de diagnostic de statut 2 |

Les [archives BOAMP, exécution 43723466741](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/43723466741), et l'[index historique BOAMP, exécution 43701158819](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/43701158819), ont terminé avec succès. **Le succès d'une procédure ne certifie pas, à lui seul, le déploiement Render ni l'actualisation de tous les manifestes de `main`.**

**Propositions automatiques en attente, vérifiées par les noms de branches de 43 PR ouvertes le 15 novembre :** les **14** branches de préfixe `automatisation/` correspondent à [#664](https://github.com/fraware/frontiere-institut-interet-public/pull/664) (pièces publiques), [#640](https://github.com/fraware/frontiere-institut-interet-public/pull/640) (délibérations), [#639](https://github.com/fraware/frontiere-institut-interet-public/pull/639) (ressources DECP), [#638](https://github.com/fraware/frontiere-institut-interet-public/pull/638) (BeauAMP), [#637](https://github.com/fraware/frontiere-institut-interet-public/pull/637) (sources), [#632](https://github.com/fraware/frontiere-institut-interet-public/pull/632) (DMTG), [#623](https://github.com/fraware/frontiere-institut-interet-public/pull/623) (flux), [#622](https://github.com/fraware/frontiere-institut-interet-public/pull/622) (canaux), [#618](https://github.com/fraware/frontiere-institut-interet-public/pull/618) (besoins publics), [#601](https://github.com/fraware/frontiere-institut-interet-public/pull/601) (programmes ANR), [#599](https://github.com/fraware/frontiere-institut-interet-public/pull/599) (surveillance), [#570](https://github.com/fraware/frontiere-institut-interet-public/pull/570) (sonde AIFE), [#485](https://github.com/fraware/frontiere-institut-interet-public/pull/485) (référentiel), [#449](https://github.com/fraware/frontiere-institut-interet-public/pull/449) (DGFiP).

Ce tableau donne les **propositions bloquantes possibles par famille**, pas un diagnostic de validité scientifique de leurs fichiers. Le script de publication consulte précisément la présence d'une branche `automatisation/<source>-` encore ouverte. Les PR #618 et #485 modifient respectivement 194 et 160 chemins déclarés dans GitHub : examen du périmètre et des conflits indispensable avant décision. Ne pas fusionner une proposition ancienne sur sa seule absence de conflit textuel.

Les procédures de publication de différentes sources sont bloquées par leurs propres PR en attente : leur décision doit être individualisée. Un échec de la phase de publication ne prouve pas un échec des étapes antérieures ; l'échec spécifique de récupération du catalogue scientifique est, lui, directement établi.

## 4. Branches, revue et déploiement

- `main` au SHA indiqué en tête ; branche principale non protégée d'après l'API GitHub consultée.
- [PR #685](https://github.com/fraware/frontiere-institut-interet-public/pull/685) : 81 catalogues proposés, non fusionnés ; contrôles précédents en échec.
- [PR #686](https://github.com/fraware/frontiere-institut-interet-public/pull/686) : correction technique des contrôles Python et Chromium proposée, sept jobs réussis sur sa branche ; revue humaine nécessaire avant fusion technique.
- [PR #687](https://github.com/fraware/frontiere-institut-interet-public/pull/687) : mandat et état documentaire en attente. Ses contrôles sur base actuelle ont rencontré les mêmes défaillances que celles motivant #686. Le présent document est une proposition **documentaire**, sans preuve de résolution des contrôles.
- **Render :** le [bilan historique du 16 octobre](ETAT_INITIAL_CHAINE_DOCUMENTAIRE_2026-10-16.md) rapportait le déploiement de `2d48f7012fe36f78456acc79b7085dc991a833ab` du 15 octobre. L'espace Render disponible dans le connecteur n'a pas été confirmé par l'utilisateur dans cette revue ; **aucune conclusion actuelle sur les services ou déploiements**.

## 5. Décision et trois priorités

Aucun état `Terminé` nouvellement attribué ; aucune dépense ni publication de donnée confidentielle.

1. **Trier les PR automatiques bloquantes par source** : contrôler les manifestes, leurs périodes, les changements et les conflits ; décider explicitement de fusionner, remplacer ou fermer uniquement les propositions démontrées admissibles. Ne pas lever le verrou globalement.
2. **Faire examiner le correctif technique #686**, puis relancer les contrôles obligatoires des PR documentaires #685 et #687 avant toute décision de fusion.
3. **Reconstituer un relevé frais et comparable pour les dix sources de veille**, en distinguant exécution en amont, pièces conservées sur les branches de collecte et intégration dans `main` ; rapprocher ensuite le déploiement Render de la révision GitHub effectivement publiée dès confirmation du bon espace de travail.

**Frontière de preuve :** document officiel consulté ≠ connexion MCP testée ≠ acquisition de fichiers sources ≠ intégration dans `main` ≠ mise en production sur Render.

## 6. Relecture complémentaire du 16 novembre 2026 — précisions et suivi de publication

Ce complément rectifie la datation de la documentation officielle et distingue l'apparition d'une **fiche de métadonnées** de la disponibilité de nouveaux résultats.

- **Recherche Data Gouv :** la [page officielle du guide du catalogue](https://recherche.data.gouv.fr/fr/page/guide-d-utilisation-du-catalogue-recherche-data-gouv) affiche « Mis à jour : **04/09/2026** ». La date du 29 octobre citée dans une version antérieure de cette note n'était pas confirmée par cette page ; elle est corrigée. La [page de présentation du catalogue](https://recherche.data.gouv.fr/fr/page/catalogue-recherche-data-gouv) affiche une mise à jour du **16/10/2026** et décrit l'interface MCP. **Aucune session MCP ni ingestion testée** lors de cette relecture ; ne pas créer une deuxième source `recherche_data_gouv`.
- **Enquête Insee « Associations 2024 » :** la [fiche officielle des produits associés](https://www.insee.fr/fr/metadonnees/source/operation/s2229/produits) affiche « Paru le **16/11/2026** », sans aucun résultat d'enquête ou produit associé présenté dans le contenu textuel consultable. **Preuve : fiche de métadonnées consultée ; aucun fichier de résultats ni questionnaire individuel acquis**. Une fiche datée ne suffit pas à établir la publication de résultats substantiels, un taux de réponse ou une diffusion dans un service de données. L'instrument est déjà documenté dans le [protocole de la PR #682](https://github.com/fraware/frontiere-institut-interet-public/pull/682), repris dans [#685](https://github.com/fraware/frontiere-institut-interet-public/pull/685) ; **pas de nouveau producteur ni de nouveau jeu de résultats enregistré**. La prochaine vérification portera sur des produits effectivement liés, leur méthodologie, leurs unités et leurs conditions de diffusion.
- **Surveillance GitHub du 16 novembre :** l'[exécution 43973987919](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/43973987919) confirme deux incidents distincts : **aucune page officielle reçue** lors de l'essai du catalogue scientifique, puis **publication refusée** parce qu'une proposition de la même source est ouverte. L'[exécution 43965220084](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/43965220084) du contrôle transversal signale de nouveau des relevés dépassant leurs seuils, avec une sortie de diagnostic de code 2. Les dernières exécutions de marchés, flux et dossiers institutionnels affichent aussi des échecs au niveau de leur procédure GitHub Actions ; leurs acquisitions métiers ne sont pas réputées toutes défaillantes sans lecture individuelle des étapes.
- **Révision et demandes de fusion :** `main` demeure à `b34cb3542385c6a759fe5fc56fdb640721f509e5` au contrôle. Les [PR #685](https://github.com/fraware/frontiere-institut-interet-public/pull/685), [#686](https://github.com/fraware/frontiere-institut-interet-public/pull/686) et [#687](https://github.com/fraware/frontiere-institut-interet-public/pull/687) sont ouvertes. Le [dernier contrôle de #687 examiné](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/43740257350) est en échec (Python 3.11, Python 3.12 et installation de Chromium), donc **pas de fusion**.

**Statuts :** découverte et lecture documentaire établies pour les deux pages primaires ; aucun essai d'ingestion, aucun résultat Insee substantiel et aucune résolution des retards revendiqués. L'état de Render n'est toujours pas vérifié. Aucune dépense engagée.
