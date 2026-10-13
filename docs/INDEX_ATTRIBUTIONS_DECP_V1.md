# Index local des attributions DECP — marchés et versions documentaires

## Point de départ empirique

La première sonde réelle de l'API de données essentielles de la commande publique de l'Agence pour l'informatique financière de l'État a examiné la ressource `db50f1f1-9fe5-4f9e-93dd-d273617d4a26`, publiée dans le [catalogue national](https://www.data.gouv.fr/datasets/api-decp).

Le fichier `decp-13102026-068-0130.json` a produit **127 notices de marchés normalisées**, une concession conservée dans un décompte séparé et aucun rejet. La première sortie du programme ne conservait toutefois que **50 notices sur 127**.

Cette révision relève à **200 notices** le plafond de l'extrait publié. Le programme refuse toute supposition de complétude lorsque `extraits_plafonnes=true`. Ainsi, si un futur fichier comporte plus de 200 marchés, l'indexation locale déclarée complète est interrompue jusqu'à ce que le plafond soit adapté, ou qu'une base persistante ingère directement le fichier intégral.

Les documents du catalogue peuvent comprendre des marchés notifiés bien avant la date du relevé. Une publication le 13 octobre 2026 n'est donc pas une preuve de 127 **nouveaux marchés** ce jour-là.

## Base locale indépendante

Le programme `scripts/indexer_attributions_decp_sqlite.py` matérialise les enregistrements dans SQLite, sans les confondre avec les épisodes de demandes de FRONTIÈRE.

Les tables distinctes conservent :

- **Identités de marchés** : couple `acheteur_siret`, `id_marche`. Le même identifiant interne chez deux acheteurs correspond à deux identités distinctes.
- **Versions normalisées** : empreinte SHA-256 de la notice, objet, code CPV, date de notification et montant déclaré. Les versions anciennes ne sont pas effacées.
- **Fichiers sources** : catalogue, identifiant de ressource et empreinte du fichier brut. Deux fichiers de même contenu publiés comme ressources différentes gardent deux provenances.
- **Attestations** : relation entre une version de marché et un fichier effectivement relevé.
- **Index textuel** : recherche dans les objets des marchés, avec consultation de la date, du CPV, du SIRET de l'acheteur et du nombre de fichiers attestant la version.

Les insertions sont transactionnelles et répétables. Importer une deuxième fois le même relevé ne crée pas de nouvelles versions. Une description différente sous la même identité de marché est conservée comme une autre version, sans décision automatique sur laquelle doit être considérée comme contractuellement en vigueur.

## Reproduction hors réseau

```bash
python scripts/indexer_attributions_decp_sqlite.py importer \
  --base /tmp/frontiere-attributions.sqlite3 \
  --releve institutionnel/decp/sonde_aife_json.json

python scripts/indexer_attributions_decp_sqlite.py rechercher \
  --base /tmp/frontiere-attributions.sqlite3 \
  --expression "recherche"

python -m pytest -q tests/test_indexer_attributions_decp_sqlite.py
```

Le fichier SQLite est créé dans l'espace local choisi ; il n'est pas publié dans le dépôt. L'exécution exige une version de Python disposant de SQLite et de son module de recherche plein texte FTS5.

## Limites

Cet index ne contient actuellement que les enregistrements **effectivement conservés** par la sonde JSON AIFE. Il ne représente pas les 1 747 fichiers du catalogue AIFE, les 5 333 ressources du PES Marché, ni les fichiers consolidés ministériels.

Aucun lien BOAMP n'est déclaré vérifié. Le fichier BOAMP de suivi courant contient un identifiant d'avis, le nom de l'acheteur et l'objet du marché, mais pas systématiquement le SIRET ni l'identifiant contractuel. Le rapprochement devra exploiter les éléments normalisés de l'avis intégral et distinguer correspondances exactes, liens candidats et absences d'identification.

La base décrit des **attributions documentées**. Une attribution ne constitue pas une demande encore ouverte, une preuve de recrutement ni la date de première contribution utile d'une compétence.
