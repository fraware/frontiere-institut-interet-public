# FRONTIÈRE — Collecte permanente des données essentielles de la commande publique

**Première intégration AIFE/DGFiP dans l'infrastructure persistante.**
Ce module est un service logiciel prévu pour un serveur. Il ne prouve ni un
hébergement déjà actif ni la couverture intégrale des DECP.

## Réemploi des travaux existants

Le service app.collecteur_decp_continu prolonge les modules du dépôt :

- scripts.collecter_catalogues_decp pour les trois catalogues officiels ;
- scripts.sonder_ressource_decp_aife pour les petits fichiers JSON AIFE ;
- scripts.sonder_lot_decp_dgfip pour les fichiers XML DGFiP sélectionnés ;
- scripts.indexer_attributions_decp_sqlite pour les identités, versions,
  provenances et recherches textuelles ;
- scripts.consolider_attributions_decp.rapports_dgfip pour l'intégration
  de chaque fichier XML au format de rapport existant.

Les données sont conservées dans une base SQLite sur un volume privé du
service. Les relevés successifs sont conservés comme fichiers JSON sur ce
même volume. Les archives déjà présentes sont importées au démarrage.

## Périmètre déjà documenté

Le bilan versionné du 14 octobre 2026 recense 47 fichiers analysés,
5 946 enregistrements documentaires, 5 643 marchés distincts suivant
le couple SIRET acheteur / identifiant de marché et 5 665 variantes.
Ces chiffres décrivent un corpus borné, non tous les contrats publics.

Les collecteurs AIFE et DGFiP existants limitent le volume des fichiers
admissibles. Le premier interroge une ressource JSON sélectionnée ; le
second traite au plus quatre ressources XML par cycle. Le traitement des
fichiers consolidés nationaux de grande taille reste un chantier distinct.

## Démarrer les trois services

    docker compose -f compose.collecte.yml up -d --build

Le service DECP est ajouté aux services BOAMP et emplois publics.
Son volume SQLite est indépendant ; la collecte des catalogues est
programmée toutes les six heures par défaut. La source des archives
est montée en lecture seule depuis institutionnel/decp.

Aucune proposition de fusion GitHub n'est nécessaire pour enregistrer
une nouvelle observation dans le stockage permanent du service.

## Exécution locale

Depuis la racine du dépôt, après installation des dépendances :

    python -m app.collecteur_decp_continu --base /tmp/frontiere-decp/marches.sqlite3 --repertoire /tmp/frontiere-decp/observations --archives institutionnel/decp amorcer

    python -m app.collecteur_decp_continu --base /tmp/frontiere-decp/marches.sqlite3 --repertoire /tmp/frontiere-decp/observations --config institutionnel/decp/sources_v1.json collecter

    python -m app.collecteur_decp_continu --base /tmp/frontiere-decp/marches.sqlite3 --repertoire /tmp/frontiere-decp/observations etat

    python -m app.collecteur_decp_continu --base /tmp/frontiere-decp/marches.sqlite3 --repertoire /tmp/frontiere-decp/observations rechercher "analyse scientifique" --limite 20

L'amorçage est relançable sans doublon. L'état local plus récent prime sur
le relevé historique, même si la base SQLite a été reconstruite.

## Limites

La surveillance porte sur les trois catalogues de métadonnées, tandis que
l'importation détaillée du nouveau service se limite aux fichiers compatibles
avec les extracteurs bornés AIFE et DGFiP. Une anomalie d'une source conserve
son dernier relevé et laisse la collecte des autres sources poursuivre.

Les variantes ne sont pas qualifiées d'avenants contractuels. Une attribution
ne prouve aucun besoin encore ouvert. Aucun nouveau rapprochement BOAMP–DECP
n'est réputé démontré.

L'actualisation de ressources anciennes sans modification de leurs
métadonnées officielles, les fichiers nationaux volumineux et TED sont les
trois développements d'acquisition suivants.

La fraîcheur réelle doit être mesurée sur un service hébergé : une image
de conteneur construite et des tests réussis ne prouvent pas une collecte
opérationnelle 24 heures sur 24.
