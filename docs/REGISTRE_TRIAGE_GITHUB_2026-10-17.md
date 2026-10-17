# FRONTIÈRE — Registre de triage des demandes et des problèmes

**État examiné :** 17 octobre 2026. **Nature :** aide à la décision pour le suivi des travaux, distincte des preuves de leur réalisation.

La qualité d'un dépôt se mesure aux travaux réellement intégrés et suivis, pas à la diminution artificielle du nombre de demandes. Une tâche scientifique bloquée peut légitimement rester ouverte. Une demande de fusion générée automatiquement contenant des données nouvelles doit être intégrée ou explicitement remplacée avant clôture.

## Résultats vérifiés

- [Nettoyage exceptionnel](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/39048500462) : 308 références de branches de PR déjà intégrées supprimées, zéro échec, sur un inventaire initial de 348 branches ; nouveau dénombrement : 41 branches avant les contributions de maintenance ultérieures.
- [Suppression hebdomadaire contrôlée](https://github.com/fraware/frontiere-institut-interet-public/pull/573) : programme protégé par les tests et enregistré dans la surveillance transversale, fusionné dans `main`. Cette protection ne ferme ni ne fusionne les propositions actives.
- [Découvertes documentaires](https://github.com/fraware/frontiere-institut-interet-public/issues/572) : PR 401 et 494 fermées après transfert des dix pistes de sources, sans ingestion déclarée.
- [Évaluation indépendante unique](https://github.com/fraware/frontiere-institut-interet-public/issues/63) : issues 26 et 27 closes comme doubles suivis de sous-expériences déjà décrites dans le protocole n° 63, sans résultat empirique présumé.

- [Canaux publics](https://github.com/fraware/frontiere-institut-interet-public/pull/575) : reprise de la PR n° 568 fusionnée après sept contrôles réussis ; les deux SHA des fichiers correspondent exactement à la proposition initiale, fermée avec preuve. Le contenu est désormais dans `main`.
- [Sonde AIFE](https://github.com/fraware/frontiere-institut-interet-public/pull/576) : reprise exploratoire non intégrée. Les tests ont révélé une incohérence entre l'échantillon et le bilan DECP ; la PR n° 570 reste ouverte, à traiter avec ses données dérivées.

## Demandes de fusion en attente de décision

| PR | Nature | État de triage et suite indispensable |
| --- | --- | --- |
| [570](https://github.com/fraware/frontiere-institut-interet-public/pull/570) | Sonde AIFE | Reste ouverte : le bilan DECP versionné doit être reconstruit avec la nouvelle sonde ; reprise n° 576 fermée sans fusion à cause des contrôles d’intégrité |
| [550](https://github.com/fraware/frontiere-institut-interet-public/pull/550) | Veille ANR | Variation de signatures documentaires non intégrée ; examiner dates et historique, puis relancer les contrôles sur branche actualisée |
| [487](https://github.com/fraware/frontiere-institut-interet-public/pull/487) | Veille DMTG | Examiner les signatures et leur temporalité ; préserver les transitions historiques avant toute clôture |
| [485](https://github.com/fraware/frontiere-institut-interet-public/pull/485) | Référentiel territorial | Modification importante de nombreux fichiers ; revue séparée de provenance, cohérence et comparaisons, aucune fusion automatique |
| [484](https://github.com/fraware/frontiere-institut-interet-public/pull/484) | Surveillance des sources | Reprise potentielle des alertes historiques ; comparer à la veille récente avant fusion |
| [449](https://github.com/fraware/frontiere-institut-interet-public/pull/449) | XML DGFiP | Grand lot de données originales ; vérifier sa nouveauté et l'intégrité avant toute éventuelle reprise |
| [407](https://github.com/fraware/frontiere-institut-interet-public/pull/407) | Enquête SCDL | Projet de recherche avec tests et dossiers ; conserver en attente de relecture documentaire indépendante |

Toute nouvelle PR de maintenance doit être prise en compte lors de la révision suivante. Les états de cette table sont ceux du triage initial, et non une lecture permanente des statuts GitHub.

## Issues ouvertes : classement des 24 travaux opérationnels

### A — Gouvernance, technique et sécurité (5)

| Issue | Décision | Condition explicite |
| --- | --- | --- |
| [54](https://github.com/fraware/frontiere-institut-interet-public/issues/54) | **Priorité A — gouvernance Git** | Protéger `main`, imposer les contrôles attendus et tester les flux automatiques ; ne pas fermer sur la seule création des procédures |
| [431](https://github.com/fraware/frontiere-institut-interet-public/issues/431) | **Priorité A — publication concurrente** | Prévenir les conflits de branches et démontrer les reprises sur plusieurs collectes |
| [537](https://github.com/fraware/frontiere-institut-interet-public/issues/537) | **Priorité A — chaîne de données** | Reproduire et comparer archives, index et site effectivement publié |
| [49](https://github.com/fraware/frontiere-institut-interet-public/issues/49) | **Bloqué par choix d'architecture** | Stockage externe immuable, politique de conservation, restauration démontrée |
| [7](https://github.com/fraware/frontiere-institut-interet-public/issues/7) | **Condition de sécurité** | Ne concerne que l'ouverture à des données de niveau 3–4 ; périmètre public limité tant que non satisfaite |

### B — Corpus documentaire et signaux (6)

| Issue | Décision | Condition explicite |
| --- | --- | --- |
| [572](https://github.com/fraware/frontiere-institut-interet-public/issues/572) | Qualification de sources | Dix découvertes à vérifier avant ingestion |
| [527](https://github.com/fraware/frontiere-institut-interet-public/issues/527) | Qualité des recrutements | Compétences, dates et faux positifs à corriger sans en déduire de besoins actuels |
| [415](https://github.com/fraware/frontiere-institut-interet-public/issues/415) | Suivi ANR | Séparer appels, sélection, financement et livrables |
| [442](https://github.com/fraware/frontiere-institut-interet-public/issues/442) | Étude DMTG | Vérifier les moyens et résultats réellement établis |
| [408](https://github.com/fraware/frontiere-institut-interet-public/issues/408) | Étude Foxy | Rechercher le bilan prévu et conserver les résultats négatifs |
| [17](https://github.com/fraware/frontiere-institut-interet-public/issues/17) | Corpus empirique | Transformer cinq sources en épisodes datés et vérifiables |

### C — Études expérimentales et résultats institutionnels (7)

| Issue | Décision | Condition explicite |
| --- | --- | --- |
| [84](https://github.com/fraware/frontiere-institut-interet-public/issues/84) | Bloquée par lecteurs indépendants | Deux relectures réellement conduites et attestées |
| [63](https://github.com/fraware/frontiere-institut-interet-public/issues/63) | Bloquée par étude indépendante | Trois méthodes, dix cas, réponses figées, comparaison sans contamination |
| [22](https://github.com/fraware/frontiere-institut-interet-public/issues/22) | Dépend des évaluations | Décider des premières sources selon résultats, pas selon volumes |
| [8](https://github.com/fraware/frontiere-institut-interet-public/issues/8) | Revue décisionnelle | Examiner les résultats de la quatrième semaine, sans supposer de premiers cas |
| [4](https://github.com/fraware/frontiere-institut-interet-public/issues/4) | Dépend d'un cas réel | Enregistrer l'état initial avant recherche |
| [5](https://github.com/fraware/frontiere-institut-interet-public/issues/5) | Dépend de 4 | Recherche prioritaire des ressources publiques et conclusion |
| [6](https://github.com/fraware/frontiere-institut-interet-public/issues/6) | Dépend de 4 et 5 | Comparaison appariée avec méthode ordinaire |

### D — Démarches institutionnelles (6)

| Issue | Décision | Condition explicite |
| --- | --- | --- |
| [3](https://github.com/fraware/frontiere-institut-interet-public/issues/3) | Coordination des démarches | Résultat concret d'échanges, non soutien général |
| [11](https://github.com/fraware/frontiere-institut-interet-public/issues/11) | EIG / DINUM | Prise de contact et réponse datées, pas simple message préparé |
| [12](https://github.com/fraware/frontiere-institut-interet-public/issues/12) | Mobilité DINUM | Cas précis de mobilité réellement documenté |
| [13](https://github.com/fraware/frontiere-institut-interet-public/issues/13) | Équipe IA de l'État | Besoin actuel et interlocuteur opérationnel attestés |
| [14](https://github.com/fraware/frontiere-institut-interet-public/issues/14) | DITP | Exemple positif ou limite de compétence établi |
| [15](https://github.com/fraware/frontiere-institut-interet-public/issues/15) | Inria Saclay | Cas où une capacité collective est pertinente, puis résultat de l'échange |

**Règle de suivi :** les démarches personnelles restent ouvertes jusqu'à preuve de contact, réponse ou décision de ne pas poursuivre. Ne jamais marquer « Terminé » une tâche d'évaluation en raison de la présence de scripts ou de tests.

## Procédure de revue régulière

Chaque lundi : relever les volumes réels ; fermer les PR effectivement remplacées, avec renvoi au nouveau commit ; vérifier les nouvelles propositions de collecte et leur date source ; ranger les issues par dépendance et niveau d'avancement ; consigner les travaux bloqués, sans modifier les données source pour améliorer artificiellement les indicateurs.

La faible quantité de PR et d'issues est un **résultat possible** d'un bon pilotage. Elle n'est pas un objectif qui justifie l'abandon de questions scientifiques encore ouvertes.
