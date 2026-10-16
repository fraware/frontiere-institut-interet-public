# FRONTIÈRE — Recherche intégrale sur les recrutements publics archivés

## Pourquoi ce moteur

L'index du site public n'expose que cinq mille offres de recrutement.
L'instantané archivé « Choisir le service public » du 12 octobre 2026
compte **268 102 variantes de documents**, associées à **266 139
références distinctes**, selon le manifeste officiel d'extraction.
Ces effectifs concernent l'instantané local ; ils ne constituent ni un
nombre de postes encore vacants ni une couverture nationale complète.

Le programme local scripts/indexer_recrutements_nationaux_sqlite.py
construit un index SQLite avec recherche textuelle FTS5 sur **toutes
les variantes effectivement conservées** dans les seize partitions.
Il ne dépend d'aucun serveur, service payant ou appel au producteur de
données. L'objectif est de retrouver les documents anciens et les
différentes versions d'une annonce tout en conservant leur preuve.

## Structure

La base locale comporte quatre tables :

- offres : une ligne par variante archivale, avec référence,
  empreinte d'enregistrement, intitulé, entité déclarée, métier,
  spécialisation, date et nature de la date indexée, éventuelle fin
  déclarée de publication, chemin de partition, numéro de ligne et
  SHA-256 de la ligne originale ;
- references_offres : chaque référence et son nombre total de
  variantes, sans assimilation à des postes différents ;
- recherche_fts : index plein texte sur les seuls intitulé, entité,
  métier et spécialisation admissibles ;
- meta : version et empreintes de la population indexée.

Les champs libres de compétences attendues ne sont pas recopiés dans
ce moteur, car ils peuvent être longs et contenir des données de
contact. Les champs textuels indexés sont bornés et filtrés contre
les courriels, liens et numéros de téléphone détectables. Ce filtre
est une précaution technique et ne constitue pas un diagnostic
exhaustif de confidentialité.

L'index reste volontairement une **projection des documents** et
n'essaie pas de qualifier une pénurie, un recrutement réalisé ou une
mission à attribuer.

## Construction et intégrité

Le programme vérifie successivement :

1. la structure du manifeste et les 16 empreintes SHA-256 ;
2. la syntaxe de chaque ligne JSONL et le nombre de variantes ;
3. la partition calculée sur la référence déclarée ;
4. l'empreinte canonique de **chaque version d'annonce** à partir
   de sa projection JSON, afin qu'une simple modification du contenu
   accompagnée d'un nouveau SHA-256 de fichier soit détectée ;
5. les nombres totaux de références distinctes et multivariantes ;
6. l'intégrité SQLite et l'index FTS5.

La base est construite hors du dépôt dans un fichier temporaire.
Toute anomalie interrompt la construction. Une base existante n'est
remplacée, sur demande explicite, qu'une fois toute la nouvelle base
validée. La reconstruction ne modifie jamais les partitions sources.

## Commandes

Python 3.11 ou ultérieur et SQLite avec FTS5 :

```sh
python -m scripts.indexer_recrutements_nationaux_sqlite construire \
  --base /tmp/frontiere-recrutements.sqlite3

python -m scripts.indexer_recrutements_nationaux_sqlite bilan \
  --base /tmp/frontiere-recrutements.sqlite3

python -m scripts.indexer_recrutements_nationaux_sqlite rechercher \
  --base /tmp/frontiere-recrutements.sqlite3 \
  --expression "économétrie"

python -m scripts.indexer_recrutements_nationaux_sqlite rechercher \
  --base /tmp/frontiere-recrutements.sqlite3 \
  --expression "ingénieur données" \
  --depuis 2026-01-01 --jusqua 2026-10-15 --limite 30

python -m scripts.indexer_recrutements_nationaux_sqlite rechercher \
  --base /tmp/frontiere-recrutements.sqlite3 \
  --reference 2026-2344611

python -m pytest -q tests/test_indexer_recrutements_nationaux_sqlite.py
```

Les mots de l'expression sont traités comme des **termes littéraux**,
combinés avec une condition de présence commune, sans exécuter
d'opérateurs de requête transmis par l'utilisateur. Les requêtes SQL
utilisent uniquement des paramètres. Les résultats sont regroupés par
référence à partir des variantes qui correspondent aux critères,
avec un nombre de variantes correspondantes et un décompte indépendant
de toutes les variantes archivées de la référence. L'ordre des
résultats reprend la date documentaire puis la référence, sans
affirmer la fraîcheur ou la vacance du poste.

Une date d'index peut correspondre à une première publication, un
début de publication ou, faute de mieux, à une date de vacance
déclarée ; le moteur renvoie **nature_date** avec chaque résultat
pour ne pas confondre ces horodatages.

## Publication et coûts

La procédure GitHub
.github/workflows/index-recrutements-integraux.yml
reconstruit la base à partir du même instantané et publie pour
**quatorze jours** une archive comprenant la base SQLite, son bilan
et leurs empreintes. Ce fichier n'est pas ajouté au dépôt ni au site
Render, et aucune ressource persistante supplémentaire n'est créée.

La vérification générale du dépôt exécute également le moteur sur
les archives réelles. Son coût est celui des minutes et du stockage
temporaires de GitHub Actions déjà utilisés pour les validations ;
aucune modification d'abonnement ou de forfait n'est effectuée.

## Limites et suite technique

Le périmètre indexé est **l'instantané CSP conservé**, distinct de
la population nationale réelle et des offres en cours. Les variantes
supplémentaires d'une référence ne démontrent pas des recrutements
distincts. La recherche textuelle n'est pas une classification
sémantique et ne mesure aucune compétence manquante.

Cette base permet de réaliser des interrogations auparavant
impossibles dans le plafond des cinq mille annonces, et constitue
une première composante d'une architecture multi-source plus vaste.
Les étapes suivantes, à instruire par leurs performances mesurées,
sont l'indexation intégrale des archives BOAMP et des attributions
DECP, la recherche fédérée sur identifiants exacts, puis l'accès
public à un index plus large avec chargement et pagination bornés.
Toute extension doit conserver l'identité documentaire et la
provenance de chaque famille de sources.
