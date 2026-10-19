# FRONTIÈRE — Journal des revues de la feuille de route

**Document de suivi :** [feuille de route directrice et 91 travaux](FEUILLE_DE_ROUTE_DIRECTRICE.md). Ce journal est un historique daté de vérifications et de décisions, pas un compte rendu automatique de succès. Les révisions de la feuille de route conservent leurs identifiants stables `F-001` à `F-091`.

## Méthode de revue hebdomadaire

Chaque lundi, ou plus tôt si une contribution importante intervient :

1. Lire le commit courant de `main`, les demandes de fusion ouvertes et les résultats des contrôles automatiques. Si l'accès est indisponible, conserver le dernier état connu et noter la panne.
2. Examiner la dernière version des manifestes BOAMP, CSP et DECP, des registres d'institutions, du catalogue de sources et des bilans de veille. Distinguer les décomptes déclarés de ceux vérifiés par reconstruction.
3. Confronter le dernier déploiement public à la révision validée et noter les écarts de fraîcheur et de documents effectivement consultables.
4. Reprendre chaque étape active de la [feuille de route](FEUILLE_DE_ROUTE_DIRECTRICE.md), confirmer les progrès par un lien de preuve, puis modifier les états sans anticiper le résultat des procédures ou de la revue humaine.
5. Enregistrer les blocages, hypothèses falsifiées, décisions, coûts supplémentaires proposés et nouvelles dépendances. Aucun engagement budgétaire ni déploiement payant sans approbation.
6. Proposer une demande de fusion pour les changements documentaires. Ne pas fusionner si les vérifications obligatoires échouent. Conserver cette entrée même si la revue ne constate aucune modification.
7. Produire une synthèse brève : réalisations intégrées, restes à faire, écarts avec la planification, prochains trois travaux et décisions demandées.

Une demande de fusion de documentation reste requise pour rendre le suivi durable dans le dépôt ; un rappel périodique externe est distinct de la mise à jour effective de `main`.

## Entrées

### 2026-10-16 UTC — Constitution du plan et premier relevé

- **Référence examinée :** [`bc44675b4b30298d9337dda92699c0a4c47bcba2`](https://github.com/fraware/frontiere-institut-interet-public/commit/bc44675b4b30298d9337dda92699c0a4c47bcba2).
- **Nouvel instrument de suivi :** feuille de route exhaustive de 91 travaux, organisée en neuf phases et cinq jalons vérifiables.
- **Résultat de travail nouveau :** [premier audit transversal](ETAT_INITIAL_CHAINE_DOCUMENTAIRE_2026-10-16.md), confrontant les manifestes, les index locaux et le déploiement public.
- **Données examinées :** 5 196 avis BOAMP, 268 102 variantes CSP et 5 643 identités DECP selon les manifestes et les vérifications de la révision citée ; unités hétérogènes et populations non exhaustives.
- **Contrôles :** exécutions GitHub générales, index BOAMP–DECP et veille transversale réussies sur la révision de référence. Reproduction indépendante locale des corpus encore non effectuée.
- **Écart constaté :** Render publie `2d48f7012fe36f78456acc79b7085dc991a833ab`, une révision antérieure à `bc44675b` ; aucun déploiement nouveau demandé.
- **Propositions ouvertes :** huit demandes, à trier avant de nouveaux traitements concurrents.
- **Prochaines actions :** (1) reconstruire les index et relever les bilans, (2) mesurer les différences entre archives et site, (3) réconcilier les huit demandes de fusion.
- **Coût nouveau engagé dans cette revue :** aucun service ni forfait créé.
- **États de feuille de route :** « En cours » signifie développement partiel existant ; aucune des 91 étapes n'est déclarée « Terminée » sur la seule base de cet examen.

### 2026-10-17 UTC — Reprise des index, collectes et publication

- **Révision examinée :** [`0c196d8f461f83d5b10487995c37eaffc41ac63c`](https://github.com/fraware/frontiere-institut-interet-public/commit/0c196d8f461f83d5b10487995c37eaffc41ac63c), issue de la fusion contrôlée de la [PR n° 545](https://github.com/fraware/frontiere-institut-interet-public/pull/545).
- **F-003 et F-004 — Avancement, toujours « En cours » :** les [PR n° 542](https://github.com/fraware/frontiere-institut-interet-public/pull/542) et [n° 540](https://github.com/fraware/frontiere-institut-interet-public/pull/540) sont intégrées. La première remplace les nombres figés de la CI pour les index intégraux par une comparaison aux manifestes de la même révision ; la seconde corrige le lancement du contrôle du site public.
- **F-002 — Réconciliation partielle, toujours « À faire » :** la [PR n° 530](https://github.com/fraware/frontiere-institut-interet-public/pull/530) a été clôturée avec justification : l'échantillon AIFE du 15 octobre était antérieur à une extraction réelle du 17 octobre, dont la publication était bloquée. Le relevé du 17 octobre n'est pas encore intégré ; prochaine collecte à vérifier.
- **F-003 et F-015 — Révision documentaire :** la [PR n° 545](https://github.com/fraware/frontiere-institut-interet-public/pull/545) a été actualisée sur `main`, ses sept vérifications préalables ont réussi, puis elle a été fusionnée. L'état BOAMP déclare **5 517 avis distincts** au 16 octobre, contre **5 196** dans le premier bilan ; la différence de **321** correspond à des avis archivés, pas à des déficits de compétences démontrés.
- **Incidents identifiés :** la [veille transversale du 17 octobre](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/39045266302) signale des retards institutionnels et BOAMP. Les [collectes des besoins](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/39035023640) et de la [sonde AIFE](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/39034974496) avaient reçu un refus de publication motivé par une autre proposition encore ouverte. Ces échecs signalent un blocage de publication, non un échec de récupération des pièces observées.
- **Publication publique :** le dernier déploiement Render vérifié avant cette entrée est toujours `2d48f7012fe36f78456acc79b7085dc991a833ab` (15 octobre). La revue ne prétend pas qu'un déploiement récent a eu lieu.
- **Conditions restant à remplir :** contrôler la réussite des essais après la fusion n° 545 ; examiner la prochaine exécution de collecte AIFE ; publier la version validée sur Render et vérifier les manifestes effectivement servis ; terminer les vérifications indépendantes de l'[issue n° 537](https://github.com/fraware/frontiere-institut-interet-public/issues/537).
- **États de la feuille de route :** aucun statut promu à « Terminé ». Aucun besoin institutionnel, contrat commun ni recrutement effectif supplémentaire inféré.
- **Nouvelle dépense ou nouveau service :** aucun.
- **Trois priorités :** (1) confirmer la CI après les trois fusions ; (2) contrôler puis actualiser Render ; (3) traiter les propositions anciennes restantes par source, sans fusion de données périmées.

### 2026-10-17 UTC — Réduction de la dette GitHub

- **Référence examinée :** [`d0ba4b37257a99b0c4e9023020217fd31b34ee50`](https://github.com/fraware/frontiere-institut-interet-public/commit/d0ba4b37257a99b0c4e9023020217fd31b34ee50).
- **Branches :** la [procédure n° 39048500462](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/39048500462) a supprimé exactement **308** branches de propositions déjà intégrées, sans erreur ni exclusion, depuis un inventaire initial de 348 branches. La [PR n° 573](https://github.com/fraware/frontiere-institut-interet-public/pull/573) a intégré le nettoyage hebdomadaire prudent ; les branches sans preuve suffisante d'intégration sont préservées.
- **Propositions remplacées :** les [PR n° 575](https://github.com/fraware/frontiere-institut-interet-public/pull/575), [n° 578](https://github.com/fraware/frontiere-institut-interet-public/pull/578) et [n° 579](https://github.com/fraware/frontiere-institut-interet-public/pull/579) reprennent respectivement les canaux, la veille ANR et la veille DMTG. Chacune a passé sept contrôles et a été fusionnée ; les anciennes PR 568, 550 et 487 ont été clôturées après vérification des empreintes des fichiers effectivement intégrés. Les essais ANR et DMTG ont été renforcés pour accepter de véritables observations nouvelles en maintenant leur filiation.
- **Conservation d'un refus scientifique :** la reprise de la [PR n° 570](https://github.com/fraware/frontiere-institut-interet-public/pull/570) a échoué aux contrôles DECP lorsqu'elle modifiait une sonde sans reconstruire le bilan associé. La reprise n° 576 a été fermée sans fusion ; la n° 570 demeure ouverte.
- **Demandes actives :** cinq PR de fond (570, 485, 484, 449, 407) nécessitent une décision sur leurs données et leurs preuves. Les PR documentaires 401 et 494 ont été transférées dans la [tâche n° 572](https://github.com/fraware/frontiere-institut-interet-public/issues/572).
- **Issues :** les issues 26 et 27 ont été clôturées comme sous-expériences déjà suivies par l'issue 63 ; **aucune mesure d'évaluation indépendante n'est considérée réalisée**. Le [registre de triage](REGISTRE_TRIAGE_GITHUB_2026-10-17.md) classe les 24 autres issues selon leurs dépendances réelles.
- **États de la feuille de route :** aucun jalon scientifique marqué « Terminé » sans preuve. Aucune dépense ni nouveau service.
- **Priorités suivantes :** préserver les historiques et contrôler la reprise du référentiel territorial, réconcilier le bilan DECP avec les sondes mises à jour, activer la protection de `main` selon l'issue 54 après essai des collectes.

### 2026-10-19 UTC — Revue hebdomadaire, blocages de publication et couverture documentaire

- **Révision observée de `main` :** [`287c01c6bb7e81658b8d5df70bdc0b78e350bb21`](https://github.com/fraware/frontiere-institut-interet-public/commit/287c01c6bb7e81658b8d5df70bdc0b78e350bb21), datée du 19 octobre à 14:45 UTC. La [PR n° 621](https://github.com/fraware/frontiere-institut-interet-public/pull/621) a été intégrée au balayage documentaire ; cette fusion n'atteste aucune ingestion des candidats identifiés.
- **Propositions ouvertes consultées :** [n° 618](https://github.com/fraware/frontiere-institut-interet-public/pull/618) (besoins), [601](https://github.com/fraware/frontiere-institut-interet-public/pull/601) (ANR), [599](https://github.com/fraware/frontiere-institut-interet-public/pull/599) (surveillance), [570](https://github.com/fraware/frontiere-institut-interet-public/pull/570) (AIFE), [485](https://github.com/fraware/frontiere-institut-interet-public/pull/485) (référentiel), [449](https://github.com/fraware/frontiere-institut-interet-public/pull/449) (DGFiP) et [407](https://github.com/fraware/frontiere-institut-interet-public/pull/407) (délibérations). Les métadonnées GitHub indiquent `mergeable: false` pour chacune au moment de la lecture ; ce booléen seul ne diagnostique pas le conflit.
- **Échecs répétés vérifiés dans les journaux GitHub Actions :** [ANR 39271951324](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/39271951324), [surveillance 39239818081](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/39239818081), [référentiel 39243600272](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/39243600272) et [DGFiP 39240202335](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/39240202335) : publication refusée car une proposition concernant la même source attend une décision. Ne pas assimiler ces refus à des échecs de récupération des données. Le [contrôle transversal 39257058057](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/39257058057) a échoué avec des alertes de fraîcheur et des accès automatisés refusés à trois pages administratives ; disponibilité publique des producteurs non établie.
- **Manifestes relus sur la révision :** BOAMP `institutionnel/besoins_publics/etat_boamp.json` : **6 297 avis distincts conservés**, contrôle le 18 octobre à 23:24 UTC, couverture historique exhaustive `false`, dernière recherche de 3 118 enregistrements et zéro page échouée ; écart de **+780** par rapport aux 5 517 avis cités le 17 octobre. CSP `manifest_offres_postes.json` : **268 102 variantes** et **266 139 références distinctes**, extraction du 12 octobre, couverture intégrale du CSV `false`. DECP `bilan_index_unifie.json` : **5 946 attestations**, **5 643 identités** et **5 665 variantes**, bilan du 14 octobre. Les unités et dates diffèrent ; aucune reconstruction indépendante des archives n'est revendiquée.
- **Balayage national :** `institutionnel/decouverte/balayage_etat.json` indique deux cycles achevés, **80 pages** et **4 000 notices** relevées pendant la dernière exécution, prochaine page **1 201**, dernière exécution non complète. Les fichiers bruts métier copiés sont au nombre de zéro dans ce manifeste ; aucune exhaustivité du Web.
- **Render :** aucune vérification directe de service ou déploiement n'a été possible dans cette revue : le connecteur exige la sélection préalable d'un espace de travail confirmé. Ne pas reprendre le commit historiquement observé du 15 octobre comme preuve du déploiement actuel. Aucun déploiement déclenché.
- **Découverte distincte de l'ingestion :** trois fiches MESR proposées dans `institutionnel/decouverte/propositions_officielles_2026-10-19.json` ; liens et licences déclarées examinés sur les pages officielles, aucun export métier téléchargé ni schéma/pagination/empreinte validés.
- **États :** aucune des étapes F-001 à F-091 n'est promue à « Terminé » sur ces seules preuves. Aucun état antérieur modifié. **Dépenses nouvelles :** aucune.
- **Trois priorités :** (1) réconcilier les PR concurrentes et les refus de publication, en préservant les relevés nouveaux ; (2) reconstruire les archives et index BOAMP/CSP/DECP et leurs empreintes sur la même révision ; (3) obtenir la confirmation de l'espace Render, comparer le site effectivement servi à `main` et résoudre les alertes de fraîcheur.

### Modèle pour la prochaine entrée

```text
### AAAA-MM-JJ UTC — Objet de la revue
- Révision Git examinée :
- Demandes de fusion concernées :
- Contrôles et preuves réellement consultés :
- Étapes modifiées (identifiants et changement d'état) :
- Nouveaux résultats, contre-exemples, échecs :
- Écarts de fraîcheur, couverture et publication :
- Blocages et décisions nécessaires :
- Dépenses nouvelles approuvées (sinon aucune) :
- Trois actions prioritaires avant la prochaine revue :
```
