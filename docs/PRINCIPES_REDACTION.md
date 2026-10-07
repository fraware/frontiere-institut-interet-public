# Principes de rédaction

Les documents et l’interface de FRONTIÈRE sont destinés à une personne qui découvre le projet. Ils doivent rester compréhensibles sans connaître le code, l’historique du dépôt ni les abréviations utilisées dans les fichiers de données.

## Règles

1. Employer le français pour les titres, explications, consignes et libellés visibles.
2. Écrire le sens en toutes lettres avant tout nom technique ou toute abréviation officielle.
3. Réserver les codes internes aux blocs de code, aux noms de fichiers et aux interfaces de programmation où ils sont indispensables.
4. Ne pas demander au lecteur de mémoriser un code pour comprendre un résultat. Écrire « recherche insuffisante » au lieu d’un code de classe, « ressource mobilisable » au lieu d’un code d’état et « besoin qualifié » au lieu d’un niveau interne.
5. Remplacer les métaphores de procédure par des verbes concrets. Écrire « enregistrer et figer l’état initial » au lieu d’une formule interne.
6. Décrire une comparaison par ce qui est réellement comparé. Écrire « comparaison de la méthode habituelle et de FRONTIÈRE sur le même cas ».
7. Distinguer explicitement un fait observé, une hypothèse, une interprétation et une décision.
8. Employer le même terme pour le même objet dans tous les documents.
9. Lorsqu’un terme technique est nécessaire, l’expliquer dans la phrase où il apparaît.
10. Les documents historiques conservent leurs résultats et leurs dates, tout en respectant les mêmes règles de clarté.

## Termes privilégiés

- « cas » : situation réelle étudiée ;
- « capacité nécessaire » : ce qu’il faut savoir faire pour résoudre le problème ;
- « ressource » : personne, équipe, organisme, outil, donnée ou infrastructure susceptible d’apporter cette capacité ;
- « voie de résolution » : manière concrète de mobiliser une ressource ;
- « état initial » : description du besoin, de l’échéance, de la voie prévue sans FRONTIÈRE et des preuves disponibles avant intervention ;
- « comparaison des deux méthodes » : comparaison de la méthode habituelle et de FRONTIÈRE sur le même cas et avec les mêmes informations de départ ;
- « valeur ajoutée » : différence observée sur le résultat, le délai, la qualité, le coût ou l’apprentissage ;
- « obstacle » : événement qui ralentit ou empêche la résolution d’un cas ;
- « jeu de développement » : cas utilisés pour améliorer le système ;
- « jeu réservé » : cas tenus à part pour une évaluation indépendante.

## Noms officiels et noms techniques

Les noms officiels de sources sont écrits en toutes lettres dans le texte. Les noms techniques restent possibles lorsqu’ils sont nécessaires pour reproduire une opération.

Exemple :

> Les données proviennent du Référentiel de l’organisation administrative de l’État, publié par la Direction de l’information légale et administrative. Le fichier de statistiques correspondant est `institutionnel/statistiques_roae.json`.

## Vérification automatique

La suite de tests parcourt toute la documentation publique. Elle refuse plusieurs termes anglais déjà éliminés et plusieurs raccourcis internes lorsqu’ils apparaissent dans le texte destiné au lecteur. Les codes restent autorisés dans les blocs de code, les noms de fichiers et les adresses techniques.
