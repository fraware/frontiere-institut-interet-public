# Jeu réservé — version 1

Ce dossier contient les éléments publics nécessaires à une évaluation indépendante de FRONTIÈRE.

## Fichiers

- `jeu_reserve_v1_questions.json` contient les dix questions ;
- `jeu_reserve_v1_manifeste.json` contient l'empreinte cryptographique du fichier privé de référence ;
- `CONSIGNES_EVALUATEUR.md` décrit les règles de l'évaluation ;
- `modele_reponses.json` donne la structure attendue des réponses.

Les réponses de référence, leurs sources et les voies attendues sont conservées hors du dépôt public.

## Procédure

1. remettre les questions et les consignes à un évaluateur qui n'a pas vu les références ;
2. obtenir un fichier de réponses complet ;
3. vérifier sa structure avec `scripts/verifier_reponses_jeu_reserve.py` ;
4. figer le fichier de réponses ;
5. seulement ensuite, comparer les réponses au fichier privé de référence avec `scripts/evaluer_jeu_reserve.py`.

L'empreinte cryptographique garantit que le fichier privé utilisé pour l'évaluation correspond à celui préparé avant les réponses de l'évaluateur.
