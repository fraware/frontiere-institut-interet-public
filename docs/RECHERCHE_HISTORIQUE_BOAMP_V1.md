# Recherche locale dans les archives BOAMP vérifiées

## Portée scientifique

Le programme `scripts/rechercher_historique_boamp.py` prépare un **index documentaire local** des métadonnées d'avis du BOAMP déjà collectées. Il ne télécharge aucun avis et ne crée aucun jugement sur une pénurie de compétences, une intervention publique nécessaire, un marché distinct ou une ressource mobilisable.

La provenance des avis est la Direction de l'information légale et administrative (DILA). Chaque ligne provient du dernier relevé intégralement vérifié pour sa journée, initial ou révisé. Les empreintes SHA-256, les dates, les chemins, les volumes et les décomptes des versions conservées sont contrôlés avant indexation. La correspondance entre une requête et les mots d'un objet de marché ou du nom de l'acheteur est une **piste documentaire**, sans valeur de validation d'un besoin scientifique.

## Préparer l'index

Depuis la racine du dépôt, avec les archives du rattrapage réellement publiées :

```bash
python scripts/rechercher_historique_boamp.py indexer --index /tmp/frontiere-boamp.sqlite3
python scripts/rechercher_historique_boamp.py chercher --index /tmp/frontiere-boamp.sqlite3 --terme "analyse hydrologique"
python scripts/rechercher_historique_boamp.py chercher --index /tmp/frontiere-boamp.sqlite3 --terme "intelligence artificielle" --page 2 --limite 20
```

L'index utilise SQLite et l'indexation textuelle intégrale FTS5. Il est construit dans un fichier temporaire, vérifié, puis remplacé de manière atomique. En cas de corruption d'une archive, l'index antérieur est conservé. Les recherches sont protégées par paramètres SQL et par une normalisation des termes. L'outil n'accède pas au réseau.

## Versions successives et recherche

Chaque archive quotidienne conserve le **premier relevé** et sa date. Pour une journée disposant d'un ou plusieurs constats de révision, le constructeur vérifie aussi **toutes** les versions ultérieures, leurs empreintes, leurs volumes, leur rattachement au relevé initial et les identifiants annoncés comme apparus, absents du nouveau relevé ou modifiés. Une correction altérée, orpheline, sans provenance ou présentant deux états divergents au même instant interrompt la construction de l'index.

La recherche textuelle utilise **la version de la journée portant la date de contrôle la plus récente parmi les versions entièrement vérifiées**. Les autres états ne sont pas supprimés : la table `versions` conserve leurs dates, chemins et empreintes. La table `provenance` conserve l'archive initiale, la version retenue et le décompte de toutes les révisions vérifiées. Chaque résultat de recherche indique la source d'archive et l'instant de son relevé. Le bilan distingue les journées indexées, le nombre d'avis issus des versions retenues, les versions corrigées vérifiées et les journées concernées.

Ce choix décrit les **états observés à plusieurs instants** : un identifiant absent du relevé le plus récent n'est pas nécessairement juridiquement supprimé. Une modification transitoire entre deux consultations peut demeurer indétectée. Un cas sans constat de correction conserve son relevé initial comme référence documentaire. Une archive révisée nouvellement publiée impose la reconstruction de l'index.

La recherche couvre **uniquement** les journées déjà présentes dans le dossier d'archives. Les fichiers arrivés depuis la construction de l'index exigent une nouvelle exécution de `indexer`. Les résultats retournent la date, l'identifiant BOAMP, l'objet, l'acheteur, la catégorie, l'état de l'avis et le lien officiel disponible. Les champs de contact ou d'attribution nominative ne sont pas ajoutés.

## Sélection à la dernière observation

Le programme utilise aussi, lorsqu'il existe, l'état documenté par `etat_revisions_boamp.json`. Si un état initial A est suivi d'une correction B, puis d'un retour observé aux octets A, **la recherche retient A à la date du retour**. La version B demeure dans la table des versions. Chaque correspondance signale l'archive effectivement utilisée et la date de contrôle la plus récente enregistrée.

L'empreinte du dernier état doit correspondre à un relevé initial ou à une version corrigée dont l'intégrité a été vérifiée. Une référence vers des octets manquants interrompt la construction. Les corrections observées entre deux consultations successives et déjà disparues au contrôle suivant demeurent hors de la portée documentaire démontrée.

## Fabrication automatique et accès au fichier indexé

La procédure `.github/workflows/index-boamp-historique.yml` construit l'index depuis les archives officielles publiées dans la branche principale, lors de l'ajout ou de la modification de ces archives, une fois par jour et sur demande. L'exécution relève les erreurs de fichier, vérifie chaque empreinte et réalise un contrôle de cohérence SQLite avant de publier un artefact temporaire téléchargeable depuis GitHub Actions.

Après la fusion automatique d'une collecte BOAMP, la procédure de collecte demande explicitement une nouvelle fabrication de l'index. Cette demande intervient uniquement à l'issue des trois vérifications et de la publication des archives sur la branche principale. Une indisponibilité temporaire du service de déclenchement laisse subsister la fabrication quotidienne, signalée comme solution de repli. Chaque index porte la révision réelle des archives utilisées, y compris lors des relances.

L'artefact contient le fichier de recherche `index-avis-boamp.sqlite3`, un bilan de construction et une fiche de preuve indiquant la révision exacte du dépôt, les nombres de journées et d'avis, le volume et l'empreinte SHA-256 de l'index. Les fichiers restent accessibles pendant quatorze jours. Ils ne sont pas ajoutés à l'historique Git, afin de maîtriser la croissance du dépôt. En cas d'échec de vérification, la procédure interrompt la publication.

Pour consulter les résultats, télécharger l'artefact d'une exécution réussie puis exécuter la commande `chercher` avec le chemin du fichier SQLite. L'existence d'un fichier d'index téléchargeable ne constitue pas un service en ligne permanent ; le protocole de collecte reste indépendant d'une application publique.

## Limites

Le dépôt contient une archive partielle, initialement huit journées de septembre et octobre 2026. L'index ne constitue ni un relevé exhaustif des marchés français ni une validation causale de la valeur de FRONTIÈRE. Les avis rectificatifs et répétitions éventuelles restent des unités documentaires distinctes. Le contenu archivé correspond à l'interface officielle à la date du relevé, sous réserve des limites de stabilité transactionnelle de cette interface.

Une recherche documentaire productive combine les avis avec les capacités institutionnelles publiées, les résultats de recrutement, les mécanismes publics existants et, lorsque possible, la chronologie d'exécution obtenue auprès de l'organisme compétent. Une correspondance de vocabulaire seule ne constitue aucune preuve de déficit de compétence.
