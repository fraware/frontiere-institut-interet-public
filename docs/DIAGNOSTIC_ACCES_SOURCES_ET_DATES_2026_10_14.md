# Veille institutionnelle — examen des accès refusés et des dates

**Examen du 14 octobre 2026.** Cet examen recoupe les états de surveillance enregistrés dans le dépôt et des pages publiques consultées séparément. Il distingue les observations réelles, les limites des mécanismes de consultation et les hypothèses de remédiation.

## État initial du référentiel

Le fichier `institutionnel/etat_sources.json`, observé le 14 octobre à 10:12 UTC, enregistre trois erreurs `HTTPError: HTTP Error 403: Forbidden` : `budget_operateurs_2026`, `legifrance_aai_api` et `ape_portefeuille`. Quatre autres entrées du référentiel portent le statut `INDETERMINE` pour la fraîcheur du **contenu** : `dila_competence_geographique`, `mesr_etablissements`, `mesr_rnsr` et `mesr_rnsr_structures_actives`.

Un refus HTTP décrit seulement la requête effectuée par le collecteur à un instant donné. Il ne prouve pas l'absence de la ressource sur le site de l'éditeur, une suppression, une interdiction juridique de réutilisation ou l'inexistence des données. La procédure de surveillance ne doit pas le présenter comme une indisponibilité générale.

| Source surveillée | Observation dans le dépôt | Vérification documentaire complémentaire | Diagnostic défendable |
| --- | --- | --- | --- |
| [Portefeuille APE](https://www.economie.gouv.fr/agence-participations-etat/comprendre-lape/les-entreprises-de-lape) | HTTP 403 du client programmé | La page officielle a été consultée par le navigateur de recherche le 14 octobre ; elle décrit le portefeuille et présente les entreprises. | Refus du client automatique ; source publique accessible par au moins un autre moyen |
| [Données des opérateurs PLF 2026](https://www.budget.gouv.fr/documentation/file-download/31510) | HTTP 403 du client programmé | Le navigateur de recherche rencontre un fichier supérieur à sa limite de récupération (environ 11,7 Mo), sans valider son contenu. | Disponibilité publique **non conclue** ; examiner type de fichier, redirections, format, taille et point d'accès |
| [Texte Légifrance sur les AAI/API](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000033897475) | HTTP 403 du client programmé | Le navigateur de recherche a également reçu un refus HTTP 403. | Accès automatique refusé ; ne pas conclure que le texte juridique n'est plus publié |

Ces résultats n'établissent pas un accès réseau utilisable depuis les procédures GitHub. Ils n'autorisent pas le contournement de restrictions de l'éditeur.

## Changement de classification

La fonction `classifier_erreur_source` distingue maintenant notamment `ACCES_REFUSE_CLIENT_AUTOMATISE` pour HTTP 403, `LIMITATION_TEMPORAIRE_ACCES` pour HTTP 429 et `RESSOURCE_NON_TROUVEE_A_CETTE_ADRESSE` pour HTTP 404. L'état de la source conserve la description de l'erreur d'origine. Le contrôle transversal traite également les anciens états dépourvus de code structuré.

L'affichage `FRAICHEUR_INDETERMINEE` du contenu n'est pas synonyme d'échec du relevé. Une page dépourvue de date de modification exploitable peut être interrogée récemment avec succès sans fournir de date contrôlable de dernière modification de ses informations.

## Distinction temporelle des délibérations

Dans la file de revue, `deliberation_date` est désormais représenté par `date_evenement` ; `date_publication` est laissé inconnu tant que la date de publication de l'acte n'a pas été retrouvée dans une source primaire. Cette correction empêche qu'un acte ancien importé récemment apparaisse dans la catégorie des publications récentes sur une hypothèse erronée.

## Prochaines vérifications ciblées

1. Pour l'APE, confronter le refus du collecteur aux exigences HTTP de l'éditeur. Chercher une ressource officielle structurée ou exportable et un relevé de licence avant d'ajouter un autre chemin d'accès. La consultation manuelle de la page ne valide pas automatiquement une collecte robotisée.
2. Pour le PLF 2026, établir l'identité, le type, la taille et l'éventuelle version datée du document ; rechercher chez la Direction du Budget un point de publication officiel plus stable. Tester des requêtes bornées uniquement lorsque le serveur et les conditions d'accès le permettent.
3. Pour Légifrance, chercher un accès officiel documenté à l'API ou à un export autorisé et distinguer la disponibilité du texte de la capacité du client à l'interroger. Une authentification ou une autorisation pourrait être nécessaire ; aucune n'est présumée obtenue.
4. Pour les quatre dates indéterminées, vérifier si le producteur publie une métadonnée de mise à jour dans un catalogue officiel. Ne pas fabriquer de date à partir de la date de consultation de la page.
5. Mesurer, lors de la prochaine exécution automatisée, les codes d'erreur structurés et les différences entre sources consultées et contenu qualifié.

**Limite :** aucune des trois voies d'accès n'a été réparée dans cette étude. Aucun nouveau nombre d'organismes ni résultat empirique n'est déduit. La classification est une amélioration de diagnostic et de traçabilité.
