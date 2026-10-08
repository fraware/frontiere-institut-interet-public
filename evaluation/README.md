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

## Contrôles d'intégrité des réponses

La vérification préalable contrôle les champs obligatoires, les identifiants de cas, les types des listes, les valeurs numériques finies et les durées positives ou nulles. Le programme d'évaluation refait cette vérification avant de lire les résultats.

Le rapport produit par `scripts/evaluer_jeu_reserve.py` conserve désormais les empreintes SHA-256 des **références privées** et du **fichier de réponses évalué** (`empreinte_sha256_reponses`). Pour préserver une attestation d'antériorité, l'empreinte des réponses doit être enregistrée auprès d'un tiers ou sur un support indépendant **avant** ouverture des références privées. La simple présence d'une empreinte dans le rapport généré après évaluation n'établit pas cette antériorité.

Ces contrôles ne vérifient ni l'exactitude des sources citées, ni l'indépendance de l'évaluateur, ni la pertinence des ressources nommées. Ces dimensions exigent une vérification humaine séparée.
