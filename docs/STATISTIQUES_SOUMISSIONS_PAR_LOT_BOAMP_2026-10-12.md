# Résultats de soumissions par lot et hypothèses concurrentes — 12 octobre 2026

## Constat sur les avis officiels

Les réponses complètes des avis d'attribution, archivées sous empreinte SHA-256 dans l'exécution 38188039028, contiennent les champs eForms `efac:NoticeResult/efac:LotResult/efac:ReceivedSubmissionsStatistics`. Le sous-champ `efbc:StatisticsCode` caractérise le **type de soumissions comptées** et `efbc:StatisticsNumeric` leur nombre déclaré. Ils ne sont pas interchangeables et leurs effectifs ne doivent pas être additionnés.

| Avis et lot | Statut officiel | Motif | Code de comptage | Effectif déclaré |
| --- | --- | --- | --- | --- |
| Météo-France 26-74896, LOT-0001 | offre retenue | — | tenders | 1 |
| Université de Caen 26-30147, LOT-0001, données radar bande X | offre retenue | — | t-esubm | 1 |
| Université de Caen 26-30147, LOT-0002, traitement du signal et algorithmique radar haute fréquence | aucun titulaire | no-rece | t-esubm | 0 |

Le code `tenders` est une mesure d'offres reçues dans le formulaire ; le code `t-esubm` mesure spécifiquement les soumissions électroniques. Le motif `no-rece` figure séparément dans `efac:DecisionReason/efbc:DecisionReasonCode`, ce qui constitue la source déterminante pour qualifier l'absence d'offre sur le lot 2 de Caen.

Le fait que certains formulaires comportent un nœud `efac:LotTender` ne suffit jamais pour calculer un nombre de soumissions, identifier un candidat valable ni déclarer un titulaire. Le nombre officiel et le statut de résultat du lot demeurent les références retenues.

## Portée de l'inférence

Le dossier Caen constitue un **signal documentaire d'absence de réponse à un lot de marché public**. Il ne démontre pas, à lui seul, une pénurie de compétences dans la société française, une difficulté interne de recrutement, une indisponibilité publique des spécialistes ni une incapacité à produire le résultat scientifique.

Quatre hypothèses concurrentes sont examinables à partir de pièces supplémentaires : demande excessivement spécialisée au regard du périmètre contractuel ; modalités financières ou délais de remise ; disponibilité et stratégie commerciale des soumissionnaires ; inadéquation entre la structure du lot et les compétences ou équipements requis. L'état actuel des preuves ne départage aucune de ces causes.

La suite prioritaire consiste à reconstruire le **dossier initial du lot 2**, ses critères détaillés et son calendrier, puis à rechercher une éventuelle nouvelle consultation, un ajustement des spécifications ou un résultat de remplacement. Cette recherche se limite aux documents publics et aux preuves archivables.

## Exigences du traitement

Le programme `scripts/reconstituer_chronologies_pilotes_boamp.py` restitue dorénavant les statistiques de soumissions, leurs codes source, valeurs entières et chemins de provenance jusqu'au champ numérique. Une donnée absente n'est pas convertie en zéro. Un motif `no-rece` associé à une statistique positive provoque une erreur de cohérence. Les résultats de lots et les contrats restent séparés.

Aucun effectif de ce corpus intentionnel ne constitue une estimation statistique de la fréquence nationale des besoins spécialisés non satisfaits. Aucun délai de première contribution utile n'est établi.
