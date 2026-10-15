# FRONTIÈRE — Sauvegarde des quatre bases persistantes

Une instance de collecte permanente doit pouvoir être reprise à partir de
copies vérifiées, sans arrêter les collecteurs pour copier directement les
fichiers SQLite.

## Première procédure reproductible

La configuration Docker Compose propose un service ponctuel nommé
sauvegarde, activable avec le profil maintenance. Les quatre volumes
d'acquisition lui sont montés en lecture seule. La commande suivante
est à exécuter sur la machine d'hébergement :

    mkdir -p sauvegardes
    docker compose -f compose.collecte.yml --profile maintenance run --rm sauvegarde

L'outil crée un dossier sauvegardes/frontiere-... contenant les quatre
bases boamp.sqlite3, emplois.sqlite3, decp.sqlite3 et ted.sqlite3, ainsi
que manifest.json avec la date, la taille et l'empreinte SHA-256 de chaque
copie.

Les copies sont produites par sqlite3.Connection.backup. Ce mécanisme
produit un instantané cohérent pour chaque base prise séparément,
même en présence de transactions concurrentes. Il ne constitue pas
un instantané global simultané des quatre bases.

L'outil confirme l'intégrité SQLite et les tables essentielles avant de
publier le manifeste. Une erreur supprime le dossier partiel.

## Vérification indépendante

Depuis la racine du dépôt :

    python3 scripts/sauvegarder_bases.py --verifier sauvegardes/NOM_DU_DOSSIER

La vérification relit les quatre fichiers, calcule leurs empreintes et
vérifie leurs structures et leur intégrité. Elle échoue si une copie est
absente, modifiée ou incompatible.

Le répertoire sauvegardes/ est exclu de Git. Ses contenus ne doivent
pas être publiés dans le dépôt public.

## Périmètre et conservation

**Les originaux bruts ne sont pas inclus dans cette première sauvegarde.**
Cela concerne les fichiers DECP consolidés présents dans le volume partagé,
les derniers relevés JSON conservés par les collecteurs et les archives
enregistrées séparément des bases.

Ces originaux devront être copiés vers un stockage indépendant, puis
soumis à un essai de restauration. Les archives déjà suivies dans Git
ne remplacent pas une sauvegarde de l'intégralité des données en
exploitation.

Copier les bases dans un dossier du même serveur protège contre
certaines défaillances locales, sans protéger contre la perte de
la machine entière. Répliquer les sauvegardes vers un stockage
indépendant et déterminer une durée de conservation adaptée.

## Reprise contrôlée

Avant de remplacer une base de production, arrêter le collecteur qui
écrit sur le volume concerné. Vérifier la copie en environnement isolé,
contrôler les volumes et les recherches représentatives, puis effectuer
le remplacement et relancer le collecteur.

La restauration automatisée sur un serveur actif n'est pas incluse.
Des copies de plusieurs bases prises à des instants différents ne prouvent
pas la cohérence d'éventuelles relations inter-sources au même instant.

La mesure du dernier passage de chaque collecteur et de son taux de
réussite constitue une contribution ultérieure.
