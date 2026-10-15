# FRONTIÈRE — Recherche nationale fédérée des quatre corpus publics

Cette étape ajoute un point de consultation commun aux quatre bases
opérationnelles : BOAMP, offres d'emploi de la fonction publique, marchés
attribués DECP et avis européens TED.

## Principe

Le service ouvre chacune des bases SQLite existantes **en lecture seule**.
Il ne recopie pas les données et ne confond pas des objets documentaires
juridiquement différents. Chaque réponse restitue explicitement le type,
l'identifiant, le titre, l'organisme et la date de publication lorsqu'elle
est effectivement connue.

Les marchés attribués incluent le montant hors taxes uniquement s'il
figure dans les sources DECP. Une URL de contrat n'est pas inventée si seul
le fichier consolidé de provenance est connu. Les offres de poste importées
ne possèdent pas nécessairement de date de publication individuelle ;
la date d'observation de leur fichier est conservée dans le registre source,
sans être présentée comme une date de publication de l'offre.

Les résultats DECP utilisent l'index plein texte FTS5 existant. Les autres
bases effectuent une recherche de termes dans les titres ou les organismes,
ainsi que dans les compétences pour les offres d'emploi.

Il ne s'agit pas encore d'une correspondance démontrée entre un appel
d'offres BOAMP, un marché attribué DECP et une publication TED. Les
résultats conservent leur provenance et leur nature.

## Démarrage local avec Docker

Lancer les collecteurs et la consultation :

    docker compose -f compose.collecte.yml up -d --build

La consultation n'est exposée que sur l'interface locale de l'hôte,
au port 8765. Les bases des collecteurs sont montées dans le service
en lecture seule. Pour interroger :

    curl 'http://127.0.0.1:8765/recherche?q=informatique&limite=20'

    curl 'http://127.0.0.1:8765/recherche?q=scientifique&source=boamp,emplois'

    curl 'http://127.0.0.1:8765/sources'

    curl 'http://127.0.0.1:8765/sante'

La réponse indique si chaque source est accessible, non configurée ou
incompatible avec le schéma attendu. L'absence d'une base n'est jamais
interprétée comme l'absence de marchés ou de recrutements.

## Recherche depuis la ligne de commande

    python -m app.recherche_nationale \
      --boamp /tmp/frontiere/avis_boamp.sqlite3 \
      --emplois /tmp/frontiere/offres_emplois.sqlite3 \
      --decp /tmp/frontiere/marches_decp.sqlite3 \
      --ted /tmp/frontiere/avis_ted.sqlite3 \
      rechercher "intelligence artificielle" --limite 30

Les chemins peuvent aussi être renseignés avec les variables
FRONTIERE_BOAMP_DB, FRONTIERE_EMPLOIS_DB, FRONTIERE_DECP_DB
et FRONTIERE_TED_DB.

## Limites à documenter dans les résultats

- Les réponses sont plafonnées à 100 documents, triés par date publiée,
  lorsque cette date est connue. Les offres d'emploi sans date sont
  présentées après les publications datées.
- La recherche textuelle demeure différente selon le moteur existant
  de chaque corpus. La correspondance sémantique et le classement par
  pertinence globale restent à développer.
- Les bases sont accessibles dès leur création effective sur le volume.
  La fusion du code GitHub ne déploie pas de conteneurs.
- Le service ne crée aucun besoin public inféré ni aucun lien contractuel
  qui ne figure pas dans les documents.
- Les requêtes larges sur les bases volumineuses devront être mesurées en
  exploitation ; une indexation de recherche optimisée sur BOAMP, TED
  et emplois publics fait partie des optimisations ultérieures.

## Étapes suivantes

Rassembler les profils d'administrations et leurs identifiants nationaux,
puis rattacher les preuves d'offres, d'achats, de programmes et de budgets
à des entités communes. Les liens entre avis BOAMP/TED et contrats DECP
seront soumis à des règles explicites de correspondance documentaire.
