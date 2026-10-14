# Captures mensuelles des pièces municipales originales — Escalquens et Auzeville-Tolosane

## Objet

Cette procédure complète [l'étude Sicoval–Delibia](ENQUETE_SICOVAL_DELIBIA_USAGES_MUNICIPAUX_2026_10_14.md) par un contrôle **des octets de deux PDF primaires** publiés sur des domaines municipaux. Elle remédie à une limite de l'enquête initiale, fondée sur la lecture des textes de documents sans récupération locale de leurs fichiers exacts.

Les deux adresses sont fixées dans `institutionnel/pieces_publiques/sources_pdfs_municipaux_v1.json` :

- Escalquens, délibérations du 13 février 2025, https://www.escalquens.fr/wp-content/uploads/2025/02/D%C3%A9lib%C3%A9rations-CM-2025-02-13.pdf.
- Auzeville-Tolosane, procès-verbal du 18 juin 2025, https://www.auzeville.fr/wp-content/uploads/2025/06/PV-18-06-25.pdf.

Le programme `scripts/relever_pdfs_municipaux.py` vérifie la concordance exacte de ces URL, refuse les redirections et limite chaque fichier à 15 millions d'octets. Il vérifie les signatures de début et de fin du PDF, puis utilise la bibliothèque `pypdf` pour compter les pages et rechercher **des expressions déterminées à l'avance**, notamment « Delibia », « Sicoval » et « service juridique ».

## Résultats conservés

`institutionnel/pieces_publiques/observations_pdfs_municipaux.json` contient, par document :

- l'identité de la commune, la date et le repère administratif annoncé ;
- l'adresse officielle exacte, la taille et l'empreinte SHA-256 du PDF récupéré ;
- le nombre de pages et le nombre de pages contenant du texte exploitable ;
- les numéros de pages où les expressions de recherche sont présentes ;
- la date du premier relevé de cette version des octets, et les erreurs éventuelles de nouvelle collecte.

**Aucun PDF brut et aucun texte libre extrait des pages n'est publié dans le dépôt.** Un résultat « mot trouvé à la page 5 » documente une présence lexicale dans la version de document téléchargée, non l'authenticité de la signature, la réalité d'une prestation ou l'effet d'un service. Un PDF numérisé sans couche de texte peut être téléchargé et empreinté tout en laissant zéro passage repérable ; aucun résultat de reconnaissance de caractères n'est inventé.

## Préservation et vérifications

Une indisponibilité temporaire du site laisse le relevé précédent inchangé. Si les deux sources sont inaccessibles au premier passage, l'exécution échoue avant publication : le programme ne crée pas de succès fictif.

La tâche `.github/workflows/releve-pdfs-municipaux.yml` s'exécute mensuellement, au changement du collecteur ou à la demande. Ses résultats ne sont intégrés que par la procédure automatique de publication, sur un fichier JSON strictement autorisé, après les trois vérifications Python 3.11, Python 3.12 et conteneur de la révision proposée. Les tests `tests/test_relever_pdfs_municipaux.py` simulent sans réseau les pièces correctes, les documents tronqués, les sources externes et les indisponibilités.

**Limites :** une empreinte et des pages retrouvées confirment un relevé de fichier, pas une signature administrative authentifiée, une mise en service ou une économie de temps démontrée. Aucune enquête OCR, aucune extraction de données personnelles, aucune collecte de liens arbitraires.
