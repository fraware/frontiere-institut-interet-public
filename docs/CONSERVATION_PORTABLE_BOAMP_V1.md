# Conservation portable des archives publiques du BOAMP

## Objectif et périmètre

Le programme `scripts/exporter_archive_boamp.py` produit un paquet ZIP contenant les relevés journaliers publics du Bulletin officiel des annonces des marchés publics (BOAMP), les versions corrigées archivées, leurs manifestes et les états de reprise et de surveillance. La source documentaire est l'interface officielle de la Direction de l'information légale et administrative (DILA). Les fichiers exportés proviennent exclusivement du corpus déjà publié et contrôlé par FRONTIÈRE.

Les annonces de marchés sont des **unités documentaires**. Ce paquet ne constitue ni un inventaire exhaustif de tous les marchés français ni une preuve de difficulté à mobiliser une compétence scientifique.

## Procédure et contrôles

Avant toute création, le programme reconstruit intégralement l'index de recherche dans un dossier temporaire. Ce passage vérifie les notices initiales, les versions corrigées, leur origine, leurs dates, leurs empreintes et le dernier état observé. La constitution du paquet refuse ensuite les chemins inhabituels, les liens symboliques, les fichiers trop volumineux et tout fichier de données séparé de son manifeste.

Le paquet contient `boamp/inventaire.json`, qui indique la révision exacte du dépôt source lorsqu'elle est renseignée, le nombre de journées et d'avis validés et pour chaque fichier son nom relatif, sa taille et son empreinte SHA-256. L'écriture ZIP est reproductible à contenu et révision égaux. Le fichier temporaire est vérifié avant son remplacement atomique. Un contrôle indépendant relit ensuite la composition et les empreintes de toutes ses entrées.

Depuis la racine du dépôt :

```bash
python scripts/exporter_archive_boamp.py exporter --paquet /tmp/archives-boamp.zip --revision COMMIT_GIT_COMPLET
python scripts/exporter_archive_boamp.py verifier --paquet /tmp/archives-boamp.zip
```

Remplacer `COMMIT_GIT_COMPLET` par les quarante caractères hexadécimaux d'une révision connue. L'argument peut être omis pour un export hors Git ; le manifeste porte alors une révision non renseignée.

## Fabrication périodique

La procédure `.github/workflows/export-boamp-portable.yml` effectue ce travail chaque semaine et sur demande. Elle produit un fichier ZIP, un bilan et une preuve de vérification dans un artefact GitHub Actions accessible pendant trente jours. Cette copie temporaire peut servir à un transfert contrôlé vers un dépôt d'archives durable. Elle évite de commettre une nouvelle copie volumineuse des fichiers dans l'historique Git.

La conservation de l'artefact GitHub **n'établit aucune copie indépendante et permanente**. Une véritable conservation hors site suppose un emplacement distinct, des droits et une politique de conservation définis, une vérification après transfert par l'empreinte externe du paquet et des essais de restauration. La fiche indique explicitement que cette étape n'a pas été réalisée.

## Conservation mensuelle parmi les versions du dépôt

Une seconde procédure, `.github/workflows/conservation-boamp-versions.yml`, complète la production hebdomadaire temporaire par un **instantané mensuel publié parmi les versions du dépôt GitHub**. Le premier passage du mois (ou l'exécution initiale du programme) produit quatre fichiers : `archives-boamp.zip`, `bilan.json`, `verification.json` et `SHA256SUMS.txt`. Chaque livraison porte une étiquette `archives-boamp-AAAA-MM` et renvoie à la révision du dépôt réellement téléchargée.

La publication passe par un état provisoire : la procédure fabrique le paquet, vérifie son contenu, crée une version provisoire, télécharge tous les fichiers publiés, vérifie à nouveau leurs empreintes, compare la copie distante aux fichiers sources et contrôle le contenu du paquet téléchargé. La version devient publique uniquement si ces opérations aboutissent. Une version mensuelle déjà présente n'est jamais remplacée : la procédure télécharge ses fichiers et les vérifie à nouveau.

La version GitHub n'est **pas soumise au délai de trente jours des artefacts d'exécution**. Elle demeure néanmoins hébergée par GitHub, sur le même fournisseur que le dépôt et les procédures. Son maintien dépend des autorisations, du dépôt et de la politique du service. Une version mensuelle n'est donc **pas** une sauvegarde géographiquement et administrativement indépendante, et GitHub ne garantit pas son immutabilité absolue aux personnes dotées de droits suffisants.

Pour une conservation réellement indépendante, transférer régulièrement le fichier ZIP et son empreinte vers un fournisseur distinct, idéalement avec conservation des versions et protection contre l'effacement. Vérifier l'empreinte calculée par le service de destination ou, mieux, télécharger une copie complète, vérifier `SHA256SUMS.txt` et refaire un essai de restitution. Conserver séparément la révision du code d'indexation permettant de relire les données. Ce transfert extérieur dépend d'un espace et d'autorisations distincts, non encore établis ici.

## Limites et risques conservés

L'inventaire et son contenu sont placés dans le même paquet. Leur cohérence interne est testée ; une preuve externe indépendante demeure nécessaire pour détecter le remplacement simultané du paquet et de son inventaire. Les corrections de l'interface non observées entre deux passages restent inconnues. La restitution ZIP préserve les données et les métadonnées archivées, tandis que le logiciel d'indexation est conservé séparément dans le dépôt source, à la révision indiquée.

La procédure n'extrait aucune donnée privée et n'aspire aucune nouvelle source. Toute extension à d'autres corpus nécessitera des règles de publication, de provenance et de réutilisation propres à leur source.
