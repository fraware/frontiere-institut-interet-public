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
