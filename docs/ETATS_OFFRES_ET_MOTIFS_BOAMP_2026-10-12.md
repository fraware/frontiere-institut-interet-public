# Séparer les offres reçues du motif officiel de non-attribution

## Cas réel de vérification

Le relevé public BOAMP du 12 octobre 2026, [exécution 38201268847](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38201268847), contient l'avis d'attribution `26-6175` du **20 janvier 2026**, publié par le **Centre hospitalier de Cayenne Andrée Rosemon**.

Le formulaire eForms est un avis de résultat d'une **relance des lots de menuiserie et de mobilier** dans un chantier hospitalier. La description de la procédure précise que cette relance fait suite à la résiliation du contrat initial pour défaillance d'un titulaire, afin d'assurer la continuité du chantier. Elle mentionne l'urgence, un démarrage des travaux dès novembre 2024, un calendrier ancien devenu contraint et des plans d'exécution déjà disponibles. Ces détails constituent des **hypothèses explicatives concurrentes** d'une pénurie de compétences ; leur effet causal n'est pas quantifié.

| Avis 26-6175 | LOT-0001 | LOT-0002 |
| --- | --- | --- |
| Code de résultat `cbc:TenderResultCode` | `clos-nw` | `clos-nw` |
| Motif officiel `efbc:DecisionReasonCode` | `other` | `other` |
| Code de statistique `efbc:StatisticsCode` | `tenders` | `tenders` |
| Nombre officiel `efbc:StatisticsNumeric` | **0** | **0** |
| Observation justifiée | Aucune offre totale déclarée | Aucune offre totale déclarée |
| Motif « aucune offre reçue » juridiquement codé | **Non** | **Non** |

Cette divergence interdit d'utiliser exclusivement le motif `no-rece` pour découvrir les cas de **zéro offre reçue déclarée**. Elle interdit aussi de réécrire le motif `other` sous le motif `no-rece`.

## Classification indépendante des variables

Les deux variables sont publiées distinctement pour chaque lot :

1. **Résultat et motif officiels** : code `selec-w` / `clos-nw`, motif `no-rece` / `other` / autre / absent. Aucune substitution depuis les nombres de soumissions.
2. **État du nombre d'offres** : `tenders=0` établit une déclaration officielle de zéro offre tous canaux ; `tenders>0` établit un nombre positif d'offres. À défaut de `tenders`, `t-esubm=0` établit seulement zéro soumission électronique et **ne prouve pas zéro offre totale**. Une valeur électronique positive atteste au moins une soumission électronique. Sans ces codes reconnus, l'effectif total reste indéterminé.

Les statistiques officielles répétées à l'identique et les résultats contractuels multiples d'un lot sont regroupés sans addition arbitraire ; chaque provenance est conservée. Si les comptes `tenders` et `t-esubm` sont tous deux publiés, le nombre électronique ne doit jamais dépasser le nombre total. Une contradiction bloque l'interprétation.

L'extraction publie les codes, les nombres et les chemins de provenance sans changer les étiquettes de résultat déjà observées. Les comparaisons scientifiques devront rapporter **séparément** le taux de lots dont le nombre total d'offres est nul et le taux de lots motivés par `no-rece`.

## Portée

Ce relevé concerne un ensemble volontairement enrichi en titres de relance, **non représentatif**. Les deux lots de Cayenne constituent un contre-exemple documentaire à l'assimilation « autre motif = des offres ont nécessairement été reçues ». Ils n'attestent ni un déficit de compétences scientifiques ni une cause établie de l'échec de la consultation.

Le jeu indépendant de 36 avis et l'ensemble enrichi de 24 avis conservent leurs identifiants et leurs empreintes respectives. Les qualifications automatiques restent distinctes des références d'une évaluation indépendante.
