# Veille FRONTIÈRE — fraîcheur, qualité et utilisation scientifique

**Version initiale : 14 octobre 2026.** Les dates désignent les observations enregistrées dans Git, et non une garantie de surveillance en temps réel.

## Chaîne complète de connaissance

La veille distingue six étapes, soumises à des contrôles différents.

1. **Découvrir une source** : identifier le producteur, son URL officielle, son jeu de données, le format, les droits et la voie d'accès.
2. **Vérifier la source** : tester son schéma, les fichiers disponibles, la pagination, les champs et les restrictions de réutilisation.
3. **Actualiser un relevé** : conserver date de vérification, succès individuels, modifications, provenance et échecs.
4. **Rapprocher des pièces** : ne relier des institutions ou événements que par identifiants probants, liens officiels ou preuves explicites.
5. **Qualifier une observation** : rechercher une pièce primaire, la chronologie, les alternatives publiques, les explications concurrentes et les résultats.
6. **Expliquer un mécanisme** : documenter les délais, coûts, capacités mobilisées, effets et limites de chaque interprétation.

Aucun passage automatique de la découverte d'une publication vers « besoin public démontré » n'est autorisé. Marché, délibération, offre d'emploi et utilisation effective sont des objets différents.

## Infrastructure existante

Le dépôt comprend des collectes programmées relatives aux institutions (DILA, Insee), à la recherche publique, aux annonces BOAMP, aux emplois publics, aux données essentielles des marchés (DECP), aux marchés attribués, aux délibérations locales SCDL, aux sites institutionnels, aux catalogues et aux flux RSS/Atom ou sociaux officiels.

Les métadonnées ne constituent pas une ingestion intégrale des données métiers. Les signaux publics sont conservés comme *non qualifiés* avant lecture contradictoire.

## Contrôle transversal ajouté

La politique de contrôle figure dans institutionnel/veille/controle_v1.json. Le programme scripts/auditer_fraicheur_veille.py vérifie dix fichiers d'état de collecte et, sur demande avec le droit de lecture GitHub Actions, les dernières réussites des seize procédures programmées recensées dans le dépôt.

Il inspecte la date du dernier relevé, les erreurs partielles, la disponibilité des sources critiques, la fraîcheur déclarée du contenu chez le producteur et le dernier succès propre à chaque flux. Il reconnaît explicitement une collecte SCDL non exhaustive.

**Exécution locale, sans réseau** : exécuter python -m pytest -q tests/test_auditer_fraicheur_veille.py, puis python scripts/auditer_fraicheur_veille.py.

**Exécution avec historique GitHub** : exécuter le même programme avec --repertoire-github fraware/frontiere-institut-interet-public et un jeton GH_TOKEN disposant de la lecture des procédures. Le jeton ne doit jamais apparaître dans les documents ou journaux.

Le programme ne modifie aucun fichier suivi, ne télécharge aucun contenu scientifique et n'a aucun droit de fusion. Il publie des rapports Markdown et JSON dans les pièces d'exécution GitHub, non dans un dossier de preuve empirique.

La procédure .github/workflows/controle-veille.yml est prévue toutes les six heures et à la demande. Elle réalise des tests hors réseau puis interroge en lecture l'historique des procédures GitHub. Les rapports sont conservés trente jours ; un retard critique signale une exécution en échec. Les avertissements simples ne sont pas assimilés à l'arrêt complet du système.

**Limite :** les planifications GitHub ne sont pas garanties à l'heure exacte. Si toutes les exécutions programmées s'arrêtent, ce contrôle interne ne créera pas lui-même d'alerte : un observateur extérieur indépendant serait nécessaire.

## Trois temporalités distinctes

- **Observation du relevé :** date à laquelle FRONTIÈRE a consulté ou enregistré un état.
- **Exécution réussie :** date à laquelle la procédure de contrôle ou collecte a terminé avec succès.
- **Publication de la source :** date à laquelle l'organisme producteur a publié ou modifié l'information.

Une source ancienne correctement consultée ne devient pas récente. Un état récent ne garantit pas la validité d'un acte, et un incident de collecte ne prouve pas l'absence de données.

Les fenêtres maximales d'âge de 36 à 960 heures (40 jours pour les traitements mensuels) représentent des seuils exploratoires de *retard de surveillance*, et non des obligations de publication imposées aux producteurs.

## Incidents et décisions

Si un contrôle signale une situation critique, vérifier le journal GitHub, les états sources, les propositions de fusion en attente, les erreurs du producteur et les dates de dernière réussite. Éviter de publier des conclusions fondées sur les seules données en retard tant que l'incident n'a pas été qualifié.

Une alerte de niveau attention signale une collecte partielle, un flux individuel retardé ou la vétusté du contenu chez le producteur. Le dernier état confirmé doit être conservé, avec son horodatage. Une impossibilité de lecture n'est jamais convertie en zéro résultat.

L'évaluation scientifique doit suivre une autre chaîne : sources primaires, actes, besoin précis, solution publique existante, ressource extérieure, première contribution utile, comparaison contradictoire. La surveillance ne démontre aucune efficacité de FRONTIÈRE.

## Sources complémentaires à expertiser

| Famille | Information potentielle | Condition d'intégration |
| --- | --- | --- |
| [API officielle data.gouv.fr](https://guides.data.gouv.fr/api-de-data.gouv.fr/reference/datasets) | Identifiants, producteurs, versions des jeux publics | Pagination, couverture, licence, mises à jour |
| [Interface tabulaire data.gouv.fr](https://tabular-api.data.gouv.fr/api/doc) | Lignes structurées de jeux admissibles | Pagination réelle, schéma, limites de taille, complétude |
| [Registre des schémas de données](https://schema.data.gouv.fr/) | Évolutions des formats et contrôles de conformité | Version, schéma effectif, champs obligatoires |
| Décisions et procès-verbaux des collectivités | Parcours entre achat, convention et travail effectif | Acte primaire, signature, dates, effet constaté |
| Catalogues scientifiques et européens de la [proposition n° 401](https://github.com/fraware/frontiere-institut-interet-public/pull/401) | Ressources institutionnelles ou scientifiques à vérifier | Identité, licence, format, capacité réellement mobilisable |

Ces pistes ne sont **pas déclarées intégrées**. Leur admission nécessite une revue humaine, des essais techniques et une justification scientifique explicite. Ne pas doubler les découvertes encore en attente dans la proposition n° 401.

## File de revue quotidienne à provenance contrôlée

Le programme `scripts/preparer_revue_veille.py` parcourt les publications publiques et les onze pistes de délibérations déjà enregistrées. Il conserve pour chaque élément un identifiant de provenance, la date de publication déclarée, la date de première observation, un lien de référence et un statut explicite de pièce non qualifiée. Il ne télécharge aucun nouveau document.

La priorité de revue est fondée sur la date de publication, en distinguant les **90 derniers jours**, les dates inconnues, les archives et les dates incohérentes. Les publications anciennes découvertes aujourd'hui ne sont pas présentées comme des nouvelles récentes. À priorité temporelle égale, la sélection est répartie entre producteurs afin qu'un flux très abondant ne monopolise pas les premiers dossiers. Les résultats et les éventuelles limites de la file sont consignés dans les pièces jointes de la procédure de contrôle.

Les correspondances sont exclusivement lexicales et ne constituent pas une évaluation de pertinence scientifique, de nouveauté ni de fiabilité. Les délibérations du registre SCDL sont incluses parmi les pistes sans avoir été vérifiées par lecture de leurs actes primaires. La file ne modifie aucun registre d'épisodes vérifiés.

## Étape scientifique suivante

Constituer un registre séparé des **propositions de liens documentaires**, avec identifiant de chaque source, méthode de correspondance, date, niveau de preuve, hypothèse concurrente, relecture humaine et résultat. Il permettra de transformer les observations issues des différentes veilles en enquêtes, sans assimiler une concordance de textes ou de fournisseurs à la preuve d'un même épisode.

La valeur du système doit être mesurée par le nombre de cas correctement étayés, les contre-exemples, la qualité des chronologies et l'utilité pour la décision, et non par le volume brut des publications recueillies.
