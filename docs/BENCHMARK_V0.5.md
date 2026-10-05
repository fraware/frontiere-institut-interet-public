# Banc d'évaluation FRONTIÈRE v0.5

## Objectif technique

Tester si FRONTIÈRE transforme une demande de capacité publique en une réponse plus utile qu'une recherche ordinaire, à coût humain contrôlé.

Le banc compare des méthodes sur exactement les mêmes cas. Les sorties sont évaluées séparément ; aucun score global n'est utilisé.

## Unité de test

Chaque cas contient :
- une demande présentée comme elle aurait pu l'être au moment du besoin ;
- une ou plusieurs voies de résolution de référence ;
- les formes de ressource de référence ;
- lorsque la source le permet, des ressources nommées ;
- une source publique ;
- une qualité d'étiquette.

Les cas publics initiaux sont marqués `PROVISIONAL` lorsqu'ils soutiennent un mécanisme sans constituer un épisode opérationnel complet.

## Méthodes à comparer

Noms recommandés :
- `web-manuel` ;
- `llm-web` ;
- `sources-institutionnelles` ;
- `frontiere-v0.5`.

Chaque prédiction enregistre voies, formes de ressource, ressources nommées, preuves, temps écoulé, temps analyste et temps de vérification.

## Mesures

- rappel des voies ;
- rappel des formes de ressource ;
- rappel des ressources nommées lorsque des références existent ;
- temps humain = temps analyste + temps de vérification ;
- temps écoulé ;
- nombre de preuves fournies.

Les mesures sont un vecteur. Une méthode plus rapide avec des preuves faibles ne domine pas automatiquement une méthode plus lente avec de meilleures ressources.

## Aveuglement

Avant la première prédiction d'un cas, l'interface affiche uniquement le titre et la demande. La source, les étiquettes attendues et le résultat connu sont révélés après enregistrement d'une prédiction.

## Corpus initial

Le jeu actuel contient quinze cas ou signaux publics. Les cinq premiers proviennent du corpus initial :
- France Compétences — recrutement de data scientists ;
- ministère de l'Agriculture — expertise scientifique et technique ;
- transition écologique — articulation recherche / besoins opérationnels ;
- biodiversité — synthèse scientifique ponctuelle ;
- compétences de l'État en matière de donnée.

Dix cas supplémentaires couvrent cyberdéfense, recrutement d'ingénieurs cyber, réserve opérationnelle, conseil scientifique, montée en capacité IA, requalification interne, ingénieurs du génie sanitaire, contraintes de recrutement liées au cadre administratif et coordination multi-opérateurs.

Ce corpus atteint désormais 15 cas et doit encore être renforcé jusqu'à environ 20–25 cas, avec davantage de cas complets et moins de signaux contextuels.

## Scellement multi-méthodes

Une première prédiction ne révèle plus automatiquement la référence. Les étiquettes restent scellées tant qu'un opérateur n'active pas explicitement la révélation du cas. Cela permet d'enregistrer plusieurs méthodes indépendantes sur un même cas. Une même paire `méthode + version` ne peut être soumise deux fois sur un cas.

## Critère stratégique

Le banc doit permettre de répondre à trois questions :
1. FRONTIÈRE trouve-t-il plus vite une voie crédible ?
2. FRONTIÈRE trouve-t-il des formes ou ressources utiles absentes des méthodes ordinaires ?
3. La valeur provient-elle de la recherche, de la vérification ou de la mobilisation ?

La prochaine architecture technique dépend des réponses observées.
