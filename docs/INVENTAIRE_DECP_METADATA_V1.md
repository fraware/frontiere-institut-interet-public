# Inventaire récurrent des données essentielles de la commande publique

**Périmètre : métadonnées de fichiers attribués, pas observations de besoins futurs.**

Les deux catalogues officiels ciblés sont :

- [Fichiers DECP consolidés des ministères économiques](https://www.data.gouv.fr/datasets/donnees-essentielles-de-la-commande-publique-fichiers-consolides), rassemblant différentes sources dont le PES Marché.
- [DECP transmises par la DGFiP via PES Marché depuis 2024](https://www.data.gouv.fr/datasets/donnees-essentielles-de-la-commande-publique-transmises-via-le-pes-marche-depuis-2024), notamment collectivités, établissements publics locaux et établissements publics de santé gérés sous Hélios. Cette source **n'inclut pas les marchés de l'État**.

**Important :** le second catalogue contribue notamment au premier. Additionner leurs fichiers ou observations conduirait à des doubles comptes. Une couverture exhaustive des marchés français n'est attestée pour aucun des deux.

## Traitement livré

Le programme `scripts/collecter_catalogues_decp.py` récupère uniquement les fiches de métadonnées de data.gouv.fr, depuis une liste fermée de deux adresses, sans suivre les URL des fichiers décrits. Il conserve le nombre total de fichiers recensés, les formats, les tailles déclarées, les dates de modification reconnues et l'empreinte SHA-256 de la liste **complète** des métadonnées réduites.

Pour contenir les coûts et éviter d'ajouter plusieurs milliers de fichiers ou métadonnées nominatives au dépôt, il détaille seulement les **150 ressources les plus récemment modifiées** par source, tout en comptant les ressources omises de cette vue. Une empreinte différente signale une **modification d'inventaire**, non une création de marché ni la cause d'une modification.

Aucun fichier massif `decp-global.json` ou `decp-2026.json` n'est téléchargé. La collecte des enregistrements de marchés demandera un traitement **en flux**, un contrôle de schéma sur de vrais extraits, une gestion de reprises et une base persistante externe.

Le registre produit est `institutionnel/decp/etat_ressources.json`. Une source défaillante laisse sa dernière observation réussie en place. Si les deux échouent, la commande s'interrompt sans remplacer son état. Elle ne qualifie aucune demande de compétence.

## Fonctionnement

```bash
python -m pytest -q tests/test_collecter_catalogues_decp.py
python scripts/collecter_catalogues_decp.py
```

La procédure `.github/workflows/catalogues-decp.yml` est programmée **deux fois par jour** et déclenchée à la modification de son programme ou des sources. Son exécution et ses dates effectives dépendent de GitHub Actions. Le registre est proposé dans une branche dédiée et fusionné uniquement lorsque les trois contrôles du dépôt ont réussi sur le commit précis.

## Étape suivante de l'intégration DECP

Télécharger un seul fichier mensuel de taille contrôlée dans un espace externe, vérifier sa structure réelle et ses catégories, puis créer une ingestion en flux avec identifiants composites de marchés et versions. Lier ensuite, avec le BOAMP, les notices de publication, les attributions, les modifications et les entités acheteuses ; préserver les chevauchements plutôt que d'additionner les lignes.

Un **marché attribué** permet de documenter une acquisition de ressources. Il ne prouve ni que la capacité est déjà en exploitation ni qu'un besoin ouvert subsiste.
