# HOLDOUT v1

Ce dossier contient uniquement les dix requêtes aveugles et l'engagement cryptographique sur les étiquettes.

Les sources, voies attendues, formes de ressource attendues et notes de référence sont conservées hors du dépôt public.

## Exécution

1. Donner `holdout_v1_blind.json` au runner.
2. Produire un fichier de prédictions couvrant exactement H01–H10.
3. Ne pas inspecter l'historique du dépôt pour retrouver les sources.
4. Scorer ensuite avec le fichier d'étiquettes privé :

```bash
python scripts/score_holdout.py \
  --blind benchmark/holdout_v1_blind.json \
  --manifest benchmark/holdout_v1_manifest.json \
  --labels /chemin/prive/holdout_v1_labels.json \
  --predictions predictions.json \
  --output score.json
```

Le scorer vérifie d'abord que le SHA-256 des étiquettes correspond au manifeste public.

## Mesures

Les voies et formes de ressource sont évaluées avec précision, rappel et F1. Cette combinaison évite qu'une méthode améliore artificiellement son rappel en proposant toutes les catégories possibles.

Le temps analyste, le temps de vérification et le nombre de preuves sont conservés séparément.
