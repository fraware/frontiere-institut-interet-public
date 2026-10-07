# Historique des évolutions

Ce fichier résume les principales étapes publiques du projet. Les détails complets restent disponibles dans l’historique Git.

## Non publié

### Clarté documentaire

- réécriture des principaux documents du référentiel institutionnel en français directement compréhensible ;
- remplacement des codes internes par leur signification dans les tableaux, titres et explications destinés au lecteur ;
- harmonisation de l’interface autour des termes « état initial », « règles de comparaison » et « recherche dans le secteur public » ;
- contrôle automatique de l’ensemble de la documentation pour éviter la réintroduction des principaux raccourcis internes.

### Référentiel institutionnel vivant

- définition d’une représentation commune des administrations, services territoriaux, collectivités, opérateurs, autorités indépendantes, structures de recherche, établissements de santé et participations publiques ;
- registre initial des principales sources officielles et de leur fréquence de vérification ;
- séparation entre la période de validité d’une information et la date à laquelle FRONTIÈRE l’a observée ;
- surveillance quotidienne de la fraîcheur et des modifications des sources ;
- mesure de la couverture et schémas communs pour les organisations et leurs relations ;
- importation, au 7 octobre 2026, de **7 905 services ou organismes** issus du Référentiel de l’organisation administrative de l’État, avec **8 073 relations hiérarchiques résolues** ;
- couverture des **93 782 enregistrements** de l’Annuaire de l’administration grâce à l’union de la publication sur l’organisation de l’État et des **85 877 services et guichets locaux** ;
- importation de **4 155 relations hiérarchiques locales ou croisées**, avec **3 536 parents principaux** ;
- résolution, grâce à l’Annuaire local, des **158 références hiérarchiques** dont la cible manquait dans la seule publication sur l’organisation de l’État ;
- conservation explicite de **100 références locales** dont la cible est absente de l’export courant ;
- interrogation à la demande de la compétence géographique publiée par la Direction de l’information légale et administrative ;
- utilisation d’empreintes calculées sur le contenu pour éviter les faux changements dus à un simple réordonnancement des données ;
- importation de **40 345 unités territoriales** issues du Code officiel géographique de l’Insee, reliées par **150 421 relations territoriales**.

### Premier cas prospectif

- enregistrement obligatoire de la situation initiale avant toute recherche menée par FRONTIÈRE ;
- exigence d’un responsable opérationnel, d’une échéance, d’une voie prévue sans FRONTIÈRE et d’au moins une preuve initiale ;
- enregistrement préalable des règles de comparaison entre la méthode habituelle et FRONTIÈRE ;
- empreintes cryptographiques de l’état initial et des règles de comparaison afin de vérifier leur antériorité.

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

- jeu réservé figé avant évaluation ;
- empreinte cryptographique des références ;
- mesures de précision, rappel et mesure harmonique.

### Version 0.5.1

- règles de l’évaluation comparative fixées avant exécution ;
- extension du corpus public initial.

### Version 0.5.0

- description structurée des capacités recherchées ;
- première architecture d’évaluation comparative.

## 4 octobre 2026

### Version 0.4.0

- résultats terrain enrichis ;
- progression contrôlée des ressources ;
- réutilisation entre cas.

### Version 0.3.0

- journal de traçabilité ;
- historique versionné du besoin ;
- règles empêchant une recherche avant l’enregistrement de l’état initial.

### Version 0.2.0

- exécution opérationnelle contrôlée ;
- registre des interlocuteurs ;
- export de recherche ;
- protections du prototype public.

## 3 octobre 2026

### Version 0.1.0

- première version opératoire du prototype FRONTIÈRE.
