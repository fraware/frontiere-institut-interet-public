# EIG, Document-IA et capacités IA de l'État — vérifications publiques du 6 novembre 2026

**Statut : enquête documentaire, aucune sollicitation envoyée ou réponse reçue attestée par cette note.**  
**Périmètre : informations déjà rendues publiques par les institutions.**  
**Confidentialité : aucun contenu d'entretien, échange privé, compte rendu nominatif non publié ou donnée de candidat n'est inclus.**

## 1. Dispositifs publics déjà établis

### Entrepreneurs d'intérêt général (EIG)

La DINUM recrute des profils expérimentés de direction technique, de direction produit et de direction de l'impact. Le dispositif fonctionne désormais sans promotions annuelles. Les personnes recrutées rejoignent la DINUM en contrat de projet d'au moins un an, renouvelable, puis accomplissent une mission au sein d'une administration partenaire.

La FAQ destinée aux administrations prévoit explicitement l'internalisation du pilotage stratégique, la structuration d'une équipe et la diffusion de pratiques de développement. Ce mécanisme constitue donc **un dispositif existant à examiner avant toute proposition de fonction comparable**.

Sources primaires :
- https://eig.numerique.gouv.fr/participer/candidats/
- https://eig.numerique.gouv.fr/participer/administrations/faq
- https://eig.numerique.gouv.fr/participer/candidats/faq

**Informations manquantes :** délais de recrutement par mission, candidatures qualifiées, refus, postes effectivement occupés, charge d'intégration, capacité maintenue à la fin de mission et demandes hors périmètre EIG.

### Intelligence artificielle dans l'État (IAE)

L'équipe officielle du département IAE distingue un pôle Accompagnement IA et un pôle Socle & Produits IA. La page nomme Ishan Bhojwani à la tête du département, Nathanaël Romano comme adjoint et responsable du socle, et Elsa Le Duigou comme responsable de l'accompagnement des ministères.

L'organigramme public atteste de fonctions et d'attributions, **pas** de la disponibilité des personnes, du nombre de projets effectivement accompagnés ni de l'issue de leurs recrutements.

Sources primaires :
- https://ia.numerique.gouv.fr/l%C3%A9quipe/
- https://ia.numerique.gouv.fr/contactez-nous/

**Informations manquantes :** critères d'arbitrage entre capacités ministérielles et mutualisation, chronologie de transfert des produits, responsabilités de maintenance, besoins techniques non satisfaits et fréquence des recours à des spécialistes scientifiques.

### Document-IA

La fiche officielle présente Document-IA comme un produit d'analyse de pièces justificatives porté par ALLiaNCE et destiné à être réutilisé. Elle documente un financement initial FTAP-IA de 150 000 euros en juillet 2025, une date de construction au 15 septembre 2025 et des jalons d'évolution ultérieurs. Le dépôt du logiciel est public.

**Ce que ces sources établissent :** existence du produit, objectif de réutilisation, financement initial déclaré, dates de phases publiées et disponibilité du code.  
**Ce qu'elles ne démontrent pas seules :** durée totale de recrutement, délai entre besoin et première contribution utile, coût complet, performance réelle, statut des agents, transfert effectif de connaissances, autonomie de maintenance à douze mois.

Sources primaires :
- https://beta.gouv.fr/startups/document-ia
- https://github.com/etalab-ia/document-ia
- https://ia.numerique.gouv.fr/

### Architecture et indicateurs à interpréter avec prudence

Le dépôt de développement public décrit une API FastAPI, une exécution asynchrone appuyée sur Redis, un stockage compatible S3, un journal d'événements PostgreSQL, ainsi qu'une application d'évaluation séparée. La présence d'un module d'évaluation documente une **capacité instrumentale**, sans attester de performances de production, de seuils métier ou de validation indépendante.

La fiche beta.gouv.fr indique que **DossierFacile traite plus de 700 000 pièces justificatives mensuelles**. Cette volumétrie concerne DossierFacile, **pas le nombre établi de pièces effectivement analysées par Document-IA**. Ne pas utiliser ce chiffre comme taux d'adoption, de couverture ou d'impact causal de Document-IA.

Sources :
- https://github.com/etalab-ia/document-ia/blob/develop/README.md
- https://github.com/etalab-ia/document-ia/blob/develop/document-ia-evals/METRICS.md
- https://beta.gouv.fr/startups/document-ia

### Direction de programme IA du ministère de la Justice

Le ministère annonce la création de la direction de programme IA le 1er décembre 2025 et la nomination d'Élise Farge Di Maria à sa tête. Cette annonce officielle ne permet pas à elle seule de déduire l'effectif réellement présent en novembre 2026, les durées de recrutement ou les contributions déjà livrées.

Source primaire :
- https://www.justice.gouv.fr/actualites/espace-presse/creation-dune-direction-programme-dediee-lintelligence-artificielle-au-sein-du-ministere

### Rémunération des métiers du numérique

Le référentiel interministériel a été initié en 2019 et révisé par la circulaire du 3 janvier 2024. Il couvre 55 métiers et quatre niveaux d'expérience, avec des fourchettes de référence et des règles de contrôle budgétaire. **L'existence de ce référentiel ne prouve pas une application homogène dans chaque ministère.**

Source primaire :
- https://www.numerique.gouv.fr/offre-accompagnement/reference-remuneration-filiere-numerique/

## 2. Questions à résoudre avec des cas réels

| ID | Question | Données minimales | Cas positif ou contre-exemple |
| --- | --- | --- | --- |
| IA-01 | Un responsable technique expérimenté facilite-t-il les recrutements ? | Date d'ouverture, nombre de candidats qualifiés, durée, offres acceptées, ressources et contraintes | Administration comparable ayant recruté sans ce profil |
| IA-02 | Qu'est-ce qui subsiste à la fin d'une mission EIG ? | Équipe, budget, responsabilité d'exploitation, capacité autonome à 6 et 12 mois | Mission EIG dont la transmission a échoué |
| IA-03 | La mutualisation d'un produit préserve-t-elle une capacité ? | Dates de transfert, responsable, équipe, coûts récurrents, adoption et exploitation | Produit mutualisé sans capacité de maintenance suffisante |
| IA-04 | Quelle expertise scientifique demeure difficile à mobiliser ? | Besoin daté, domaine scientifique, recherche publique, alternatives, délai et résultat | Expertise obtenue rapidement par une coopération existante |
| IA-05 | Quel frein relève du recrutement, des systèmes ou du financement ? | Chronologie par étape, causes, durées, choix de résolution | Besoin satisfait malgré les contraintes courantes |
| IA-06 | Les conditions salariales permettent-elles d'attirer et de fidéliser les profils ? | Poste, cadre de rémunération, offres, refus, dates, motif de départ | Recrutement rapide à rémunération ordinaire |

**Règle d'analyse :** une chronologie ne suffit pas à attribuer un effet causal. Documenter simultanément le budget, le soutien hiérarchique, la visibilité de la mission, les conditions techniques et les alternatives.

## 3. Programme de vérification

1. Reconstituer un cas de recrutement réussi et un cas difficile, avec les mêmes jalons et définitions.
2. Établir un exemple de transfert vers une capacité interministérielle, en distinguant transfert de code et reprise effective des responsabilités.
3. Examiner un cas documenté de mobilisation scientifique spécialisée. Vérifier d'abord les compétences déjà disponibles dans les organismes publics.
4. Comparer, sur un besoin daté, recrutement, mobilité, prestation, coopération scientifique et mutualisation.
5. Déterminer si le dispositif déjà existant résout le cas, s'il doit être renforcé, ou si une fonction complémentaire étroite reste utile.

Les démarches de contact restent **à réaliser** tant qu'aucune preuve d'envoi n'a été enregistrée dans le registre privé approprié. Le dépôt public ne contient ni transcriptions d'entretiens ni correspondances individuelles.

## 4. Critères de clôture

- Deux épisodes contrastés vérifiables, dont un cas positif.
- Une chronologie sourcée de Document-IA jusqu'au premier usage et à la reprise opérationnelle.
- Une grille comparative des voies de résolution avec coûts, risques et délais.
- Une recherche prioritaire des capacités scientifiques publiques pour tout besoin spécialisé soumis à examen.
- Une conclusion motivée sur l'utilité marginale de FRONTIÈRE, admettant explicitement renforcer l'existant, intervention ciblée, prolongation de l'étude ou arrêt.

## 5. Rattachement aux travaux existants

- [Première vague EIG](../docs/VAGUE_1_PRISE_DE_CONTACT.md) et [issue #11](https://github.com/fraware/frontiere-institut-interet-public/issues/11).
- [Première vague IAE](../docs/VAGUE_1_PRISE_DE_CONTACT.md) et [issue #13](https://github.com/fraware/frontiere-institut-interet-public/issues/13).
- [Mobilités, réinternalisation et prestations — issue #676](https://github.com/fraware/frontiere-institut-interet-public/issues/676).
- [Comparaison des modalités scientifiques — issue #658](https://github.com/fraware/frontiere-institut-interet-public/issues/658).
- [Protocole de recherche](../docs/PROTOCOLE_V1.1.md).

**Date de consultation des pages officielles : 6 novembre 2026.** Cette note décrit les publications consultées, non la situation interne exhaustive des administrations.
