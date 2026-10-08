# Vérification documentaire ciblée — 8 octobre 2026

## Portée

Cette note enregistre une relecture des **sources officielles** relatives à deux chronologies du corpus, S001 (France Compétences) et S016 (IGN). Les versions antérieures restent disponibles. La note précise les écarts constatés entre la date d'un fait, la date à laquelle il a été rapporté et la date de publication ou d'approbation du document.

Il s'agit d'un contrôle documentaire ciblé. Les autres événements des dix chronologies restent à examiner dans le `registre_verification_evenements_v1.json`. Cette note ne prétend ni mesurer un délai de résolution manquant ni valider l'ensemble des cas.

## S016 — IGN : date attribuée aux 126 recrutements

**Enregistrement antérieur :** `donnees/chronologies_v3.json`, événement `S016-E02`, daté du 5 juillet 2024. Il attribue à une réunion du conseil d'administration l'annonce de 126 recrutements sur 150, dont 30 dans les métiers des données et de l'intelligence artificielle.

**Source primaire examinée :** IGN, *Délibération du conseil d'administration du 5 juillet 2024, n° 2024-04, approuvant le procès-verbal de la séance du 15 mars 2024* :

https://www.ign.fr/publications-de-l-ign/institut/informations_legales_administratives/de_deliberations_ca_5_juillet_2024.pdf

- **Page 1 du fichier PDF :** la séance du 5 juillet approuve le procès-verbal **du 15 mars 2024**.
- **Page 21 du fichier PDF (page 20 du procès-verbal) :** M. Éric Kolb indique 126 recrutements réalisés sur un objectif de 150, dont 30 dans les métiers des données et de l'intelligence artificielle.
- **Page 22 du fichier PDF (page 21 du procès-verbal) :** le nombre de 126 est qualifié de valeur **observée fin 2023** ; la discussion précise qu'il inclut les mobilités ou recrutements internes ainsi que les recrutements externes.

**Conclusion :** le chiffre de 126 est bien soutenu. La date « 5 juillet 2024 » se rapporte à l'approbation du compte rendu, et non à la séance qui a présenté ce résultat. La chronologie doit distinguer :

1. **fin 2023 :** état déclaré de l'indicateur (126 recrutements, internes et externes) ;
2. **15 mars 2024 :** présentation au conseil d'administration ;
3. **5 juillet 2024 :** approbation du procès-verbal.

**Formulation proposée pour une future version :** « Lors de la séance du conseil d'administration du 15 mars 2024, l'IGN présente un indicateur de 126 recrutements réalisés sur un objectif de 150, dont 30 dans les métiers de la science des données et de l'intelligence artificielle. Le document précise qu'il s'agit d'une valeur observée fin 2023 ; le procès-verbal est approuvé le 5 juillet 2024. »

Le rapport chronologique antérieur reste conservé et cette note constitue la trace explicite du contrôle.

## S001 — France Compétences : date du témoignage et date du rapport

**Enregistrement antérieur :** `donnees/chronologies_v3.json`, événements `S001-E01`, `S001-E02` et `S001-E03`.

**Source primaire 1 :** Sénat, commission d'enquête sur les agences de l'État, audition de Stéphane Lardy le **3 avril 2025** :

https://www.senat.fr/compte-rendu-commissions/20250331/ce_agences.html

La page place l'audition au 3 avril 2025. Dans son témoignage, Stéphane Lardy décrit la perte de maîtrise interne du langage R et indique que la situation perdure **depuis octobre précédent**, tandis qu'un recrutement spécialisé est recherché.

**Source primaire 2 :** Sénat, rapport de commission d'enquête n° 807, tome I, déposé le **1er juillet 2025**, section sur les fonctions support :

https://www.senat.fr/rap/r24-807-1/r24-807-121.html

Le rapport reproduit l'exemple et indique que sa source est constituée des réponses orales de Stéphane Lardy en audition.

**Conclusion :** le constat d'une difficulté existant depuis octobre 2024 et encore rapportée lors de l'audition du 3 avril 2025 est soutenu par la source primaire. La publication du rapport le 1er juillet 2025 ne constitue pas une nouvelle observation indépendante de l'état exact de la capacité en juillet.

**Formulation proposée pour une future version de `S001-E03` :** « Le 1er juillet 2025, le rapport de la commission d'enquête reprend le témoignage du 3 avril concernant la perte de capacité interne, la rareté des profils et la rémunération peu compétitive. Le rapport ne fournit pas de date nouvelle de rétablissement de la capacité. »

La date effective de résolution, si elle a eu lieu, demeure inconnue et reste une demande d'exécution à adresser à l'établissement.

## S016 — IGN : audition sénatoriale du 12 novembre 2024

**Source primaire :** Sénat, délégation à la prospective, audition de Sébastien Soriano le **12 novembre 2024** :

https://www.senat.fr/compte-rendu-commissions/20241111/pro_2024_11_12.html

Dans sa réponse relative aux recrutements, le directeur général indique un objectif de 150 personnes formées ou recrutées, 156 déjà recrutées et formées au moment de l'audition, et l'atteinte de l'objectif de 30 spécialistes de la science des données.

L'événement `S016-E04`, daté du 12 novembre 2024, est cohérent avec cette source. Les 126 indiqués dans le procès-verbal antérieur et les 156 présentés en novembre ne doivent pas être confondus avec des embauches exclusivement externes.

## Règles pour la suite

- Conserver séparément la date du fait, celle de sa constatation et celle de publication du document.
- Préserver les formulations d'origine dans l'historique et tracer toute modification d'un événement.
- Vérifier la catégorie exacte d'effectifs ou recrutements avant de comparer des nombres de périodes différentes.
- Lier chaque fait à un document, à un passage identifiable et à son degré d'appui ; ne pas considérer une source générique associée au signal comme preuve de chaque événement.
- Maintenir les observations non couvertes par les sources en état « à vérifier ».

**Résultats de ce contrôle :** une attribution de date à corriger dans S016, une ambiguïté d'interprétation temporelle à lever dans S001, et confirmation de la cohérence de l'audition S016 du 12 novembre 2024. Aucun nouveau délai de mobilisation n'est établi.
