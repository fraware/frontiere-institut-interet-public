# Modèle de sécurité avant exploitation institutionnelle — version 1

**État : spécification préparatoire, non déployée.** Le prototype public ne possède ni authentification ni permissions par dossier. Les opérations d'écriture sont accessibles sans identité vérifiée lorsque l'instance expérimentale est exposée. Le contrôle de démarrage refuse les environnements déclarés de production et de préproduction ; il n'empêche pas l'exposition accidentelle d'un serveur démarré en développement.

## Périmètre de confiance actuel

L'application FastAPI `app/main.py` dépend d'une base SQLAlchemy locale. `app/config.py` contient des paramètres de développement, dont une valeur de secret explicitement réservée au développement. Les événements d'audit attribuent actuellement par défaut leurs actions à « équipe Frontière », sans identité personnelle authentifiée. Une telle chaîne ne fournit pas de preuve d'attribution individuelle ni de contrôle d'accès.

La base regroupe notamment les besoins, organismes, ressources, découvertes, preuves, journaux, évaluations et événements d'audit. Les niveaux de sensibilité sont attachés aux dossiers, alors que les droits réels et les finalités de traitement devront aussi porter sur les objets liés, les exports et les pièces jointes. Un numéro de niveau n'autorise aucune communication supplémentaire.

## Menaces prioritaires

| Scénario | Défense attendue | Test de réception |
| --- | --- | --- |
| Lecture d'un dossier par une autre institution | Autorisation par objet et organisation, refus explicite par défaut | Deux institutions, même type de dossier : accès croisé refusé par la lecture et les exports |
| Écriture sans identité vérifiée | Identité institutionnelle vérifiée avant chaque modification | Requêtes anonymes refusées, y compris fichiers et actions secondaires |
| Élévation de rôle ou modification d'un identifiant de dossier | Autorisation côté serveur, indépendante des paramètres du client | Un lecteur ne transforme aucun dossier en modifiant son identifiant |
| Fuite par journaux, sauvegardes, recherche ou export | Minimisation, redaction ciblée, frontières des finalités | Contrôles sur les journaux, indices, copies, traces et exports |
| Modification discrète des preuves ou de l'antériorité | Journal externe appendu, horodatages et empreintes vérifiés séparément | Altération de la base détectée par une comparaison indépendante |
| Utilisation du contenu documentaire comme instruction | Traitement des sources comme données non fiables | Essai d'injection dans une pièce importée, aucune élévation de privilège |
| Accès persistant d'un ancien opérateur | Révocation de session et d'habilitation | Compte révoqué refusé sur tous les points d'accès |
| Panne ou suppression malveillante | Sauvegarde chiffrée, séparation des responsabilités et essai de restauration | Restauration complète en environnement isolé, avec mesures d'intégrité |

## Identité, rôles et portée

L'identification doit reposer sur un fournisseur institutionnel de confiance capable de délivrer des identités individuelles, au moyen d'un protocole standard choisi pour l'environnement d'hébergement. Les secrets, les identifiants d'applications et les clés privées ne doivent pas être intégrés dans Git.

Les rôles minimaux à distinguer sont : opérateur d'étude, responsable d'une organisation, évaluateur indépendant, détenteur de références privées, responsable technique et responsable de sécurité. Les droits portent **sur l'action, la finalité, la sensibilité, l'organisation et le dossier exact** ; un rôle seul ne suffit pas. Le détenteur des références privées n'obtient pas automatiquement la faculté de modifier les réponses d'évaluation. Un financeur ne reçoit aucun droit automatique sur les dossiers individuels.

Les accès temporaires doivent expirer, les comptes administratifs utiliser des privilèges distincts et les accès sensibles faire l'objet d'une authentification renforcée et de journaux exploitables.

## Séparation des finalités

Conserver quatre espaces logiques séparés et leur habilitation : recherche, réseau professionnel, mission réelle et intégrité. Une personne ou un dossier associé à deux espaces ne justifie pas le rapprochement systématique de leurs informations. Les éléments contenant des données personnelles requièrent une base juridique identifiée, une durée de conservation définie, un fondement documenté de communication et une procédure d'exercice des droits.

Les niveaux de sensibilité 3 et 4 restent exclus de l'instance actuelle. Les dossiers de niveau inférieur ne doivent jamais être pris pour des données anonymes du seul fait de leur classification.

## Conditions avant toute ouverture d'une instance institutionnelle

1. Choisir le responsable de traitement, la base juridique, les finalités, les catégories de personnes, les accès et la durée de conservation ; organiser la revue avec les responsables compétents.
2. Spécifier le fournisseur d'identité, la topologie de l'hébergement, les frontières entre institutions et l'administration technique.
3. Implémenter et tester **sur tous les points d'entrée** l'authentification et les autorisations par dossier, y compris exports, pièces jointes, interfaces de programmation et tâches différées.
4. Remplacer l'attribution générique actuelle des audits par une identité contrôlée, établir une conservation des journaux séparée des données métier et définir les conditions d'accès et d'effacement appropriées.
5. Installer chiffrement en transit et au repos, gestion indépendante des secrets, sauvegardes vérifiées, surveillance, réponses aux incidents, protection contre les ressources non fiables et procédures de suppression.
6. Conduire des essais d'autorisation interorganisationnelle et des vérifications techniques indépendantes ; tester les restaurations, révocations et erreurs de configuration.
7. Uniquement ensuite, revoir le blocage explicite de démarrage en production et les restrictions de sensibilité. Aucun interrupteur de configuration ne doit autoriser à lui seul des données sensibles.

## Critère de décision

La réussite d'essais unitaires sur de faux dossiers ne certifie ni la conformité juridique, ni la sécurité de l'hébergeur, ni la robustesse contre tous les acteurs malveillants. La fermeture du ticket n° 7 exige une instance réellement configurée, les preuves des contrôles ci-dessus et une revue de sécurité adaptée au niveau de données.

**Cette note ne déverrouille aucun environnement de production, ne crée aucun utilisateur et n'autorise aucune ingestion de données sensibles.**
