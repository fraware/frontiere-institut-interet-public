# Données associatives : cadrage de faisabilité (30 octobre 2026)

**Statut :** recherche documentaire préliminaire. Document public, établi à partir de sources officielles. Aucune enquête auprès d'une administration, autorisation d'accès à des données restreintes ni mission commandée n'est réputée acquise.

## Question
Quelle part des financements attribués aux associations est identifiable dans les systèmes publics existants ? Quelles données supplémentaires seraient nécessaires pour décrire les services rendus et évaluer leurs résultats ?

L'analyse sépare **demande de subvention**, **décision d'attribution**, **versement**, **marché public**, **dépense fiscale**, **don privé** et **service effectivement fourni**. Les définitions et populations sont différentes ; aucun montant total n'est construit par addition de ces postes.

## Infrastructures publiques existantes

1. [Data.Subvention — présentation](https://beta.gouv.fr/startups/data-subvention.html). Service conduit depuis janvier 2022 ; comité du 18 juin 2026 : priorités annoncées pour l'exhaustivité, les usages et la pérennité du service. Portail et API existants. Les informations rassemblent notamment Chorus, Osiris et Fonjep.
2. [API Data.Subvention — périmètre](https://dashboard.entreprise.api.gouv.fr/catalogue/data_subvention/subventions). D'après la fiche officielle consultée le 30 octobre 2026, **100 % des demandes de subventions de l'État** et **100 % des paiements Chorus associés**, **45 % des demandes des collectivités** (sans leurs paiements) et **4 % des demandes des opérateurs et caisses**. Ces dénominateurs ne mesurent pas toute la dépense associative nationale et sont propres aux fournisseurs et champs du service.
3. [Data.Subvention — documentation et règles d'accès](https://datasubvention.beta.gouv.fr/api/) et [spécification API](https://api.datasubvention.beta.gouv.fr/docs/). Des points d'accès sont publics ; d'autres données et fonctions exigent une habilitation. Ne jamais traiter l'existence d'un point d'accès documenté comme un droit d'accès général.
4. [Data.Subvention — sources](https://datasubvention.beta.gouv.fr/nos-donnees/). Associations et établissements, demandes, projets, versements, pièces et engagements ; fréquences et couvertures hétérogènes.
5. [DILA — API annonces officielles et comptes annuels des associations](https://www.data.gouv.fr/dataservices/api-annonces-officielles-et-comptes-annuels-des-associations). Source complémentaire des publications et des comptes déposés, avec couverture dépendante de l'obligation de publication.
6. [Comptes publiés de Break Poverty](https://breakpoverty.com/rapports-d-activite/) : exemple de documents financiers individuels qui n'établissent pas la couverture du secteur entier.

## Obstacles méthodologiques

- **Double comptage :** engagements, versements et dépenses budgétaires ne doivent pas être additionnés ; paiements et subventions peuvent référencer une même opération.
- **Identité :** tracer la relation association (RNA/SIREN) – établissement (SIRET) et les réorganisations, avec contrôle des faux rapprochements.
- **Dépenses fiscales :** ne pas présumer l'accès aux dossiers individuels de dons ou des contribuables.
- **Commande publique :** distinguer titulaires de marchés, acheteurs et sous-traitance, ainsi que les montants engagés et payés.
- **Production :** une mesure de financement ne mesure ni nombre de places ni qualité des services. Définir les unités de production, les bénéficiaires, les contrôles de qualité, les périodes et les comparateurs.
- **Causalité :** coût par service, coût budgétaire, valeur sociale et effet causal sont des objets distincts. Les effets exigent un protocole d'identification approprié.
- **Intelligence artificielle :** toute extraction et tout rapprochement automatique font l'objet d'une évaluation sur échantillon indépendant, avec précision, rappel, calibration d'erreurs et revue des cas ambigus.

## Protocole de décision

1. Constituer une table de sources avec fournisseur, champ, unité, dates, droits, couverture, identifiants, cadence et URL officielle.
2. Choisir un seul territoire/secteur disposant de données légalement accessibles et d'unités de services explicites.
3. Reconstituer un petit échantillon de financements et produire des liens sourcés entre entité, décision, paiement et service, avec cas négatifs.
4. Comparer le produit aux fonctions de Data.Subvention : préciser les données/résultats que le dispositif existant ne traite pas déjà.
5. Conclure par **poursuite ciblée / réorientation vers un outil public existant / besoin indéterminé / arrêt**.

**Garde-fou :** le chiffre médiatique de « 60 milliards » est une hypothèse de discussion ; ni son périmètre ni sa décomposition ne sont validés dans ce cadrage. Ne publier aucun chiffre consolidé national sans définition et audit des sources.

## Suivi dans le dépôt

- [#651](https://github.com/fraware/frontiere-institut-interet-public/issues/651) : audit des données et des accès.
- [#652](https://github.com/fraware/frontiere-institut-interet-public/issues/652) : dispositifs publics existants de mobilisation scientifique.
- [#653](https://github.com/fraware/frontiere-institut-interet-public/issues/653) : reconstitution financière sur documents publiés.

Ce document constitue un cadrage, pas le résultat des tests d'ingestion, des vérifications sur échantillon, ni une étude d'impact.
