# Historique des évolutions

Ce fichier résume les principales étapes publiques du projet. Les détails complets restent disponibles dans l’historique Git.

## Non publié

### Référentiel institutionnel vivant

- définition d'un graphe canonique couvrant l'État central, les services territoriaux, collectivités, opérateurs, autorités indépendantes, recherche, santé et participations publiques ;
- registre initial des principales sources officielles et de leur cadence ;
- séparation entre validité institutionnelle et date d'observation ;
- surveillance quotidienne de la fraîcheur et des modifications des sources ;
- matrice de couverture et schémas canoniques pour les entités et relations ;
- ingestion du snapshot DILA du 6 octobre 2026 avec 7 903 entités et 8 071 relations hiérarchiques résolues ;
- 7 898 parents principaux dérivés, cinq entités sans parent principal et 158 références hiérarchiques explicitement conservées comme non résolues ;
- vérification automatique des empreintes, partitions, identités, relations et parentage du snapshot complet ;
- couverture des **93 782 enregistrements** du snapshot courant de l'Annuaire DILA par l'union des **7 903 SI** et **85 879 SL/SIL** ;
- ingestion de **4 155 relations** locales et croisées, avec **3 536 parents principaux** ;
- résolution par le flux local des **158 références hiérarchiques** restées orphelines dans le seul ROAE ;
- conservation explicite de **100 références locales** dont la cible est absente du snapshot courant ;
- interrogation à la demande de la compétence géographique DILA et contrôle de bout en bout sur une commune réelle ;
- empreinte sémantique de l'export Annuaire afin d'éliminer les faux changements dus à l'ordre de transport.

### Exécution terrain

- quatre prises de contact rendues directement exécutables avec canaux vérifiés, messages, données minimales et règles de relance ;
- provenance des canaux de contact enregistrée dans les données du projet ;
- nouveaux contrôles automatiques sur le paquet d’exécution.

### Documentation et tenue du dépôt

- refonte de la page d’accueil ;
- index documentaire ;
- architecture conceptuelle ;
- état empirique consolidé ;
- guide de contribution ;
- vérifications automatiques sur Python 3.11 et 3.12 ;
- contrôle automatique des liens documentaires et des métadonnées de version ;
- suppression du doublon historique du guide de contribution ;
- vérification du conteneur et de son point de santé en intégration continue ;
- suivi mensuel des dépendances Python et des actions GitHub.

## 6 octobre 2026

### Passage aux données d’exécution

- mise à jour du cas ASNR avec une donnée publique récente sur les vacances de postes ;
- formalisation du plafond actuel des sources publiques ;
- quatre demandes de données ciblées pour France Compétences, IGN, Saint-Brieuc et ASNR ;
- conservation de six chronologies sur dix avec un délai de parcours directement exploitable.

## 5 octobre 2026

### Corpus et évaluation

- extension du corpus public à cinquante signaux ;
- audit des seize cas solides ;
- passage à dix chronologies documentées ;
- synthèse des premiers mécanismes observés ;
- douze cas rétrospectifs de développement ;
- séparation entre questions et références historiques ;
- analyse des délais et approfondissement progressif des chronologies.

### Version 0.5.4

- documentation et interface reformulées en français clair.

### Version 0.5.3

- paquet destiné à l’exécution indépendante du jeu réservé.

### Version 0.5.2

- jeu réservé scellé ;
- empreinte cryptographique des références ;
- mesures de précision, rappel et mesure harmonique.

### Version 0.5.1

- scellement de l’évaluation multi-méthodes ;
- extension du corpus public initial.

### Version 0.5.0

- requêtes de capacité structurées ;
- première architecture d’évaluation comparative.

## 4 octobre 2026

### Version 0.4.0

- résultats terrain enrichis ;
- progression contrôlée des ressources ;
- réutilisation inter-cas.

### Version 0.3.0

- journal de traçabilité ;
- historique versionné du besoin ;
- garde-fous de pré-enregistrement.

### Version 0.2.0

- exécution opérationnelle contrôlée ;
- registre des interlocuteurs ;
- export de recherche ;
- protections du prototype public.

## 3 octobre 2026

### Version 0.1.0

- première version opératoire du prototype FRONTIÈRE.
