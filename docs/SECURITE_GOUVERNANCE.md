# Sécurité et gouvernance des données

## Environnements séparés

Le modèle cible distingue quatre finalités :

1. Recherche — épisodes et analyses pseudonymisées.
2. Réseau professionnel — profil minimal et disponibilité générale avec accord.
3. Candidature — informations nécessaires à une mission réelle.
4. Intégrité et incompatibilités — conflits, intérêts, confidentialité et données à accès fortement restreint.

La version 0.1 matérialise l'environnement et le niveau de sensibilité dans le modèle. Un déploiement multi-utilisateurs réel devra appliquer des stockages ou contrôles d'accès séparés avant collecte de données sensibles de niveau élevé.

## Minimisation

Toute donnée doit avoir une finalité, une décision associée, un groupe d'accès et une durée de conservation. Une information ancienne de disponibilité doit être réaffirmée avant usage opérationnel.

## Niveaux

- 1 : ordinaire ;
- 2 : interne ;
- 3 : sensible ;
- 4 : fortement restreint.

## Interdictions v0.1

- aucun classement public de personnes ;
- aucun score global d'institution ;
- aucune inférence automatique de données sensibles ;
- aucune présentation d'une personne sans accord explicite ;
- aucune décision juridique ou déontologique automatique ;
- aucun financeur n'accède automatiquement aux dossiers individuels.

## Avant hébergement externe

Exiger au minimum : authentification, contrôle d'accès par rôle, journal d'accès, chiffrement en transit et au repos, sauvegardes, politique de conservation, procédure de suppression, gestion des incidents, séparation des secrets et revue juridique adaptée aux données réellement collectées.
