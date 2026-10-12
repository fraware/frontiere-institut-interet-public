# Nouveaux résultats observables dans les cas d'exécution — 12 octobre 2026

## Objet

Cette enquête poursuit les dix chronologies du corpus `donnees/chronologies_v9.json` et complète les observations du 12 octobre sur France compétences et Saint-Brieuc. Trois nouveaux dossiers documentaires sont ici exploités pour **S016 (IGN), S042 (ASNR) et S050 (Météo-France)**.

L'unité conservée est un fait opérationnel accompagné de son organisme, de son document, de sa période de référence et de sa limite. Un résultat collectif ne devient pas une date individuelle de recrutement ; une livraison de matériel antérieur ne devient pas une livraison du nouveau contrat.

Données structurées : `donnees/jalons_operationnels_sources_publiques_2026-10-12.json`.

## S016 — IGN : passage des recrutements aux usages effectifs

Le [Plan d'activités 2025 de l'IGN](https://www.ign.fr/publications-de-l-ign/institut/Publications/plan-activites-ign-2025.pdf), page **27 imprimée** (page **27 du PDF**), présente :

- **10 systèmes d'IA déjà utilisés en production** dans les activités géographiques ;
- une **réduction déclarée d'un facteur trois des temps et coûts** de production de la description de l'occupation des sols OCS GE, dans un processus refondu autour de systèmes d'IA ;
- une équipe de **30 spécialistes de l'IA** issus d'un plan de recrutement et de formation, déjà recensée dans la chronologie S016.

Les deux premières observations complètent les seules données de recrutement de la chronologie courante par un résultat de **production collective**. Le rapport ne donne pas la date individuelle de mise en production des dix systèmes, ni celle de la première contribution de chacune des personnes recrutées. La mesure du facteur trois provient de l'établissement ; le passage ne détaille pas le protocole de calcul.

## S042 — ASNR : habilitations et formation réellement effectuées

Le [rapport 2025 de l'ASNR](https://reglementation-controle.asnr.fr/annual_report/2025-fr/130/), chapitre 1.4.3, page **130 imprimée** (page web intitulée « Page 132 »), rapporte :

- **367 inspecteurs** ayant au moins une habilitation en sûreté nucléaire ou radioprotection **au 31 décembre 2025** ;
- **9 135 journées de formation** dispensées au personnel en **2025**.

Ces indicateurs documentent un état des compétences et une activité effective de formation au sein de l'ASNR. Ils ne mesurent ni le nombre de nouveaux recrutements dans les métiers rares, ni le délai de recrutement, ni le nombre de personnes distinctes formées. L'effectif total de 2 126 agents au 31 décembre 2025 figurait déjà dans S042 et n'est pas enregistré une seconde fois.

## S050 — Météo-France : étalon historique séparé du nouveau contrat

Le [Contrat d'objectifs et de performance 2022–2026 de Météo-France](https://meteofrance.fr/sites/meteofrance.fr/files/files/editorial/Rapport_COP_V14.pdf), page **11 imprimée** (sixième page du PDF), distingue trois résultats historiques :

- réception de **deux supercalculateurs** en **2020** ;
- migration de la chaîne de production opérationnelle des modèles météorologiques **au début de 2021** ;
- gain de performance **effectivement mesuré, facteur 5,5**, selon le bilan rétrospectif de l'établissement.

Ces éléments concernent **les machines du cycle 2017–2021**, et non le marché **METEO-FRANCE2432F0342** attribué à BULL SAS en juillet 2026. Le fait que les générations successives aient un fournisseur ou des objectifs apparentés ne prouve aucune livraison récente. Le début 2021 reste une période qualitative, pas une date journalière.

Le comparateur fournit une chaîne de livraison puis exploitation réellement observée dans le passé et met en évidence les pièces à chercher pour le cycle 2026 : réception, migration opérationnelle et premières utilisations scientifiques.

## Ce qui change et ce qui ne change pas

| Cas | Nouveau fait accessible | Date de première contribution individuelle |
| --- | --- | --- |
| S016 IGN | Dix systèmes en production, facteur trois déclaré sur OCS GE | Inconnue |
| S042 ASNR | 367 inspecteurs habilités, 9 135 journées de formation en 2025 | Inconnue |
| S050 Météo-France | Réception 2020 et mise en exploitation début 2021 de la **génération précédente** | Inconnue pour le marché 2026 |

L'amélioration documente mieux les résultats de **capacité collective** ; elle n'ajoute aucun délai complet entre l'apparition du besoin actuel et une première contribution utile.

Aucune ligne antérieure de `chronologies_v9.json` n'est modifiée. Les trois pièces ajoutées sont des sources primaires et les sept observations gardent leurs limites propres.

## Reproduction hors réseau

```bash
python scripts/bilan_jalons_operationnels_publics.py
python -m pytest -q tests/test_jalons_operationnels_sources_publiques.py
```

La commande rapproche les identifiants avec les dix chronologies, refuse les valeurs numériques non finies, les observations dupliquées et les dates exactes dérivées d'une simple année. Elle tient séparées les observations de l'ancienne génération Météo-France. Elle ne télécharge pas les sources distantes : leur URL et leur localisation documentaire sont fournies pour contrôle ciblé.

## Prochaines pièces réellement déterminantes

**IGN :** archives de déploiement des dix systèmes ou d'une production OCS GE permettant de dater une première contribution ; les données RH restent distinctes.

**ASNR :** statistiques 2025 par métier ou cohortes anonymisées entre ouverture de poste, sélection et prise de fonctions ; les chiffres d'habilitation et de formation sont des résultats complémentaires.

**Météo-France :** réception et migration des équipements du marché 2026, à ne jamais confondre avec le bilan ancien.

**Caen :** cahier des exigences du lot HF, éventuelle nouvelle consultation et résultat administratif ultérieur, avec identification de la procédure et de son lot.
