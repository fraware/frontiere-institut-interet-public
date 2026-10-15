# FRONTIÈRE — Sauvegardes vérifiables des fichiers sources bruts

Les copies SQLite sauvegardent les avis et les identités déjà indexés.
Les fichiers bruts doivent être archivés **séparément** pour préserver
le contexte de collecte, la possibilité de réimporter les données et
les originaux des fichiers DECP nationaux.

## Sources couvertes

L'utilitaire \`scripts/sauvegarder_sources_brutes.py\` accepte une liste
explicite de répertoires présents sur le disque persistant. Les
principaux répertoires créés par l'instance gérée sont :

- \`/var/lib/frontiere/boamp/releves\`
- \`/var/lib/frontiere/emplois/releves\`
- \`/var/lib/frontiere/decp/releves\`
- \`/var/lib/frontiere/decp/fichiers-consolides\`

## Commandes sur l'hôte d'exploitation

Dans un environnement Python, avec un espace de sauvegarde
physiquement indépendant du disque d'acquisition :

    python -m scripts.sauvegarder_sources_brutes \
      --source boamp=/var/lib/frontiere/boamp/releves \
      --source emplois=/var/lib/frontiere/emplois/releves \
      --source decp=/var/lib/frontiere/decp/releves \
      --source decp_consolides=/var/lib/frontiere/decp/fichiers-consolides \
      --destination /sauvegardes-exterieures

La commande produit une arborescence \`originaux/\` avec tous les
fichiers documentaires admissibles, un manifeste horodaté et une
empreinte SHA-256 pour chaque fichier. Les copies sont réalisées en
blocs d'un mégaoctet. Une modification du fichier d'origine pendant
sa copie conduit à refuser la sauvegarde correspondante.

La vérification indépendante se lance ensuite ainsi :

    python -m scripts.sauvegarder_sources_brutes \
      --verifier /sauvegardes-exterieures/frontiere-bruts-DOSSIER

Elle vérifie l'inventaire complet, les fichiers supplémentaires,
les empreintes, les tailles, et refuse les liens symboliques et les
chemins de traversée de répertoires.

## Limites actuelles

Cet utilitaire est **prêt à être lancé sur un stockage accessible**, sans
création d'un compte de stockage ni synchronisation automatique vers
un fournisseur externe. Un disque Render n'est pas accessible en tant
que volume local depuis cette conversation et aucun hébergement n'a
encore été créé.

Le programme ignore les fichiers temporaires masqués et les bases
SQLite, déjà traitées par leur procédure dédiée. Il refuse les extensions
documentaires inconnues pour éviter de présenter une couverture incomplète
comme une sauvegarde exhaustive.

L'absence d'un répertoire déclaré empêche la sauvegarde. Le programme
ne garantit pas un instantané simultané de plusieurs répertoires modifiés
en continu ; chaque fichier est contrôlé séparément. Une campagne
de restauration sur machine distincte devra être effectuée avant de
considérer l'ensemble résilient à la perte du service.

La prochaine évolution est une destination de stockage d'objets
indépendante de Render avec conservation des versions et reprise
des transferts volumineux.
