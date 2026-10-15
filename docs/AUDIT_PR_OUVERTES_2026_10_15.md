# FRONTIÈRE — Revue des contributions ouvertes (15 octobre 2026)

## Contrôle de périmètre

Le périmètre actif est **BOAMP, emplois publics, DECP**. La voie TED a été explicitement abandonnée et ne doit pas revenir par un rétablissement de fichiers anciens. Le site est statique, sans collecteur hébergé par Render et sans stockage persistant facturé. Toute contribution à une collecte doit distinguer la programmation GitHub Actions, son dernier succès, et les archives réellement enregistrées.

## Inventaire GitHub au 15 octobre 2026 (état observé)

| PR | Proposition | État | Décision de revue |
|---|---|---|---|
| [#494](https://github.com/fraware/frontiere-institut-interet-public/pull/494) | Veille officielle, quatre sources | Brouillon | Vérifier l'identité des quatre sources, la datation et l'absence de duplication avant fusion |
| [#487](https://github.com/fraware/frontiere-institut-interet-public/pull/487) | Signatures des publications officielles DMTG | Ouverte | Vérifier le producteur, les empreintes et les changements par rapport à la source antérieure |
| [#485](https://github.com/fraware/frontiere-institut-interet-public/pull/485) | Référentiel administratif et territorial | Ouverte | Réconcilier avec l'état actuel de main ; vérifier les identifiants institutionnels et les cas de réorganisation |
| [#484](https://github.com/fraware/frontiere-institut-interet-public/pull/484) | Surveillance des sources institutionnelles | Ouverte | Vérifier les adresses officielles, l'absence de journalisation de données personnelles et la qualité des sondes |
| [#449](https://github.com/fraware/frontiere-institut-interet-public/pull/449) | Premier lot de marchés XML DGFiP | Ouverte | Priorité haute : confronter les tailles, empreintes et décomptes à la provenance DGFiP avant ingestion |
| [#448](https://github.com/fraware/frontiere-institut-interet-public/pull/448) | Catalogues nationaux DECP | Ouverte | Priorité haute : vérifier l'inventaire des ressources, les liens de téléchargement, les doublons et les versions |
| [#407](https://github.com/fraware/frontiere-institut-interet-public/pull/407) | Onze pistes de délibérations | Brouillon | Conserver la qualification « piste » tant qu'aucun usage institutionnel n'est documenté |
| [#401](https://github.com/fraware/frontiere-institut-interet-public/pull/401) | Découverte de quatre sources complémentaires | Brouillon | Maintenir au stade de découverte documentaire, sans annoncer d'ingestion |

Ces décisions sont un **tri préliminaire à partir des intitulés et de l'état des PR**. Elles n'équivalent ni à une analyse complète des différences de fichiers, ni à une acceptation scientifique ou opérationnelle.

## Contrôles avant fusion

1. Vérifier que la PR est fondée sur l'état actuel de `main` et n'introduit aucun fichier TED, configuration Render payante ou retour à une recherche serveur.
2. Examiner séparément les observations sources (URL officielle, date, taille, empreinte), les transformations et les champs publiés.
3. Vérifier les cas nuls, corrections de source, doublons, identifiants réutilisés et erreurs partielles ; conserver les archives antérieures.
4. Exécuter les contrôles Python 3.11, 3.12, conteneur et index documentaire sur la version candidate effectivement fusionnée.
5. Seuls les totaux provenant de manifestes contrôlés peuvent être annoncés publiquement. Les sondes et répertoires de catalogues ne constituent pas des collectes nationales complètes.

## Ordre de revue

**A :** #449 et #448, dont dépend la représentativité des marchés attribués.  
**B :** #485, #484 et #487 pour les identités et la surveillance des producteurs.  
**C :** #494, #407 et #401, dont la valeur dépend de preuves institutionnelles supplémentaires.

Une PR ancienne peut contenir un changement déjà intégré par une autre voie. Vérifier le contenu réel et les conflits avant de la fusionner ou de la fermer. Aucune des huit contributions n'est déclarée validée par ce seul document.
