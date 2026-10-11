# Catégorie de marché BOAMP — correction du schéma de données

## Diagnostic réel

Le diagnostic du 11 octobre 2026 sur cent notices officielles récentes a établi que le champ `type_marche` était transmis sous forme de **liste JSON dans cent cas sur cent**, comprenant 65 listes `["SERVICES"]`, 26 listes `["FOURNITURES"]` et 9 listes `["TRAVAUX"]`. L'ancien normaliseur acceptait uniquement une chaîne de caractères et enregistrait systématiquement une valeur absente pour ces cent notices.

L'index historique constitué avant cette correction contient **197 640 valeurs de catégorie absentes sur 197 640 avis**. Cette lacune ne démontre aucune absence de catégorie dans la source officielle : le défaut appartient à la transformation des données.

## Correction et préservation de la série temporelle

La fonction `categorie_marche_officielle` accepte une chaîne ou une liste portant exactement une des trois catégories connues. Une liste ambiguë ou une valeur étrangère au schéma produit une catégorie non renseignée, au lieu d'en choisir arbitrairement une.

Les nouveaux lots d'archives historiques sont désormais produits avec la version `liste_v2`, inscrite dans leur manifeste quotidien. Les archives antérieures, dont les manifestes ne portent pas ce marqueur, restent des **photographies normalisées selon l'ancien schéma**.

Le contrôleur de révisions applique la même version de normalisation que celle du relevé d'origine : les différences introduites par un changement de logiciel ne doivent jamais être confondues avec des modifications réellement observées dans les données officielles. Les tests hors connexion vérifient la stabilité des relevés anciens et nouveaux face à une même notice `["SERVICES"]`.

Cette première correction porte sur les futures collectes. **Elle ne restaure pas encore les catégories manquantes des 197 640 notices anciennes**. Leur restauration exige un réexamen contrôlé des données officielles et la conservation des informations de provenance et de date du complément. Il serait incorrect de réécrire silencieusement les archives immuables.

## Conséquence pour l'analyse

Tant qu'une période n'est pas intégralement enrichie, la comparaison statistique par catégorie de marché reste limitée aux valeurs effectivement renseignées. L'échantillonnage historique conserve pour l'instant ses strates par mois civil, état documentaire et domaine lexical ; il n'annonce aucune stratification par catégorie de marché.

Source du diagnostic : procédure `Diagnostic des champs techniques BOAMP` du dépôt, exécution du 11 octobre 2026, avec comptes agrégés et sans copie du contenu intégral des avis.
