# Premier cas prospectif — protocole d’exécution version 1

## Objet

Le premier cas prospectif doit permettre d’observer toute la chaîne, depuis un besoin actuel jusqu’à une contribution utile, en conservant une description vérifiable de la situation avant l’intervention de FRONTIÈRE.

Le protocole complète les tickets #4, #5 et #6. Une comparaison sur un seul cas reste une comparaison opérationnelle ; elle ne suffit pas à établir un effet causal général.

## Conditions d’admission

Le cas entre dans le protocole seulement si les éléments suivants sont enregistrés avant toute recherche menée par FRONTIÈRE :

- situation actuelle délimitée ;
- résultat observable recherché ;
- responsable opérationnel ;
- indication explicite du fait que le besoin existait déjà, ou non, avant le contact avec FRONTIÈRE ;
- échéance utile ;
- voie que l’institution suivrait sans FRONTIÈRE ;
- hypothèse initiale de FRONTIÈRE ;
- au moins une preuve initiale avec sa provenance.

L’application refuse de figer l’état initial si une recherche a déjà commencé.

## Enregistrer et figer l’état initial

L’application conserve l’identité du cas, la version active du besoin et les preuves disponibles à ce moment.

Elle calcule également une empreinte SHA-256. Cette empreinte est une valeur calculée à partir du contenu enregistré. Elle permet de vérifier qu’une modification ultérieure n’a pas remplacé silencieusement l’état initial.

Le nom technique de l’événement conservé dans le journal est `CAS_PROSPECTIF_PRE_ENREGISTRE`.

Une modification ultérieure du besoin crée une nouvelle version. L’état initial historique reste consultable.

## Enregistrer la comparaison avant toute intervention

Avant que FRONTIÈRE commence sa recherche sur un cas dont l’état initial a été figé, les règles de comparaison doivent être enregistrées.

Elles précisent :

- la méthode habituellement utilisée par l’institution ;
- la méthode FRONTIÈRE ;
- le responsable de chaque recherche ;
- la mesure principale ;
- la date à laquelle le résultat sera observé ;
- la règle applicable si les deux recherches échangent une information ou une ressource ;
- les budgets de temps prévus, lorsqu’ils sont connus.

L’application calcule une seconde empreinte SHA-256 pour ces règles. Le nom technique de l’événement correspondant est `COMPARAISON_APPARIEE_PRE_ENREGISTREE`.

Tant que ces règles ne sont pas enregistrées, l’application bloque les actions qui constitueraient déjà une intervention de FRONTIÈRE : formalisation de la capacité recherchée, recherche dans le secteur public, ajout d’une ressource trouvée, évaluation d’une voie de résolution et décision d’orientation.

## Première recherche dans le secteur public

La recherche enregistre séparément :

- la méthode utilisée ;
- le périmètre examiné ;
- les sources consultées ;
- le temps humain consacré ;
- le fait que la recherche soit suffisante ou encore incomplète ;
- l’existence éventuelle d’une capacité publique pertinente ;
- la possibilité réelle de mobiliser cette capacité.

La conclusion est exprimée en toutes lettres : recherche insuffisante ; capacité publique mobilisable ; capacité publique trouvée avec obstacles de mobilisation ; ou aucune capacité publique pertinente trouvée après une recherche suffisamment approfondie.

## Mesures de la comparaison

La mesure principale recommandée pour le premier cas est le temps écoulé jusqu’à l’identification d’une ressource réellement mobilisable pour la mission.

Conserver également :

- temps humain total ;
- temps consacré à la vérification ;
- ressources utiles trouvées par une seule des deux méthodes ;
- moment et contenu des interactions éventuelles entre les deux recherches ;
- date de première contribution utile ;
- résultat observé à la date fixée.

## Vérifier l’antériorité des enregistrements

L’interface de programmation `/api/v1/episodes/{code}/preregistration` restitue l’état initial enregistré, les règles de comparaison et leurs empreintes pour les cas admissibles au prototype public.

La séquence attendue est :

```text
besoin actuel
→ preuves initiales
→ état initial enregistré et figé
→ règles de comparaison enregistrées
→ méthode habituelle et méthode FRONTIÈRE
→ ressources trouvées et vérification de leur mobilisation
→ première contribution utile
→ résultat à la date fixée
```

## Vérification de l'intégrité interne

L'interface `/api/v1/episodes/{code}/preregistration` expose aussi un objet `integrity`. Il vérifie l'empreinte du contenu de l'état initial, l'empreinte du plan de comparaison, le rattachement du plan à l'état initial et l'ordre des deux événements enregistrés.

Un contrôle absent reste inconnu. Une divergence rend `internally_consistent` faux. Cette vérification porte sur les contenus et les horodatages présents dans la même base de données. Elle ne constitue **ni une preuve d'antériorité indépendante, ni une protection contre un acteur ayant le pouvoir de réécrire simultanément les données et leurs empreintes**.

Pour attester une antériorité auprès d'un évaluateur externe, conserver en outre une empreinte datée dans un système indépendant, avec des règles de conservation et d'accès adaptées au niveau de sensibilité.

## Critère de réussite du premier cas

Le premier cas est exploitable pour l’apprentissage méthodologique si :

1. l’état initial est enregistré avant toute recherche de FRONTIÈRE ;
2. les règles de comparaison sont enregistrées avant l’intervention ;
3. les deux méthodes partent des mêmes informations initiales ;
4. les interactions entre les deux recherches sont enregistrées ;
5. le résultat est observé à une date fixée à l’avance ;
6. les limites de comparaison restent explicites.
