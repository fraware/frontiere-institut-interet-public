# Épisodes comparables de mobilisation scientifique et technique — SICTIAM et Sicoval

**Corpus pilote du 14 octobre 2026.** Ce registre met en relation quatre épisodes documentaires sans les fusionner : le système d'acquisition dynamique de solutions d'intelligence artificielle du SICTIAM, une délibération intercommunale du Sicoval, l'expérimentation déclarée à Escalquens et les usages rapportés à Auzeville-Tolosane.

Le registre structuré est [`donnees/episodes_mobilisation_preuves_v1.json`](../donnees/episodes_mobilisation_preuves_v1.json). Chaque événement porte une catégorie administrative, une date de précision journalière ou annuelle, une référence documentaire et un numéro de page pour les PDF. L'outil [`scripts/valider_episodes_mobilisation.py`](../scripts/valider_episodes_mobilisation.py) vérifie les données hors réseau. Sa sortie est un bilan dérivé, pas une transcription des sources originales.

## Résultats établis et interdictions d'inférence

| Épisode distinct | Événement observé | Preuve retenue | Première utilité datée |
| --- | --- | --- | --- |
| SICTIAM — dispositif et marchés spécifiques d'IA | Choix déclarés des titulaires les 23 janvier et 23 février 2026 ; conclusion des contrats le 20 mars 2026 | Avis officiel BOAMP n° `26-43435`, pages 9 à 11 | **Inconnue** |
| Sicoval — convention Delibia | Délibération `SB2025024` du 18 février 2025, publiée le 20 février | Registre public des délibérations intercommunales ; texte intégral de l'acte non récupéré | **Inconnue** |
| Escalquens — proposition de poursuite | Essai décrit rétrospectivement pour 2024 ; décision communale du 13 février 2025 | Document municipal, PDF dont l'empreinte SHA-256 a été enregistrée ; date exacte de l'essai inconnue | **Inconnue** |
| Auzeville-Tolosane — témoignage d'usage | Déclaration en conseil municipal le 18 juin 2025 sur la préparation de délibérations | Procès-verbal communal empreinté ; **date du témoignage**, distincte de la première utilisation | **Inconnue** |

Les deux PDF municipaux sont liés aux empreintes réellement relevées dans [`institutionnel/pieces_publiques/observations_pdfs_municipaux.json`](../institutionnel/pieces_publiques/observations_pdfs_municipaux.json). Les pièces du SICTIAM ont une référence officielle mais **aucune empreinte d'octets conservée dans ce registre**. La validation refuse l'attribution d'une empreinte fictive et compare les numéros de pages des PDF communaux avec le fichier réellement reçu.

Le même SIREN `908039142` apparaît dans les quatre épisodes comme identité de Solyne / Delibia dans le périmètre étudié. Cette récurrence identifie un fournisseur commun. **Aucune relation contractuelle entre le SICTIAM et les marchés des communes via le Sicoval n'est démontrée.**

## Dates administratives calculables

Pour les titulaires des marchés spécifiques du SICTIAM, le relevé établit **56 jours entre le choix déclaré de TOMORRO (23 janvier) et la conclusion déclarée (20 mars)** et **25 jours entre le choix déclaré des trois autres titulaires (23 février) et le 20 mars**. Ces calculs sont effectués par soustraction de dates du même épisode et sont vérifiés par les essais automatiques. Ils décrivent des jalons de passation, ni la durée d'exécution ni le délai besoin → première contribution utile.

Le résultat de la validation pour ce corpus doit indiquer **zéro** date de première contribution utile exactement établie et **zéro** mesure indépendante d'effet. Ces zéros représentent l'état du corpus de quatre épisodes, jamais la preuve qu'aucune utilisation n'a eu lieu. Une information d'usage en production rapportée par un responsable municipal constitue un témoignage opérationnel, non une mesure chronométrée.

## Exploitation ultérieure sans intervention humaine

La procédure de validation et ses tests peuvent être lancés à chaque changement des événements, des sources ou des empreintes des PDF. La prochaine extension empirique devrait rechercher les pièces primaires de commande, les dates de mise en service, les évaluations d'expérience et les comparateurs institutionnels existants. Chaque élargissement doit annoncer explicitement une nouvelle version de corpus ou de schéma. Un résultat statistique sur les quatre épisodes ne permet aucune généralisation nationale.

**Commandes :**

```bash
python scripts/valider_episodes_mobilisation.py
python -m pytest -q tests/test_valider_episodes_mobilisation.py
```

Ce dispositif reste un instrument de recherche documentaire, distinct d'un système d'attribution causale ou de justification de la création institutionnelle de FRONTIÈRE.
