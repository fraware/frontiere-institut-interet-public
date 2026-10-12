# Index local des publications publiques — SQLite FTS5

## Objet et périmètre

Les relevés RSS, Atom et Bluesky déjà publiés dans `institutionnel/flux_publics/observations.json` forment un fichier de collecte versionné. Cet instrument propose une **projection locale SQLite interrogeable** de ces observations. Il ne remplace ni les fichiers sources, ni les bases de cas d'exécution, ni les historiques BOAMP et Choisir le service public.

L'index couvre actuellement uniquement les publications du collecteur multisource. Il n'introduit aucune conclusion automatique sur l'existence, l'importance, le financement ou l'urgence d'un besoin public. L'unité est la **publication**, non la mission.

## Exécution hors réseau

Précondition : Python 3.11 ou ultérieur et module standard `sqlite3` compilé avec FTS5 (disponible sur les versions habituelles de Python distribuées par GitHub Actions).

```bash
python scripts/indexer_signaux_publics_sqlite.py importer \
  --base /tmp/frontiere-signaux.sqlite3

python scripts/indexer_signaux_publics_sqlite.py rechercher \
  --base /tmp/frontiere-signaux.sqlite3 \
  --expression "intelligence artificielle" \
  --limite 30

python scripts/indexer_signaux_publics_sqlite.py rechercher \
  --base /tmp/frontiere-signaux.sqlite3 \
  --expression "recherche" \
  --source anr_appels \
  --limite 20

python -m pytest -q tests/test_indexer_signaux_publics_sqlite.py
```

Le chemin `--base` est **extérieur au dépôt**, de sorte que le fichier SQLite ne soit pas publié accidentellement. Les chemins des sources peuvent être changés explicitement par `--catalogue` et `--observations`.

## Modèle de données

- `sources` — identifiants, nature et catégories des canaux officiels.
- `publications` — identifiant stable, texte normalisé, lien public, date de publication éventuellement inconnue, premier et dernier instant d'observation, empreinte de contenu, nombre de modifications.
- `versions_observees` — première observation locale de chaque version de contenu effectivement reçue. Une version disparue entre deux relevés est inconnue.
- `recherche_fts` — index plein texte Unicode FTS5, sensible aux termes recherchés, sans prétention de compréhension sémantique.

L'importation est transactionnelle et idempotente. Les entrées qui disparaissent d'un flux distant ne sont pas supprimées automatiquement. Une ancienne version ne peut remplacer une version plus récente déjà observée. Une source inconnue, une date erronée, un doublon, une modification hors ordre ou un classement abusif comme mission établie interrompt l'importation.

La recherche accepte une expression littérale bornée et, facultativement, un identifiant de source. Son ordre utilise la date de publication connue, sinon la date de première observation. Ce critère est un ordre documentaire, **pas une date de création du besoin**.

## Limites de la première version

Il s'agit d'une **base locale reproductible**, et non d'une base partagée, hébergée, continuellement disponible ou alimentée directement par l'ensemble des administrations. Les données de syndication ne couvrent pas tous les messages historiques, et les liens et dates manquants restent inconnus.

L'étape suivante à grande échelle est de séparer les trois plans :

1. acquisition continue et conservation du contenu brut lorsque la licence et la portée le permettent ;
2. historique des publications normalisées, avec identités intersources et rapprochements vers les organismes du référentiel ;
3. base d'événements et de besoins, alimentée uniquement par des faits qui documentent réellement une mission ou un problème.

Un service de données persistant et une interface de consultation seront étudiés à partir de mesures réelles de volume, de retard, de fraîcheur et de fréquence des changements. Le fichier SQLite constitue la première capacité de requête locale, sans hébergement permanent.

## Interprétation scientifique

Deux publications provenant de deux comptes officiels différents peuvent désigner une seule initiative. L'index les maintient séparées, car leur identité documentaire et leur date d'observation diffèrent. La fusion des besoins en entités canoniques exige un rapprochement explicite des programmes, financeurs, organismes, périodes et documents.

Les requêtes textuelles sont des outils de repérage. Leurs résultats ne constituent pas des jugements établissant un déficit de capacité.
