# FRONTIÈRE — Hygiène des branches et demandes de fusion

**Audit initial :** 17 octobre 2026 (UTC). **Dépôt :** `fraware/frontiere-institut-interet-public`. **Périmètre :** nettoyage des références, sans destruction de contenu inédit.

## Inventaire contrôlé

Lors de la première lecture du dépôt, GitHub exposait **348 branches**, dont `main` et **10 demandes de fusion ouvertes**. La lecture paginée des 531 demandes fermées a permis de distinguer :

| Catégorie | Nombre à l'instantané initial | Décision |
| --- | ---: | --- |
| Branche encore présente, tête SHA identique à celle d'une demande **fusionnée** | **308** | Candidate à suppression contrôlée |
| Branche rattachée à une demande **fermée sans fusion** | **10** | Conserver jusqu'à évaluation du contenu inédit |
| Branche associée à une demande **ouverte** | **10** | Conserver jusqu'à décision sur la demande |
| Branche restante sans association de PR établie | **20** | Conserver jusqu'à preuve de redondance, de portée de test ou de reprise |
| **Total initial** | **348** | Exclut les nouvelles branches créées pour cet audit |

L'inventaire figé [des 308 suppressions candidates](../institutionnel/maintenance/branches_fusionnees_2026-10-17.json) consigne le nom exact, le SHA exact et le numéro de la demande de fusion correspondante. Le fichier n'est pas une instruction aveugle : le programme revérifie en direct l'état de GitHub à l'exécution.

## Règles de suppression

- Ne supprimer ni `main`, ni les branches protégées, ni aucune branche associée à une demande ouverte.
- Exiger que la demande correspondante ait été **fusionnée**, que son dépôt d'origine soit exactement ce dépôt et que son couple nom/SHA corresponde au plan.
- Vérifier une seconde fois le SHA effectif immédiatement avant suppression. S'il a changé, conserver la branche et signaler l'écart.
- Ne jamais supprimer uniquement en fonction d'un nom ressemblant à `automatisation/*`, `travail/*` ou d'une date ancienne.
- Garder les anciennes demandes fermées sans fusion pour une évaluation distincte. GitHub conserve les objets PR et commits après suppression des références déjà intégrées ; le plan garde leurs noms et SHA à des fins de reconstruction.
- Déclencher ce nettoyage exceptionnel uniquement à la fusion, sur `main`, de la modification du manifeste initial. La revue préalable est en lecture seule. Sauvegarder le rapport détaillé dans les artefacts GitHub Actions et conserver toute erreur de suppression.

## Réduction des demandes de fusion ouvertes

La liste initiale comprend les PR **570, 568, 550, 494, 487, 485, 484, 449, 407, 401**. Les données nouvelles du 17 octobre (sonde AIFE, canaux) sont à préserver. Les lots historiques non fusionnés (référentiel territorial, DGFiP XML, enquêtes SCDL) ne doivent pas être clos sur une simple durée d'inactivité. Le jugement de vétusté doit s'appuyer sur le contenu, la provenance, les dates producteur, l'existence d'une révision ultérieure et le résultat des essais.

Pour réduire durablement les blocages de collecte, chaque famille d'actualisation doit disposer d'au plus une proposition courante : soit la proposition existante est rendue compatible avec `main` et validée, soit elle est fermée avec justification après constat d'obsolescence. Aucun mélange automatique de deux instantanés de producteurs de dates différentes.

## Entretien permanent prévu

Le script `scripts/nettoyer_branches_fusionnees_hebdomadaire.py` et la procédure
`.github/workflows/hygiene_branches_hebdomadaire.yml` instaurent une revue
**hebdomadaire chaque lundi**, à partir de la branche principale. Elle retient
uniquement les références de PR fusionnées depuis plus de vingt-quatre heures,
avec nom et SHA encore identiques, absence de PR ouverte, aucune protection,
et une limite stricte de 325 références par exécution.

Avant toute suppression, les références sont lues à nouveau depuis GitHub.
Chaque exécution conserve un rapport détaillé trente jours. Les essais sur
PR sont sans suppression, et les déclenchements automatiques sont limités
à `schedule` ou `workflow_dispatch` sur le dépôt autorisé.

Il s'agit d'une seconde barrière de maintenance : la préférence à long terme
reste la fonctionnalité native GitHub « Automatically delete head branches »,
sous réserve d'une décision administrative distincte.

## Après le nettoyage

Le résultat attendu de la première opération est d'environ **40 branches restantes**, auxquelles s'ajoute la branche de maintenance tant que cette dernière existe. Ce n'est pas une garantie : tout changement simultané, défaut de permission ou nouvelle PR ouverte justifie la conservation de la branche concernée.

Pour éviter la réapparition des branches fusionnées, activer dans **GitHub → Settings → General → Pull Requests** la suppression automatique des branches après fusion, **si les droits d'administration le permettent**. Cet audit n'atteste pas la valeur actuelle de ce réglage. Une autre option est une maintenance programmée qui réutilise exactement les protections ci-dessus, avec revue des résultats.

**Aucune branche non fusionnée ne doit être supprimée sans évaluation de sa contribution résiduelle.**
