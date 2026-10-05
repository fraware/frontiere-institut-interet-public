# Traçabilité — version 0.3

## Objectif

Une décision doit pouvoir être relue plus tard en retrouvant les informations qui existaient au moment où elle a été prise.

Deux mécanismes permettent cette reconstruction.

## Historique du besoin

La première description du besoin est conservée. Si une nouvelle information change substantiellement le problème, une nouvelle version est créée.

La version précédente n'est pas écrasée. La raison du changement est enregistrée.

## Journal des événements importants

L'application conserve les événements qui modifient l'état d'un cas : création, modification du besoin, ajout d'une preuve, recherche, évolution d'une ressource, comparaison d'une voie, décision, obstacle, résultat et connaissance réutilisable.

Chaque événement conserve au minimum sa date, son type, l'objet concerné et le contexte nécessaire à sa compréhension.

## Règles

1. Les décisions importantes sont reliées à la version du besoin qui existait à ce moment.
2. Une nouvelle version ne supprime jamais une version antérieure.
3. Le journal n'est pas réécrit depuis l'interface.
4. Le suivi du temps humain reste distinct du journal des événements.

## Limite

Ce journal sert à reconstruire l'histoire d'une décision. Il ne remplace pas les mécanismes de sécurité, les contrôles d'accès ou un stockage conçu pour des données sensibles.
