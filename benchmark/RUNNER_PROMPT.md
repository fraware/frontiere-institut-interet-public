# Prompt pour runner indépendant — HOLDOUT v1

Tu participes à une évaluation aveugle de FRONTIÈRE.

Tu reçois uniquement `benchmark/holdout_v1_blind.json`. N'ouvre pas le dépôt GitHub, son historique, les issues, les commits ou toute autre ressource susceptible de révéler l'origine des cas.

Pour chaque cas H01–H10, produis :

- `routes` : 1 à 4 voies de résolution prioritaires, sous forme de libellés courts en MAJUSCULES_AVEC_UNDERSCORES ;
- `resource_forms` : 1 à 4 formes de ressource réellement adaptées ;
- `resources` : ressources nommées seulement si elles sont justifiées par la recherche ;
- `evidence_urls` : sources utilisées pour justifier la sortie ;
- `elapsed_seconds` : temps total écoulé consacré au cas ;
- `analyst_minutes` : minutes de travail intellectuel humain direct ; mettre 0 pour un run entièrement automatisé ;
- `verification_minutes` : minutes humaines consacrées à vérifier la sortie ;
- `notes` : au plus deux phrases sur les inconnues principales.

Règles :

1. Optimise la précision. Ne propose pas une voie ou une forme de ressource simplement pour augmenter le rappel.
2. Recherche des mécanismes concrets et activables.
3. Une personne n'est qu'une forme de ressource parmi d'autres. Considère aussi équipes, laboratoires, organismes, réseaux, formations et infrastructures.
4. Distingue les capacités scientifiques ou techniques des mécanismes administratifs.
5. Chaque URL doit soutenir directement un élément proposé.
6. Aucun raisonnement fondé sur le nom FRONTIÈRE ou sur les hypothèses du projet.
7. Ne cherche pas à retrouver le texte source exact du cas à partir de formulations uniques. Utilise le Web comme un analyste répondant au problème, pas comme un détective recherchant le corrigé.
8. Ne consulte pas les labels privés, le manifeste de hash ou le scorer.

La sortie finale doit être un JSON conforme à `benchmark/predictions_template.json` et couvrir exactement H01–H10.

Nom de méthode recommandé :
- run généraliste avec Web : `llm-web-independent`
- analyste manuel : `web-manuel-independent`

Avant remise :
```bash
python scripts/validate_holdout_predictions.py \
  --blind benchmark/holdout_v1_blind.json \
  --predictions predictions.json
```
