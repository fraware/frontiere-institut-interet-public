# FRONTIÈRE — Trois horloges distinctes

Le fichier statique `site_frontiere/metadonnees-index.json` est produit lors de la construction Render, sans nouvelle collecte des producteurs.

Il distingue explicitement :

- **Publication ou notification du document** : date propre à chaque résultat (parution BOAMP, début de publication de l'offre, notification DECP, éventuellement publication déclarée en repli).
- **État de l'archive versionnée** : date du dernier contrôle BOAMP, extraction du manifeste des offres, construction du bilan DECP, lorsque ces valeurs existent.
- **Indexation du site public** : date UTC à laquelle les documents ont été sélectionnés et les fichiers statiques écrits.

Les horodatages des bilans sont des événements de procédure documentaire distincts et ne démontrent pas la capture de chaque notice individuelle. Les champs `date_acquisition_de_chaque_avis`, `date_acquisition_de_chaque_offre` et `date_acquisition_de_chaque_marche` restent explicitement à `null` en l'absence de preuve individuelle.

Le fichier conserve également la révision Git des sources lorsqu'elle est disponible. Les archives sont identifiées par empreintes dans l'index principal. Une date de production récente n'implique ni une mise à jour complète des trois corpus ni un besoin public encore actif.
