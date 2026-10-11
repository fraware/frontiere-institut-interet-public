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


## Compléments historiques indépendants

Le programme `scripts/completer_categories_boamp.py` récupère les catégories officielles de douze journées antérieures par passage. Il sélectionne les identifiants du relevé historique initial dont l'empreinte a été vérifiée, puis consulte de nouveau la source avec les seuls champs `idweb`, `dateparution` et `type_marche`.

Chaque journée est conservée séparément dans `institutionnel/besoins_publics/categories_boamp/AAAA/MM/AAAA-MM-JJ.jsonl.gz`, avec manifeste SHA-256 et heure de contrôle. La correspondance avec les identifiants du relevé initial est explicite. Les identifiants apparus ou disparus depuis ce relevé sont comptés ; les avis absents du nouveau contrôle portent une catégorie inconnue.

**Une catégorie récupérée en octobre 2026 n'est pas présumée être la catégorie qui était publiée à la date initiale de l'avis.** Les catégories ainsi observées sont documentaires et datées. L'archive BOAMP originale, son contenu et son empreinte ne sont jamais modifiés par ce traitement.

Le programme vérifie toutes les archives complémentaires existantes avant d'ajouter un nouveau lot. Les limites de taille et de pagination empêchent de publier une consultation partielle comme exhaustive. Les fichiers complémentaires et leur état sont inclus dans la publication automatisée, avec vérifications Python et conteneur. Leur nombre et leur couverture doivent être mesurés sur les exécutions réelles avant toute interprétation statistique.


## Bilan quantitatif des compléments

Le programme `scripts/analyser_complements_categories_boamp.py` publie, lors de chaque reconstruction de l'index, un bilan `bilan-categories-reobservees.json`. Il compte pour chaque mois les journées historiques initialement archivées, les journées disposant d'un complément vérifié, les identifiants d'avis initiaux couverts, les catégories effectivement retrouvées dans la nouvelle consultation et les identifiants ajoutés ou absents depuis la photographie initiale.

Il vérifie les empreintes de chaque complément et celles des archives BOAMP initiales auxquelles il se rapporte. Une fiche manquante, une archive altérée ou une journée sans source initiale interrompt la production du bilan. Le dénominateur est celui des **identifiants d'avis documentaires archivés**, jamais un nombre de marchés distincts ni un échantillon national de besoins.

Les colonnes `categories_du_dernier_etat_BOAMP_deja_dans_index` et `categories_retrouvees_lors_des_recontroles` décrivent deux observations distinctes. Elles ne doivent pas être additionnées comme s'il s'agissait d'une même photographie temporelle. Une couverture faible, même avec des catégories systématiquement retrouvées dans les journées réexaminées, interdit de généraliser les distributions aux années entières.
