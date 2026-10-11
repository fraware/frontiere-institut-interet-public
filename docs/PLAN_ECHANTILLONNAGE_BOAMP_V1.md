# Échantillonnage exploratoire des avis BOAMP

## Problème scientifique

Les pistes BOAMP fondées sur les dates les plus récentes et des plafonds par acheteur sont utiles pour explorer des dossiers, sans permettre une comparaison équilibrée entre périodes et domaines. Le programme `scripts/echantillonner_avis_boamp.py` parcourt l'ensemble de l'index vérifié et constitue un cadre de sondage documentaire explicitement borné.

## Strates et témoins

Les strates sont définies par **mois civil intégralement archivé × état documentaire publié × domaine lexical**, en utilisant les sept familles d'expressions de l'analyse BOAMP. L’état documentaire distingue les avis initiaux, rectificatifs, modifications et annulations. Les mois incomplets sont exclus, avec leurs dénominateurs publiés dans le rapport.

Le groupe témoin correspond uniquement aux avis ne contenant **aucune expression des sept familles**. Il ne démontre aucune absence de besoin scientifique. Un avis peut appartenir à plusieurs domaines ; le programme compte donc séparément les tirages et les identifiants distincts.

## Tirage reproductible

Chaque annonce reçoit un rang SHA-256 fondé sur une semence annoncée, la strate, la date et l'identifiant. Les quatre plus petits rangs sont sélectionnés par défaut, avec quota configurable de un à cinquante. Dans le corpus réel vérifié, la catégorie de marché est absente pour les 197 640 avis. Le rapport compte ces valeurs manquantes et utilise l'état documentaire, effectivement renseigné. Les fractions de sondage sont calculées dans chaque strate sur les avis effectivement archivés, sans extrapolation à la demande nationale ou aux marchés distincts.

Les données publiées contiennent objets, liens officiels, états documentaires, catégories déclarées lorsqu'elles sont renseignées, acheteurs, références d'archives, dates de relevé, rangs, volumes et fractions conditionnelles. Aucun plafond par acheteur n'est appliqué, car il modifierait les fractions d'inclusion. Les concentrations d'acheteurs seront analysées séparément.

La variation de semence permet de tester la sensibilité des sélections. La comparaison de périodes porte sur les seules périodes complètement couvertes, et la diversité des annonces ne démontre aucune compétence mobilisable.


## Contre-vérification intégrale et sensibilité aux semences

Le programme `scripts/auditer_echantillon_boamp.py` relit **l'intégralité** de l'index des avis, vérifie son empreinte, reconstitue indépendamment les mois complètement archivés et les effectifs de chaque strate, puis recalcule les rangs SHA-256 et les annonces sélectionnées. Il compare directement les objets et références d'archives, les états documentaires, les nombres de tirages et les chevauchements. Toute divergence interrompt la publication du fichier d'analyse.

La contre-vérification exécute également deux tirages supplémentaires, avec des semences distinctes et annoncées, sur le même cadre documentaire. Pour chaque réplication, elle produit le nombre de tirages communs à l'échantillon de référence et leur part, ainsi que le chevauchement attendu si les rangs des deux tirages étaient indépendants et uniformément répartis dans chaque strate. Ces valeurs documentent la sensibilité des choix individuels et la concentration des petites strates ; elles ne mesurent ni la pertinence scientifique ni une performance opérationnelle.

L'instrument emploie une autre procédure de maintien des plus petits rangs, mais conserve les règles lexicales et le même index de référence. Ce contrôle constitue donc une **vérification d'implémentation et de reproductibilité**, distincte d'une évaluation empirique indépendante de la qualité des besoins.

La publication indique explicitement que la stratification effective porte sur le mois, l'état documentaire et le domaine lexical. Même si une catégorie de marché est renseignée dans un jeu futur, ce constat ne sera jamais présenté comme une stratification par catégorie sans modification vérifiable du plan et des tests.
