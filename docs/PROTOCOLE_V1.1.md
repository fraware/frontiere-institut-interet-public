# Protocole FRONTIÈRE - INSTITUT POUR L’INTÉRÊT PUBLIC - v1.1

## Statut

Version consolidée avant les premiers épisodes réels. Cette version reprend le protocole de pré-exécution et enregistre les extensions issues des tests adverses et de la conception fonctionnelle. Toute modification ultérieure importante doit être datée, justifiée et versionnée.

## Question centrale

Lorsqu'une institution publique ne dispose pas, au moment utile, d'une capacité scientifique ou technique importante, quel mécanisme explique réellement la situation et quelle est la plus petite intervention capable de la corriger ?

## Unité d'analyse

Un épisode est une situation délimitée dans le temps associant :

- une institution et une unité concernée ;
- un résultat opérationnel précis ;
- une capacité manquante ou inaccessible ;
- une période identifiable ;
- des démarches effectivement entreprises ;
- un résultat observé ou une situation actuelle ;
- une explication documentée de la difficulté ;
- un contrefactuel ;
- une qualité de preuve.

## Extension v1.1 : de la personne à la ressource

La version antérieure était plus centrée sur les personnes. La version 1.1 distingue désormais :

`Source → Ressource → Forme d'intervention → Voie de mobilisation`

Une ressource peut être une personne, une équipe, un laboratoire, un organisme, un prestataire, une communauté, un outil, un jeu de données, un document, un modèle, un service ou une procédure.

Cette modification évite d'interpréter chaque déficit comme un problème de recrutement.

## Niveaux de demande

- D0 : intérêt hypothétique.
- D1 : problème historique documenté.
- D2 : besoin actuel avec responsable identifié.
- D3 : besoin actuel avec ressources engagées.
- D4 : besoin immédiatement activable avec procédure, financement ou dispositif déclenchable.

Les estimations de demande opérationnelle reposent principalement sur D2–D4.

## Recherche prioritaire dans le secteur public

La recherche publique précède normalement une recherche extérieure. Une dérogation d'urgence peut autoriser des recherches parallèles, avec justification documentée.

- P0 : recherche insuffisante pour conclure.
- P1 : capacité publique pertinente trouvée et mobilisable.
- P2 : capacité publique pertinente trouvée, mobilisation non établie ou difficile.
- P3 : recherche suffisamment approfondie et aucune capacité publique suffisamment pertinente identifiée.

P2 est un signal de mobilité ou d'organisation, pas une preuve de pénurie.

## États génériques d'une ressource

- R0 : identifiée.
- R1 : pertinence plausible.
- R2 : capacité vérifiée.
- R3 : conditions compatibles.
- R4 : capacité d'engagement confirmée.
- R5 : mobilisable pour le besoin précis et la période considérée.

La mobilisabilité est relationnelle : `ressource × besoin/mission × temps`.

## Résultat principal

Le résultat principal d'un épisode est la résolution ou l'orientation utile du déficit :

- résolu ;
- partiellement résolu ;
- correctement réorienté ;
- non résolu ;
- besoin devenu sans objet.

Le placement d'une personne n'est pas un critère principal.

## Additionalité

Aucun score agrégé. Cinq dimensions sont conservées séparément :

- issue ;
- délai ;
- qualité ;
- coût ;
- apprentissage réutilisable.

Chaque dimension est classée forte, modérée, faible, nulle ou indéterminée avec justification et preuve.

## Capacité d'accueil

Pour une mission longue, cinq conditions impératives sont évaluées :

- responsable institutionnel ;
- encadrement opérationnel ;
- accès ;
- capacité de décision ;
- transmission interne.

`UNKNOWN` ne vaut jamais `PASS`. D'autres formes d'intervention possèdent des profils de préparation adaptés.

## Frictions et chemin critique

Chaque délai est enregistré comme événement avec dates, responsable, dépendances, caractère bloquant et motif. Les processus parallèles ne sont pas additionnés naïvement. Le délai pertinent est reconstruit par le chemin critique du graphe de dépendances.

## Mémoire et effet cumulatif

Chaque connaissance réutilisable est enregistrée comme objet explicite : capacité, source, ressource, voie, friction, délai, règle ou précédent. Une réutilisation n'est comptée que si elle est effectivement reliée à un épisode ultérieur. La mesure la plus exigeante est la réutilisation entre organisations distinctes et l'accessibilité de la connaissance à un nouvel analyste.

## Cas synthétiques

Douze scénarios adverses servent aux tests du protocole. Ils sont marqués `synthetic=true` et exclus des statistiques opérationnelles. Ils ne constituent aucune preuve sur la France.

## Place de l'intelligence artificielle

L'intelligence artificielle peut assister l'extraction, la recherche de précédents, la détection de contradictions, la recherche de ressources et la synthèse des preuves. La validation du besoin, D0–D4, P0–P3, R5, l'orientation finale, la présentation d'une personne, les décisions de conformité et l'additionalité restent sous autorité humaine.

Toute connaissance opérationnelle doit exister dans le système avec une provenance ; une information présente seulement dans le contexte d'un modèle ne constitue pas une preuve institutionnelle.

## Phase des douze premières semaines

Cible :

- 8 à 12 épisodes fortement documentés ;
- au moins 4 organisations ;
- au moins 8 D2+ ;
- au moins 75 % de besoins préexistants à la sollicitation ;
- 3 à 5 recherches parallèles appropriées ;
- recherche publique systématique ;
- 20 à 30 entretiens spécialistes ;
- quelques employeurs ;
- plusieurs reconstructions de chemin critique ;
- contrôles négatifs et cas où les mécanismes existants fonctionnent correctement.

Les sorties possibles restent : construire, construire de manière ciblée, réorienter, prolonger ou arrêter.
