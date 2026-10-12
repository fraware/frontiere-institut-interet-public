# Audit des quatre avis d'attribution non interprétés

**Corpus fixé avant correction :** 36 avis sélectionnés sans consultation des résultats, empreinte ordonnée `40f791c35adcdc67d69bb933e873b0efaa7b24dd0c74958474dc6272b94242c8`. Relevé primaire du 12 octobre 2026 : [exécution GitHub 38196898276](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38196898276), archive 11723693379.

La première lecture donnait 12 avis d'attribution eForms interprétés (23 résultats de lots attribués), 20 avis sans résultat d'attribution dans la notice interrogée et 4 formulaires d'attribution non interprétés. Aucun lot sans offre n'avait été établi parmi les lots couverts. Il ne s'agit pas d'une mesure de précision, ni d'un jugement indépendant.

| Avis | Formulaire et cause | Interprétation admissible après correction |
| --- | --- | --- |
| 25-121801, France Travail Occitanie | FNSimple, texte libre : « Lots 1 et 2 attribués à ECLIPSE ISTEC SAS » | Transcription littérale uniquement, **zéro lot automatiquement certifié** |
| 25-121097, Cerema | MAPA : `attribution/resultat/attribue`, titulaire LIBRICIEL SCOP, une offre et date 2025-10-16 | Attribution déclarée sans numéro de lot déterminable ; **aucun lot créé artificiellement** |
| 26-16578, département des Ardennes | eForms : double occurrence de `t-esubm=2` dans un même lot | Une seule mesure de deux soumissions, deux chemins de provenance conservés ; contradiction si les valeurs diffèrent |
| 26-53532, SDIS 34 | eForms : quatre lots attribués, trois contrats par lot | Quatre résultats de lots avec **trois références de contrats distinctes par lot**, aucun contrat unique inventé |

Le parseur eForms conserve la propriété antérieure `contrat_reference` uniquement lorsque le lot ne référence qu'un seul contrat. Sa nouvelle propriété `contrats_references` contient tous les identifiants annoncés par le formulaire. Les dates d'attribution et d'émission ne sont toujours pas assimilées à la première contribution utile.

Les sources MAPA et FNSimple sont conservées séparément dans `observations_hors_lots`. Un texte libre d'attribution ne devient pas une preuve structurée, et une attribution MAPA dépourvue d'identifiant de lot ne crée aucun résultat de lot. Les contradictions ou variantes de format non contrôlables restent à interprétation inconnue.

L'évaluation **indépendante** n'a pas encore eu lieu : les catégories extraites par le programme sont des préqualifications automatiques. Les cas pilotes, l'échantillon original et sa semence ne sont pas modifiés. Le nouveau prélèvement de contrôle enrichi en événements négatifs devra être publié séparément et ne devra pas servir à une estimation représentative des marchés français.
