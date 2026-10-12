# Deux compléments documentaires aux cas d'exécution — 12 octobre 2026

Cette étape apporte des **observations primaires supplémentaires** pour les cas S024 et S001. Les chronologies historiques déjà publiées ne sont pas modifiées : leurs événements et leurs dates sont conservés. Les nouvelles observations figurent dans `donnees/observations_execution_publiques_2026-10-12.json`.

## S024 — Saint-Brieuc : attestation publique antérieure à juin 2025

La [Commission nationale du débat public](https://www.debatpublic.fr/sites/default/files/2024-05/Verbatim-Visite-Parc-eolien-St-Brieuc-14022024.pdf) a publié le compte rendu d'une visite-débat du **14 février 2024**.

À la **page 4 du PDF**, Léa Nativel, chargée de mission à la DDTM des Côtes-d'Armor, indique que les services ont déjà sollicité des établissements publics, notamment l'Ifremer, le Cerema et le Shom, pour bénéficier d'expertises sur des questions halieutiques, de turbidité et d'acoustique. Elle présente aussi les catégories de protocoles sur lesquels le conseil scientifique a déjà rendu des avis.

Cette attestation **précède** le rapport IGEDD daté de **juin 2025**, déjà associé à `S024-E05`. Le nouveau document atteste qu'au moins une sollicitation était déjà intervenue **au plus tard le 14 février 2024**. Il ne livre aucune paire individualisée « date de saisine / date de remise de l'avis » et ne démontre pas que chacun des trois établissements a effectivement rendu un avis dans le cadre cité. Le délai de production d'une expertise demeure inconnu.

La date du débat est celle du **14 février 2024**. Le répertoire `2024-05` dans l'adresse du PDF ne constitue pas une date de sollicitation. Le rapport de juin 2025 garde sa date propre.

## S001 — France compétences : une fiche de poste précise les exigences en R

La [fiche de poste publique de chargé(e) d'études statistiques](https://www.francecompetences.fr/app/uploads/2025/04/Fiche-de-poste_Charge-detudes-statistiques_2025.pdf), au sein de la Direction de l'Observation et de l'Évaluation, définit des tâches de préparation, d'analyse et d'exploitation de données. Elle cite **R** parmi les outils de traitements statistiques attendus (**page 2 du PDF**) et propose un **CDD de neuf mois** (**page 3 du PDF**).

La fiche matérialise des exigences et conditions contractuelles cohérentes avec la difficulté de capacité rapportée lors de l'audition de Stéphane Lardy, le 3 avril 2025. Elle **ne prouve pas** qu'il s'agit du même poste ou de la même recherche de remplacement, qu'un candidat a été trouvé, ni que la capacité a été rétablie. Son adresse contenant `2025/04` ne suffit pas à dater l'ouverture effective du poste. Aucun nouvel événement daté n'est ajouté à S001.

## Exploitation reproductible

Depuis la racine du dépôt :

```bash
python scripts/extraire_jalons_execution_publics.py
pytest -q tests/test_complements_execution_publics.py
```

Le programme conserve les attestations datées, les dates individuelles d'action et les documents de recrutement non datés dans des catégories distinctes ; il refuse de convertir une fiche de poste sans date en recrutement accompli. Il n'effectue pas d'accès réseau ni de vérification des octets des PDF.

**Limite de ce cycle :** aucun nouveau délai jusqu'à la première contribution utile n'est désormais calculable à partir de ces deux documents. Les cas IGN (S016) et ASNR (S042) demeurent inchangés. La recherche complémentaire n'a pas apporté leurs délais individuels ou par métier.
