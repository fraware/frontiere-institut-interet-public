# Gouvernance des actualisations institutionnelles

## Situation observée et portée de la migration

La chaîne dépendante associe trois collectes publiques dans cet ordre : organisation administrative de l’État, services publics locaux et territoires de l’Insee. La procédure `preparer-proposition-referentiel.yml` exécute les trois collectes dans une copie de travail unique, vérifie leurs résultats et construit une proposition distincte en présence de modifications admissibles.

L’[essai intégral sans publication du 9 octobre 2026](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/37890327489) s’est terminé avec succès. Il établit la bonne exécution technique des trois collectes et de leurs contrôles ce jour-là, sans conclure à une disponibilité institutionnelle des compétences.

La création d’une proposition par le jeton de GitHub Actions a été [vérifiée au moyen d’un dossier fictif](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/37950043096). La proposition n° 122 a été fermée sans fusion et sa branche temporaire supprimée. Le précédent échec de permission et la période de repli sont documentés dans le [suivi de gouvernance n° 54](https://github.com/fraware/frontiere-institut-interet-public/issues/54).

## Organisation cible du code

- La procédure commune réalise les collectes et contrôles, puis soumet leurs changements au moyen d’une branche technique et d’une proposition de fusion.
- Son déclenchement programmé a lieu chaque jour à 5 h 47 UTC. Un lancement manuel permet une vérification sans publication, par défaut, ou une publication demandée explicitement.
- Les trois procédures individuelles sont conservées pour les essais sur les modifications proposées. Elles disposent de droits de lecture uniquement et ne déclenchent plus de collectes périodiques ni d’écritures dans `main`.
- Les collectes indépendantes de structures de recherche et de surveillance conservent leur propre publication sous forme de propositions, sans fusion automatique.
- L’outil de publication refuse une liste de fichiers hors périmètre, une base devenue périmée et plusieurs propositions simultanément ouvertes pour une même source.

La fusion des données produites reste une opération distincte. Le contrôle de compatibilité des fichiers, les vérifications sur deux versions de Python et les essais du conteneur ne remplacent ni la relecture des sources de données ni l’évaluation indépendante de la contribution du projet.

## Procédure de réception de la migration

1. Constater que l’essai réel avec publication autorisée a terminé toutes ses étapes. Si les sources sont inchangées, constater explicitement l’absence de proposition créée ; ce résultat ne teste pas le chemin de création d’un lot de données.
2. Vérifier l’absence de nouvelle commande `git push` directement vers `main` dans les procédures, ainsi que le périmètre des permissions accordées à chaque tâche.
3. Vérifier l’activation de la programmation commune et la suppression des anciens déclenchements des trois procédures individuelles.
4. Sur le premier lot effectivement modifié, vérifier la présence d’une proposition en provenance de la branche technique, son empreinte de commit, puis les trois contrôles explicitement lancés sur cette empreinte.
5. Contrôler manuellement la proposition avant fusion, avec conservation des empreintes et du sens des données. Une absence de modifications ne justifie aucune proposition.
6. Ensuite seulement, activer les règles administratives de protection de `main` et exercer des essais non destructifs de refus d’écriture directe.

**Limite :** le connecteur GitHub disponible ne possède pas d’action administrative permettant d’activer lui-même les règles de protection. La réussite des contrôles de code ne constitue pas une preuve que ces règles sont actives. Le suivi n° 54 reste ouvert jusqu’à cette confirmation.

## Conditions de sécurité

Les essais issus de propositions externes disposent de droits de lecture uniquement. Aucun jeton de publication n’est conservé par l’étape de récupération initiale du dépôt. Les permissions de création de branches, propositions et déclenchement des contrôles sont limitées à la tâche de collecte autorisée.

La procédure commune partage un groupe de sérialisation avec les autres collectes institutionnelles. Les validations de volume, de qualité structurelle, de liens administratifs et de variation des sources interrompent la publication lorsqu’elles échouent.

En cas d’échec, l’équipe responsable doit examiner les journaux et corriger la cause. Le mécanisme refuse de remplacer automatiquement des données historiques ou de franchir un contrôle de sécurité pour obtenir une publication.
