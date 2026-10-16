# FRONTIÈRE — Recherche intégrale BOAMP–DECP dans SQLite

## Ce qui a été construit

Le nouveau programme scripts/indexer_commande_publique_sqlite.py reprend
l'index contractuel existant et lui ajoute les archives BOAMP, dans une
base unique et locale, indexée avec SQLite FTS5.

Périmètre du corpus utilisé : **5 196 avis BOAMP**, **5 946 attestations
contractuelles DECP**, **5 643 identités de marché**, **5 665 variantes
documentaires**, et **47 fichiers sources AIFE/DGFiP**. Ce sont les
effectifs des relevés archivés, sans revendication de couverture nationale.

## Invariants de provenance et d'identité

L'index DECP réutilise scripts/consolider_attributions_decp.py : il distingue
les identités (SIRET acheteur, numéro de marché), leurs variantes, les
attestations et les fichiers sources. Les reprises de mêmes données ne
créent ni nouveaux marchés ni avenants contractuels supposés.

Le BOAMP conserve chaque avis individuellement par son numéro officiel,
son texte déclaré, son acheteur, sa date de parution, sa catégorie,
son échéance si déclarée et son état exact (initial, rectificatif,
modification, annulation). Une échéance n'établit pas le statut actuel
d'une consultation.

Les avis BOAMP dépourvus de SIRET proprement attesté ne sont jamais
rattachés automatiquement à un acheteur DECP par similitude de nom
ou d'objet. La consultation intersources ne démontre aucune identité
contractuelle ni besoin public non satisfait.

## Reconstruction et contrôles

La construction s'effectue sans réseau, dans un dossier temporaire.
Elle refuse les fichiers incomplets, les formats inattendus, les avis
BOAMP répétés, les URL non officielles, les dates impossibles et les
contradictions avec le bilan DECP déjà archivé. Les trois empreintes
SHA-256 des fichiers sources sont incluses dans la base.

Les index textuels, les clés étrangères, l'intégrité SQLite et les
décomptes d'identités/variantes sont contrôlés avant publication
atomique. Une base existante reste inchangée si la reconstruction
échoue. L'option --remplacer autorise explicitement une nouvelle version.

## Utilisation (Python 3.11+, SQLite FTS5)

    python -m scripts.indexer_commande_publique_sqlite construire --base /tmp/commande.sqlite3
    python -m scripts.indexer_commande_publique_sqlite bilan --base /tmp/commande.sqlite3
    python -m scripts.indexer_commande_publique_sqlite rechercher --base /tmp/commande.sqlite3 --expression "quantique"
    python -m scripts.indexer_commande_publique_sqlite rechercher --base /tmp/commande.sqlite3 --identifiant 26-100001
    python -m scripts.indexer_commande_publique_sqlite rechercher --base /tmp/commande.sqlite3 --siret 21590271900016
    python -m scripts.indexer_commande_publique_sqlite rechercher --base /tmp/commande.sqlite3 --source decp --identifiant 21590271900016/2025026000000000
    python -m pytest -q tests/test_indexer_commande_publique_sqlite.py

Le texte est interrogé par mots littéraux, les paramètres SQL sont
bornés et les dates sont distinctes selon la provenance. Les résultats
sont paginés par 100 au maximum. Le nombre total d'identités et la
sélection effective sont conservés séparément.

## Étape suivante

Cette étape ne modifie pas le site Render : la consultation porte sur
une base SQLite locale, indépendante de l'hébergement. GitHub produira
un artefact téléchargeable temporaire avec bilan et empreintes SHA-256.

La prochaine extension concerne la fédération de ce moteur documentaire
avec l'index intégral des 268 102 variantes de recrutement CSP, puis
un accès public paginé évitant de transférer toute la base au navigateur.
