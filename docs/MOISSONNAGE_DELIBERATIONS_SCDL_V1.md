# Moissonnage autonome des délibérations locales structurées

## Finalité empirique

FRONTIÈRE recherche des **indices documentaires** de mobilisation, d'expérimentation et d'utilisation de moyens scientifiques et techniques dans les collectivités. Les avis de marchés documentent souvent la phase d'achat ; les délibérations peuvent contenir des étapes postérieures, des décisions de poursuite ou des évaluations publiques. Un exemple étayé apparaît dans [l'enquête Sicoval–Delibia](ENQUETE_SICOVAL_DELIBIA_USAGES_MUNICIPAUX_2026_10_14.md). La présente collecte étend **la découverte**, sans transformer les mots d'un titre en preuve d'usage.

Référence du format ouvert : [schéma national SCDL des délibérations, version 2.1.4](https://schema.data.gouv.fr/scdl/deliberations/2.1.4/documentation.html). La source de découverte est le [catalogue officiel des jeux de données de data.gouv.fr](https://www.data.gouv.fr/datasets/). Des jeux de délibérations de Gironde numérique, entre autres, y sont déjà référencés. Chaque producteur conserve son périmètre ; aucun recensement national exhaustif n'est présumé.

## Procédure automatique

Le programme `scripts/moissonner_deliberations_publiques.py` interroge trois termes fixes dans le catalogue officiel et examine au plus deux pages par terme. Il sélectionne uniquement les jeux dont le titre désigne explicitement des délibérations ou des actes réglementaires et dont la licence structurée est reconnue comme réutilisable. Il récupère **au plus vingt-cinq fichiers CSV** par exécution, uniquement depuis `static.data.gouv.fr/resources/` ou par la [passerelle tabulaire officielle de data.gouv.fr](https://tabular-api.data.gouv.fr/api/doc) sur `tabular-api.data.gouv.fr`, en reconstruisant l'adresse à partir de l'identifiant public de ressource. Aucun domaine tiers contenu dans une fiche de jeu de données n'est appelé directement. Chaque lecture est limitée à quatre millions d'octets et quatre-vingt mille lignes.

Les fichiers doivent comporter les quatre champs SCDL `COLL_SIRET`, `DELIB_ID`, `DELIB_DATE` et `DELIB_OBJET`. Les recherches utilisent des expressions rédigées explicitement, notamment « intelligence artificielle », « Delibia », « assistant juridique », « retranscription », « cybersécurité », expérimentation logicielle et formation technique. **Le seul sigle IA, trop ambigu, ne déclenche pas de correspondance.**

Les sorties sont `institutionnel/deliberations_publiques/pistes.json` et `etat_collecte.json`. Pour chaque piste : organisme, SIRET, identifiant et date de délibération, éventuelle URL annoncée du document, étiquettes de repérage, identifiants de jeu et de ressource, empreintes SHA-256 du CSV et de la ligne source. Le texte intégral libre de l'objet, les colonnes personnelles supplémentaires et les PDF annexés **ne sont pas copiés**. Les empreintes protègent la filiation documentaire sans valoir vérification de la pièce jointe.

La reprise conserve les pistes précédentes si un téléchargement échoue et évite les identifiants dupliqués. Un curseur versionné `position_suivante` avance d'un lot au suivant dans la liste des ressources admissibles et revient au début en fin de liste. Comme le catalogue est évolutif, même un tour achevé ne signifie pas que toutes les délibérations françaises ont été parcourues. Si aucune page du catalogue officiel n'est obtenue, le programme échoue **avant d'écrire** : un problème réseau n'est pas confondu avec une absence de délibérations. Si les jeux admissibles ne disposent pas de fichier directement accessible ni de copie traitée par l'API tabulaire, le bilan peut établir **zéro CSV téléchargé et zéro nouvelle piste**, sans inventer de résultat. Un échec de la passerelle officielle ne prouve pas l'inaccessibilité de la ressource chez son éditeur.

## Exploitation et interprétation

Les pistes sont `correspondance_textuelle_non_qualifiee` et portent `preuve_usage_verifiee = false`. La date enregistrée est la date déclarée de délibération ; elle n'est ni la date d'une première utilisation effective, ni une date de notification. L'URL éventuelle d'une pièce est un **pointeur à vérifier séparément**, jamais la preuve de lecture de ce document.

Pour qualifier une piste, il faut rechercher l'acte original et son passage exact, identifier sans ambiguïté l'acheteur, le dispositif contractuel et le bénéficiaire, puis comparer les étapes datées : besoin initial, accès à une compétence ou solution, premier usage, décision de poursuite et résultat observé. Les comparaisons temporelles impliquant plusieurs marchés ne seront admises qu'une fois leurs identités établies.

## Déclenchement et suivi sans intervention humaine

Le programme est testé hors réseau par `tests/test_moissonner_deliberations_publiques.py`. La tâche `.github/workflows/moissonnage-deliberations-scdl.yml` est planifiée **deux fois par semaine**, avec possibilité d'exécution manuelle. Elle crée une proposition limitée aux deux fichiers de résultat ; la fusion automatique ne se produit qu'après réussite des contrôles Python 3.11, Python 3.12 et conteneur sur la révision exacte proposée.

Les limites de la première version sont explicites : couverture de catalogue partielle, absence de téléchargement direct depuis les hébergements externes, fichiers sans SCDL strict ignorés, absence d'extraction automatique de PDF et **absence de preuve d'efficacité ou de déficit de compétence**. La vérification de la réussite réelle de la tâche distante reste distincte de la réussite des tests hors réseau.

## Premier relevé en conditions réelles

La première exécution déclenchée après intégration (GitHub Actions n° [38517844762](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38517844762)) a produit une première proposition de données n° [374](https://github.com/fraware/frontiere-institut-interet-public/pull/374). Son état de collecte déclare 15 jeux de données retenus, 15 fichiers éligibles examinés, 11 fichiers reçus, 612 lignes SCDL contrôlées, 0 correspondance aux expressions surveillées et 6 anomalies ou indisponibilités recensées, dont 3 refus de schéma. Ces résultats **ne démontrent aucune absence de besoin** et motivent l'extension au-delà des quinze premières ressources. Le curseur de progression est activé par la présente révision ultérieure, pas par cette première exécution historique.
