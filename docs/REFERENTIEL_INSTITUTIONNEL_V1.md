# Référentiel institutionnel vivant — version 1

## Finalité

FRONTIÈRE maintient une représentation à jour et traçable des organismes publics utiles à la recherche de capacités scientifiques et techniques.

Ce référentiel doit répondre à des questions concrètes :

- quelle institution est compétente pour un sujet ;
- de quelle autorité dépend-elle ;
- quels services, opérateurs, établissements ou laboratoires lui sont rattachés ;
- quel territoire couvre-t-elle ;
- quels responsables occupent les fonctions pertinentes ;
- quelles capacités scientifiques ou techniques sont documentées ;
- quels textes fondent son existence ou ses compétences ;
- quels changements récents peuvent modifier la réponse ;
- comment contacter ou mobiliser la ressource pertinente.

Il s’agit d’un réseau d’organisations, de territoires et de relations sourcées, et pas d’un simple annuaire.

## Ce que signifie « couvert »

FRONTIÈRE ne prétend pas représenter une fois pour toutes l’intégralité du secteur public français.

La couverture est mesurée par périmètre. Pour chaque famille d’organisations, le dépôt indique la source officielle utilisée, la date de dernière observation, le nombre d’objets importés, les identifiants ou relations qui restent non résolus, les sources en erreur ou trop anciennes et les changements qui demandent une validation humaine.

Une information inconnue reste explicitement inconnue.

## Périmètre

Le référentiel couvre progressivement :

1. institutions constitutionnelles et Gouvernement ;
2. administration centrale de l’État ;
3. administration territoriale de l’État ;
4. autorités administratives et publiques indépendantes ;
5. opérateurs et établissements publics ;
6. collectivités territoriales et groupements intercommunaux ;
7. santé et secteur médico-social public ;
8. enseignement supérieur et recherche publique ;
9. justice et juridictions ;
10. réseau diplomatique et implantations publiques à l’étranger ;
11. entreprises et participations liées à l’État lorsqu’elles sont pertinentes pour une capacité publique.

## Sources déjà intégrées

Le premier socle est le **Référentiel de l’organisation administrative de l’État**, publié par la Direction de l’information légale et administrative. L’état observé le 7 octobre 2026 contient **7 905 services ou organismes** et **8 073 relations hiérarchiques résolues**.

Le deuxième socle est l’**Annuaire de l’administration**, également publié par la Direction de l’information légale et administrative. Le même cycle d’observation contient **85 877 services et guichets locaux**. Les deux importations couvrent ensemble les **93 782 enregistrements** de l’export courant de l’Annuaire.

La DILA publie aussi un jeu de compétence géographique qui relie des communes à des types de services compétents. Ce jeu, beaucoup plus volumineux, est interrogé directement auprès de la source au moment d’une recherche territoriale.

Le troisième socle est le **Code officiel géographique de l’Insee**, qui fournit l’identité des communes, départements, régions et autres unités territoriales. Les territoires restent séparés des organisations qui les administrent.

Le registre complet des sources prévues figure dans `institutionnel/sources_v1.json`.

## Modèle d’une organisation

Chaque organisation reçoit un identifiant technique stable. Sa représentation normalisée peut contenir son identité, ses identifiants officiels, sa position institutionnelle, ses missions, ses responsables, ses capacités documentées, ses coordonnées, ses textes de référence et les ressources budgétaires disponibles.

Une mission, un responsable ou une capacité n’est enregistré comme fait que s’il possède une source. Une capacité déduite par analyse reste distincte d’une capacité explicitement documentée.

## Relations

Les relations techniques ont des noms stables dans les fichiers. La documentation les présente par leur sens.

| Sens | Identifiant technique |
| --- | --- |
| dépend d’une organisation | `DEPEND_DE` |
| est sous la tutelle d’une organisation | `TUTELLE_DE` |
| est financé par | `FINANCE` |
| est contrôlé par | `CONTROLE` |
| est dirigé par | `DIRIGE` |
| est compétent sur un territoire | `COMPETENT_SUR` |
| est implanté dans un territoire | `IMPLANTE_DANS` |
| succède à | `SUCCEDE_A` |
| coopère avec | `COOPERE_AVEC` |
| détient une capacité | `DETIENT_CAPACITE` |

Chaque relation conserve une source et une date d’observation.

## Dates

FRONTIÈRE distingue deux questions : à quelle période l’information était-elle vraie, et à quelle date FRONTIÈRE l’a-t-il observée ou vérifiée ?

Les noms techniques `valide_depuis`, `valide_jusqua` et `observe_le` servent uniquement à représenter cette distinction dans les fichiers.

## Résolution d’identité

Le même organisme peut apparaître sous plusieurs noms ou dans plusieurs sources.

L’ordre de confiance est le suivant :

1. identifiant officiel stable partagé ;
2. SIREN ou SIRET ;
3. autre identifiant sectoriel officiel ;
4. correspondance explicitement publiée par une source ;
5. rapprochement par nom, adresse et autorité de rattachement ;
6. validation humaine dès qu’une ambiguïté subsiste.

Deux organisations ne sont jamais fusionnées sur la seule similarité de leur nom.

## Provenance

Chaque fait important doit pouvoir être relié à sa source. Le minimum attendu comprend l’adresse de la ressource, la date de collecte, l’identifiant de l’objet dans la source et, lorsque cela est possible, une empreinte du contenu.

## Organisation du répertoire

```text
institutionnel/
  README.md
  sources_v1.json
  schema_entite_v1.json
  schema_relation_v1.json
  couverture_cible_v1.json
  etat_sources.json
  alertes_sources.json
  entites/
  relations/
  evenements/
  instantanes/
```

Les gros fichiers bruts des producteurs publics ne sont pas copiés quotidiennement dans Git. Le dépôt conserve les informations nécessaires pour vérifier la provenance et reconstruire les représentations normalisées.

## Surveillance

Les sources n’évoluent pas toutes au même rythme. Les sources administratives fréquemment mises à jour sont vérifiées quotidiennement ; les sources annuelles sont vérifiées lors de leur publication et périodiquement pour détecter une correction.

Le programme `scripts/surveiller_sources_institutionnelles.py` enregistre l’état des sources et les alertes correspondantes.

## Mesurer la qualité

La qualité du référentiel ne se résume pas au nombre d’objets. Les mesures utiles comprennent notamment la part des organisations avec identifiant stable, parent institutionnel résolu, territoire résolu, mission sourcée, responsable sourcé et texte juridique, ainsi que la fraîcheur des sources et le nombre d’ambiguïtés restantes.

## Utilisation dans un cas

Lorsqu’un besoin est enregistré, FRONTIÈRE commence par chercher les capacités déjà présentes dans le secteur public. Le référentiel aide à identifier les institutions compétentes, les services ou laboratoires pertinents, les voies de coopération ou de mobilité et les personnes ou services à contacter.

Le résultat attendu est une carte vérifiable des ressources publiques et des chemins permettant de les mobiliser.

## Critère de réussite de la version 1

La version 1 est suffisamment solide lorsque les sources critiques sont surveillées, la couverture est mesurée, l’organisation de l’État et les services locaux sont importés, les territoires sont reliés de manière fiable et chaque fait important conserve sa provenance.

Les extensions suivantes doivent être choisies à partir des besoins observés dans les cas réels, et non pour augmenter le volume du référentiel.
