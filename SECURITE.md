# Sécurité

FRONTIÈRE est publié dans un dépôt public. Le dépôt et l'instance publique ne doivent contenir aucun secret, aucune donnée personnelle confidentielle, aucune information de sécurité, aucun conflit d'intérêts sensible et aucun dossier de candidature réel.

## Données admises dans la version publique

Seules les informations ordinaires ou internes à faible sensibilité peuvent être saisies. Les informations sensibles ou fortement restreintes exigent une instance privée comportant au minimum :

- une authentification ;
- des droits d'accès différenciés ;
- un journal des accès ;
- un chiffrement adapté ;
- des sauvegardes ;
- une durée de conservation définie ;
- une procédure de suppression ;
- une procédure de traitement des incidents.


## Démarrage en environnement institutionnel

L'application actuelle autorise des opérations de lecture et d'écriture **sans identité d'utilisateur ni droits différenciés**. Elle ne constitue pas un service sécurisé pouvant accueillir des dossiers réels confidentiels.

Au démarrage, le programme refuse les modes `FRONTIERE_ENV=production`, `FRONTIERE_ENV=staging` et tout autre mode non reconnu tant qu'aucune authentification et aucun contrôle des droits ne sont intégrés. Cette protection empêche qu'un réglage déclaratif de production masque l'absence de mécanismes de sécurité.

Les modes `development` et `test` sont destinés uniquement aux instances expérimentales **isolées et contrôlées**, avec des données artificielles ou explicitement publiques. Le mode de développement n'est pas une autorisation de publier l'application sur Internet. Le conteneur écoute sur toutes les interfaces internes pour faciliter les essais ; publier son port vers l'extérieur sans protection exposerait les opérations de modification.

Ce contrôle de démarrage n'ajoute **aucune authentification**, n'empêche pas un opérateur mal configuré d'exposer une instance de développement et ne remplace pas les contrôles d'accès, journaux, sauvegardes et procédures de conservation définis plus haut. Une véritable exploitation institutionnelle reste bloquée jusqu'à mise en place et essais de ces garanties.

## Signalement d'un problème

Ne pas publier dans une discussion publique une vulnérabilité accompagnée de données réelles. Utiliser un canal privé du mainteneur.

## Spécification préparatoire pour les données institutionnelles

La [spécification du modèle de sécurité institutionnelle](docs/MODELE_SECURITE_INSTITUTIONNELLE_V1.md) décrit les frontières de confiance, les rôles, les obligations d'autorisation par dossier et les conditions de réception avant toute exploitation réelle. Elle ne constitue pas un dispositif d'authentification. Le refus de démarrage en production reste pleinement applicable.
