# FRONTIÈRE — Audit d'hygiène des branches et demandes de fusion, 16–17 novembre 2026

**État Git examiné en UTC le 17 novembre 2026.** Dépôt : [fraware/frontiere-institut-interet-public](https://github.com/fraware/frontiere-institut-interet-public).
**Révision de `main` après les trois fusions documentaires :** [`db7a31d7cc2e862c0226f44127abdee1d300be16`](https://github.com/fraware/frontiere-institut-interet-public/commit/db7a31d7cc2e862c0226f44127abdee1d300be16).

**Inventaire source :** [`institutionnel/maintenance/inventaire_hygiene_github_2026_11_17.json`](../institutionnel/maintenance/inventaire_hygiene_github_2026_11_17.json). Il contient les 81 noms et SHA de branches et les 40 PR ouvertes observées dans la version v2. Cette note est une **proposition**, pas une déclaration de fusion dans `main`.

## 1. Résultat réalisé

La [PR documentaire #675](https://github.com/fraware/frontiere-institut-interet-public/pull/675), consacrée à la comparaison des voies existantes de mobilisation des compétences scientifiques et numériques, a été **fusionnée par squash** dans `main` au commit `75998abc37f99bea1c9d1130ae3686458ccd8093`.

Avant fusion, sa branche était sans conflit et les **sept jobs de la procédure de vérification 41868442983** avaient abouti avec succès (Python 3.11/3.12, Chromium, index CSP, index BOAMP–DECP, index documentaire, conteneur). La PR modifie exclusivement cinq fichiers documentaires, dont la feuille de route, qui contient maintenant **F-092**. Elle ne déclare aucun cas d'intervention scientifique empiriquement terminé et ne déploie aucun nouveau collecteur.

**Autres intégrations de cette revue :** la [PR #671](https://github.com/fraware/frontiere-institut-interet-public/pull/671) (grille de qualification de l'accueil et de la continuité, un document) a été fusionnée après sept contrôles réussis au commit `bca6c5c15aecb93d2667faaabad140b9872070f1`. La [PR #683](https://github.com/fraware/frontiere-institut-interet-public/pull/683) (deux fiches CollTerr/SIES, découverte seulement) a été fusionnée après sept contrôles réussis au commit `db7a31d7cc2e862c0226f44127abdee1d300be16`. Les pages officielles confirment les budgets prévisionnels/réalisés, les fichiers CSV/JSON/PDF, la Licence Ouverte 2.0 et la mise à jour du 9 septembre 2026. Aucun fichier métier n'a été acquis durant cette revue.

**Contrôle après la fusion #675 :** la [procédure sur `main` 43996077099](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/43996077099) s'est terminée en **échec**, malgré les sept contrôles réussis de la PR #675 : les jobs Python 3.11 et Python 3.12 échouent sur deux contrôles de rédaction publique (les 1 266 autres tests Python 3.12 passent), et Chromium échoue car Playwright ne prend pas en charge `ubuntu26.04-x64`. Le correctif est précisément proposé dans [#686](https://github.com/fraware/frontiere-institut-interet-public/pull/686), qui a sept contrôles réussis **sur sa propre branche**. **L'intégration de #675 est effective, sans preuve que la CI de `main` soit actuellement saine.** Le résultat n'autorise ni désactivation des contrôles ni fusion de #685/#687 sans exécutions propres réussies.

## 2. Inventaire observé

| Objet | Nombre | Qualification |
| --- | ---: | --- |
| Branches Git | **81** | Comprend `main` et les branches ouvertes ou historiques |
| PR ouvertes | **40** | Dont 14 PR de provenance automatisée et cinq PR de mise à jour des actions GitHub |
| Branches sans PR ouverte, hors `main` | **40** | Ne sont pas présumées obsolètes |
| Branches sans PR ouverte **ancêtres vérifiés** de `main` | **4** | Comparaison Git : aucun commit en avance |
| Branches associées à des PR fusionnées avec conservation du SHA de tête | **3** | Branches sources de #675, #671 et #683, fusions squash ; nettoyage possible sous contrôle |
| Branches restantes sans PR ouverte et non qualifiées | **33** | **Préserver** : des commits potentiellement inédits subsistent |

**Quatre ancêtres vérifiés par comparaison des commits :**
`maintenance/attester-nettoyage-314-branches-20261017`, `veille/catalogues-officiels-2026-10-18-abes`, `veille/catalogues-officiels-2026-10-21`, `veille/catalogues-officiels-2026-10-22`. Ces références représentent des **candidats** à suppression à condition de recontrôler leur SHA, leur ascendance, la présence de PR associée et leur protection. **Aucune suppression n'a été effectuée pendant cette revue.** Une autre comparaison de branche n'a pas pu être résolue : aucune conclusion sur cette branche.

La [procédure hebdomadaire du 16 novembre, run 43915079137](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/43915079137), a réussi et enregistré `candidats: 0`, `supprimees: 0`. Ce succès atteste l'exécution du nettoyeur, non la disparition des 40 références restant sans PR ouverte.

## 3. Dépendances des PR prioritaires

| PR | Qualification actuelle | Décision |
| --- | --- | --- |
| [#686](https://github.com/fraware/frontiere-institut-interet-public/pull/686) | Correctif **technique** des tests Python et du système de Chromium. Sept jobs du run 43262645623 réussis, modifications de tests et de procédure GitHub Actions. | Revue technique humaine avant fusion ; ne pas convertir une validation CI en approbation de code. |
| [#685](https://github.com/fraware/frontiere-institut-interet-public/pull/685) | Consolidation documentaire de **81** catalogues, dont 58 ajouts proposés ; les tests précédents ont échoué. L'index a été réconcilié avec la tâche F-092 intégrée par #675. | Vérifier ses propres contrôles réussis, le chevauchement avec #682 et la licence de chaque source avant intégration. |
| [#687](https://github.com/fraware/frontiere-institut-interet-public/pull/687) | Mandat et notes de veille. Le journal a été reconcilié avec F-092 et `main` au moyen d'une fusion Git dont les quatre fichiers initiaux étaient conservés ; inventaire, audit et harmonisation des 92 travaux ont ensuite été ajoutés. | Attendre les vérifications de **sa** révision actuelle et l'absence de conflit ; ne pas fusionner sur la seule réussite antérieure de #686. |
| [#682](https://github.com/fraware/frontiere-institut-interet-public/pull/682) | Protocole associatif en brouillon. Le fichier proposé dans #685 est **différent** : version consolidée légèrement enrichie. | Comparer précisément les deux contenus avant de fermer #682 comme remplacée. |
| [#683](https://github.com/fraware/frontiere-institut-interet-public/pull/683) | **Fusionnée** : données documentaires CollTerr avec fichier identique à celui déjà proposé par #685. | La fusion de #685 devra préserver ce fichier, devenu présent sur `main`. Pas de double ingestion. |
| [#678](https://github.com/fraware/frontiere-institut-interet-public/pull/678) | Découverte des infrastructures INRAE : le fichier corrigé figure avec **SHA identique** dans #685. Une relecture de la [fiche officielle](https://www.data.gouv.fr/datasets/liste-des-infrastructures-de-recherche-inrae) donne le **21 juillet 2026**, et non le 16 octobre, comme date affichée de mise à jour. | Date corrigée dans #678, dans son dossier inclus par #685 et dans le catalogue consolidé. Ne fusionner qu'avec ses contrôles propres réussis et sans contenu métier inédit non vérifié. |
| [#671](https://github.com/fraware/frontiere-institut-interet-public/pull/671), [#679](https://github.com/fraware/frontiere-institut-interet-public/pull/679), [#670](https://github.com/fraware/frontiere-institut-interet-public/pull/670), [#667](https://github.com/fraware/frontiere-institut-interet-public/pull/667) | Propositions documentaires **en brouillon**, disposant d'exécutions CI historiques réussies sur leurs têtes examinées. | Conserver le statut de brouillon tant que la revue demandée n'est pas satisfaite ; revalider les conflits et contrôles avant intégration. |

Les cinq PR Dependabot [#659](https://github.com/fraware/frontiere-institut-interet-public/pull/659) à [#663](https://github.com/fraware/frontiere-institut-interet-public/pull/663) touchent des versions d'actions GitHub. Leurs dépendances, compatibilités et contrôles doivent être analysés séparément : une mise à jour majeure n'est pas documentaire.

## 4. Propositions automatiques et blocage récurrent

**14 PR issues de la publication automatique** sont encore ouvertes : #449, #485, #570, #599, #601, #618, #622, #623, #632, #637, #638, #639, #640, #664.

Les vérifications CI examinées classent **11** de ces branches comme `action_required` (validation d'exécution GitHub Actions absente) et **3** (#449, #485, #570) avec des contrôles échoués. L'absence de job réussi ne prouve ni l'absence d'archives originales ni leur intégrité. Les fichiers des PR #618 et #485 ont un périmètre important : 194 et 160 chemins modifiés au relevé antérieur. Conserver la provenance et les données inédites.

Le script de publication [`scripts/publier_mise_a_jour_institutionnelle.py`](../scripts/publier_mise_a_jour_institutionnelle.py) refuse une nouvelle PR `automatisation/<source>-` si une proposition de même famille reste ouverte. C'est une protection contre les modifications concurrentes ; **ne pas la supprimer pour faire artificiellement passer les collectes au vert**. Le traitement correct est un triage par source, avec recomposition, test et décision documentée sur la PR existante.

## 5. Gouvernance et règles de décision

La réponse GitHub indique **`main.protected = false`**. Cela justifie la priorité du [ticket #54](https://github.com/fraware/frontiere-institut-interet-public/issues/54) : définir et tester une protection effective de la branche principale et ses contrôles requis. Aucune protection n'a été activée dans cette revue.

- **Fusionner** : contenu documenté, sans conflit ni donnée confidentielle, contrôles obligatoires réussis sur le SHA actuel, et type de modification admissible. Les corrections techniques et modifications de données conservent les revues spécifiques.
- **Fermer comme remplacé** : uniquement après vérification de l'identité des fichiers ou de la couverture exacte sur `main`, et référence à la PR intégratrice.
- **Supprimer une branche** : seulement si aucun travail ouvert n'en dépend, avec SHA courant inchangé et preuve d'ascendance ou de fusion du commit exact ; consigner la suppression.
- **Conserver** : toute branche aux commits en avance, tout travail de recherche en brouillon, toute donnée originale dont la reprise n'est pas démontrée.

## 6. Trois priorités suivantes

1. **Revue technique puis décision sur #686**, afin de rétablir les contrôles sans affaiblir leur portée.
2. **Réaligner et tester #685/#687**, puis intégrer les dossiers documentaires vérifiés ; fermer les propositions sources reprises seulement après correspondance de SHA et présence vérifiée sur `main`.
3. **Trier les 14 propositions automatiques et les 40 branches sans PR** : préserver les 33 références non qualifiées, traiter les quatre ancêtres et les trois branches #675/#671/#683 par le mécanisme de suppression contrôlée, puis activer les protections attendues de `main`.

**Aucun déploiement Render, aucune suppression de branche, aucune dépense, aucune ingestion de données scientifiques et aucune nouvelle preuve de résultat causal ne sont revendiqués ici.**
