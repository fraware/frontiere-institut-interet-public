# Recherche locale dans les archives BOAMP vérifiées

## Portée scientifique

Le programme `scripts/rechercher_historique_boamp.py` prépare un **index documentaire local** des métadonnées d'avis du BOAMP déjà collectées. Il ne télécharge aucun avis et ne crée aucun jugement sur une pénurie de compétences, une intervention publique nécessaire, un marché distinct ou une ressource mobilisable.

La provenance des avis est la Direction de l'information légale et administrative (DILA). Chaque ligne provient d'un fichier quotidien dont les deux empreintes SHA-256, la date, le chemin et le nombre d'avis sont vérifiés avant indexation. La correspondance entre une requête et les mots d'un objet de marché ou du nom de l'acheteur est une **piste documentaire**, sans valeur de validation d'un besoin scientifique.

## Préparer l'index

Depuis la racine du dépôt, avec les archives du rattrapage réellement publiées :

```bash
python scripts/rechercher_historique_boamp.py indexer --index /tmp/frontiere-boamp.sqlite3
python scripts/rechercher_historique_boamp.py chercher --index /tmp/frontiere-boamp.sqlite3 --terme "analyse hydrologique"
python scripts/rechercher_historique_boamp.py chercher --index /tmp/frontiere-boamp.sqlite3 --terme "intelligence artificielle" --page 2 --limite 20
```

L'index utilise SQLite et l'indexation textuelle intégrale FTS5. Il est construit dans un fichier temporaire, vérifié, puis remplacé de manière atomique. En cas de corruption d'une archive, l'index antérieur est conservé. Les recherches sont protégées par paramètres SQL et par une normalisation des termes. L'outil n'accède pas au réseau.

La recherche couvre **uniquement** les journées déjà présentes dans le dossier d'archives. Les fichiers arrivés depuis la construction de l'index exigent une nouvelle exécution de `indexer`. Les résultats retournent la date, l'identifiant BOAMP, l'objet, l'acheteur, la catégorie, l'état de l'avis et le lien officiel disponible. Les champs de contact ou d'attribution nominative ne sont pas ajoutés.

## Fabrication automatique et accès au fichier indexé

La procédure `.github/workflows/index-boamp-historique.yml` construit l'index depuis les archives officielles publiées dans la branche principale, lors de l'ajout ou de la modification de ces archives, une fois par jour et sur demande. L'exécution relève les erreurs de fichier, vérifie chaque empreinte et réalise un contrôle de cohérence SQLite avant de publier un artefact temporaire téléchargeable depuis GitHub Actions.

Après la fusion automatique d'une collecte BOAMP, la procédure de collecte demande explicitement une nouvelle fabrication de l'index. Cette demande intervient uniquement à l'issue des trois vérifications et de la publication des archives sur la branche principale. Une indisponibilité temporaire du service de déclenchement laisse subsister la fabrication quotidienne, signalée comme solution de repli. Chaque index porte la révision réelle des archives utilisées, y compris lors des relances.

L'artefact contient le fichier de recherche `index-avis-boamp.sqlite3`, un bilan de construction et une fiche de preuve indiquant la révision exacte du dépôt, les nombres de journées et d'avis, le volume et l'empreinte SHA-256 de l'index. Les fichiers restent accessibles pendant quatorze jours. Ils ne sont pas ajoutés à l'historique Git, afin de maîtriser la croissance du dépôt. En cas d'échec de vérification, la procédure interrompt la publication.

Pour consulter les résultats, télécharger l'artefact d'une exécution réussie puis exécuter la commande `chercher` avec le chemin du fichier SQLite. L'existence d'un fichier d'index téléchargeable ne constitue pas un service en ligne permanent ; le protocole de collecte reste indépendant d'une application publique.

## Limites

Le dépôt contient une archive partielle, initialement huit journées de septembre et octobre 2026. L'index ne constitue ni un relevé exhaustif des marchés français ni une validation causale de la valeur de FRONTIÈRE. Les avis rectificatifs et répétitions éventuelles restent des unités documentaires distinctes. Le contenu archivé correspond à l'interface officielle à la date du relevé, sous réserve des limites de stabilité transactionnelle de cette interface.

Une recherche documentaire productive combine les avis avec les capacités institutionnelles publiées, les résultats de recrutement, les mécanismes publics existants et, lorsque possible, la chronologie d'exécution obtenue auprès de l'organisme compétent. Une correspondance de vocabulaire seule ne constitue aucune preuve de déficit de compétence.
