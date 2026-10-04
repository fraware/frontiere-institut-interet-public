# Traçabilité — FRONTIÈRE v0.3

## Objet

La v0.3 formalise une règle méthodologique centrale : toute conclusion doit pouvoir être reconstruite à partir de l'état d'information disponible au moment où elle a été prise.

Deux mécanismes sont séparés.

### 1. Versionnement du besoin

Le besoin actif possède un numéro de version. La version initiale est verrouillée avant investigation. Une information nouvelle ne modifie jamais silencieusement cette version.

Une révision :
- rend la version précédente historique ;
- crée une nouvelle version active ;
- conserve situation, résultat recherché, responsable, échéance, contrefactuel et hypothèse ;
- est immédiatement verrouillée ;
- enregistre explicitement la raison de révision.

La version précédente reste consultable.

### 2. Journal appendu des événements

Les opérations critiques créent un événement de traçabilité : création d'épisode, verrouillage, révision, preuve ajoutée, recherche publique, état d'une ressource, évaluation d'une voie, décision, friction, résultat et connaissance réutilisable.

Chaque événement contient :
- type d'événement ;
- type et identifiant de l'objet concerné ;
- épisode, le cas échéant ;
- horodatage ;
- acteur ;
- contexte structuré.

Lorsqu'une opération dépend d'une version du besoin, son identifiant est inscrit dans le contexte de l'événement.

## Invariants

1. Une recherche publique, une ressource, une voie, une décision, une friction, un résultat ou une connaissance opérationnelle exigent un besoin actif verrouillé.
2. Une révision n'efface aucune version antérieure.
3. Les événements du journal ne sont pas modifiés par l'interface.
4. Les opérations importantes doivent être interprétables avec la version du besoin qui existait alors.
5. Le journal sert à l'audit méthodologique ; le suivi du temps humain reste un objet distinct.

## Limites

Le journal v0.3 n'est pas un mécanisme de sécurité ni une preuve cryptographique d'intégrité. Il ne remplace ni authentification, ni journal d'accès, ni stockage immuable pour un déploiement sensible.
