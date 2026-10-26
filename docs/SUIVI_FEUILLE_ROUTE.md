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

### 2026-10-26 UTC — Revue hebdomadaire : blocages de publication, CI et Render

- **Révision examinée :** [`54e024d48eba8209fbac64b617d188db2bc5792c`](https://github.com/fraware/frontiere-institut-interet-public/commit/54e024d48eba8209fbac64b617d188db2bc5792c), dernier commit de `main` confirmé par l'API GitHub lors de cette revue ; branche `main` signalée non protégée. La feuille de route et ce journal ont été relus. **Aucun des 91 états n'est promu à « Terminé ».**
- **Demandes de fusion :** 17 PR ouvertes à la consultation, dont les propositions documentaires [#641](https://github.com/fraware/frontiere-institut-interet-public/pull/641), [#642](https://github.com/fraware/frontiere-institut-interet-public/pull/642) et [#643](https://github.com/fraware/frontiere-institut-interet-public/pull/643), toutes en brouillon. Elles sont techniquement déclarées fusionnables par GitHub, avec état `unstable` : cinq contrôles réussis et deux contrôles Python échoués sur chacune des trois révisions exactes. Les deux échecs récurrents de `tests/test_app.py` (lignes 739 et 818) correspondent à une réponse HTTP 400 au lieu de 303 sur le plan prospectif après verrouillage ; [exécution #643](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/40208011455). **Cause identifiée par inspection du code :** les deux tests soumettent la date fixe `2026-10-20` ; la route `app/main.py::lock_paired_comparison` refuse explicitement `date_observation < date.today()`. Depuis le 21 octobre, ce scénario positif est périmé. Corriger les données de test avec une date future contrôlée sans supprimer la vérification de refus des dates passées. **Fusion interdite tant que les contrôles obligatoires échouent.**
- **Échecs de publication répétés :** le 26 octobre, les [découvertes de sources](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/40337434275), les [catalogues DECP](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/40308377474), les [besoins publics](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/40297642816) et la [veille ANR](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/40339239820) échouent à l'étape de publication avec le message « Une proposition de la même source attend déjà une décision ». Cela atteste un blocage de publication, sans démontrer un échec de collecte métier. Le [contrôle transversal](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/40326009680) échoue également et signale des retards et refus d'accès client automatisé.
- **Manifestes de `main` :** BOAMP [`etat_boamp.json`](https://github.com/fraware/frontiere-institut-interet-public/blob/main/institutionnel/besoins_publics/etat_boamp.json) : 6 297 avis distincts conservés, contrôle du 18 octobre ; CSP [`manifest_offres_postes.json`](https://github.com/fraware/frontiere-institut-interet-public/blob/main/institutionnel/besoins_publics/manifest_offres_postes.json) : 268 102 offres/variantes distinctes déclarées, extraction du 12 octobre, couverture intégrale du CSV explicitement fausse ; DECP [`bilan_index_unifie.json`](https://github.com/fraware/frontiere-institut-interet-public/blob/main/institutionnel/decp/bilan_index_unifie.json) : 5 643 identités distinctes, construit le 14 octobre, sans couverture nationale. Ces décomptes proviennent des manifestes publiés et n'ont pas été recalculés indépendamment pendant cette revue.
- **Découverte nationale :** [`balayage_etat.json`](https://github.com/fraware/frontiere-institut-interet-public/blob/main/institutionnel/decouverte/balayage_etat.json) déclare trois cycles achevés au 20 octobre, 74 535 jeux annoncés par le catalogue national et zéro fichier brut copié. [`etat_collecte.json`](https://github.com/fraware/frontiere-institut-interet-public/blob/main/institutionnel/decouverte/etat_collecte.json) conserve deux échecs `RemoteDisconnected` sur 47 pages tentées et neuf identifiants nouveaux non qualifiés ; collecte incomplète. Aucune exhaustivité du Web revendiquée.
- **Déploiement Render directement contrôlé :** service `frontiere-observatoire-public` (`srv-db8ekaajnfac73fb1gug`), lié à ce dépôt sur `main`, avec déploiement automatique **désactivé**. Dernier déploiement `live` [`dep-db9pm42jnfac73d6acng`](https://dashboard.render.com/static/srv-db8ekaajnfac73fb1gug) du **17 octobre 2026, 15:58 UTC**, au commit `0195a7688075e5d6e136a559feb41298a3bfc417`. Il est antérieur au `main` du 20 octobre. Le statut `live` n'atteste pas la concordance du contenu servi avec les derniers manifestes ; aucun nouveau déploiement déclenché.
- **Nouvelle source qualifiée :** [Eurostat GBARD, code `gba_nabsfin07`](https://ec.europa.eu/eurostat/databrowser/view/gba_nabsfin07__custom_7846942/default/table?lang=en), allocations budgétaires publiques de R&D par objectifs NABS 2007 ; mise à jour des données affichée au 25 septembre 2026, API REST documentée et réutilisation sous conditions d'attribution et d'exceptions pour les pays tiers. Proposition séparée dans `institutionnel/decouverte/propositions_officielles_2026-10-26.json`. **Découverte documentaire uniquement : aucune ingestion, requête métier réussie, validation de schéma ou d'empreinte.** Tentative HTTPS directe bloquée par DNS dans le conteneur.
- **États et décisions :** F-002, F-003, F-006, F-007, F-011 et F-019 restent ouverts selon les critères de preuve de la feuille de route ; aucun état, priorité ou échéance modifié. Aucun nouveau service, déploiement, achat ou coût engagé. La présente mise à jour documentaire doit rester en PR tant que ses contrôles obligatoires échouent ou qu'un conflit subsiste.
- **Trois priorités :** (1) réconcilier par source les PR en attente et résoudre les deux tests prospectifs Python sans affaiblir leurs assertions ; (2) reconstruire et dater les corpus BOAMP/CSP/DECP sur une révision unique avec empreintes et dénominateurs ; (3) préparer une publication Render contrôlée de `main`, sans la déclencher avant validation de la CI, de la concordance et des coûts.

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
