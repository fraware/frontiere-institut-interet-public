# Consignes pour l'évaluateur indépendant

Vous participez à une évaluation aveugle de FRONTIÈRE.

Vous recevez uniquement le fichier `jeu_reserve_v1_questions.json` et le modèle de réponse. Ne consultez pas le dépôt GitHub, son historique, ses discussions ou toute ressource susceptible de révéler l'origine exacte des cas.

Pour chaque cas H01 à H10, fournissez :

- `voies` : une à quatre voies de résolution prioritaires ;
- `formes_ressource` : une à quatre formes de ressource réellement adaptées ;
- `ressources` : des ressources nommées seulement si elles sont justifiées par la recherche ;
- `urls_preuves` : les sources qui soutiennent directement les propositions ;
- `duree_secondes` : le temps total consacré au cas ;
- `minutes_analyste` : le temps de travail intellectuel humain direct ;
- `minutes_verification` : le temps humain consacré à vérifier la réponse ;
- `notes` : au plus deux phrases sur les principales inconnues.

## Règles

1. Privilégier la justesse des propositions à leur nombre.
2. Proposer des mécanismes concrets et activables.
3. Considérer plusieurs formes de ressource : personne, équipe, laboratoire, organisme, réseau, formation, infrastructure ou autre forme pertinente.
4. Distinguer la capacité scientifique ou technique du mécanisme administratif permettant de la mobiliser.
5. Chaque source citée doit soutenir directement une proposition.
6. Ne pas utiliser les hypothèses internes de FRONTIÈRE pour orienter la réponse.
7. Ne pas chercher à retrouver le corrigé à partir de formulations particulières ; utiliser la recherche en ligne comme un analyste répondant au problème.
8. Ne pas consulter le fichier privé de référence, le manifeste de son empreinte ou le programme d'évaluation.

La réponse finale doit couvrir exactement H01 à H10 et suivre la structure de `modele_reponses.json`.
