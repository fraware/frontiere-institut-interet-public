# Cas prospectif — protocole d’exécution version 1

## Objet

Le premier cas prospectif doit permettre d’observer la chaîne entière depuis un besoin actuel jusqu’à une contribution utile, tout en préservant un point zéro antérieur à l’intervention de FRONTIÈRE.

Ce protocole complète les tickets #4, #5 et #6. Il ne transforme pas une comparaison opérationnelle en estimation causale.

## Condition d’admission

Un cas entre dans le protocole prospectif seulement si les éléments suivants sont enregistrés avant toute recherche menée par FRONTIÈRE :

- situation actuelle délimitée ;
- résultat observable recherché ;
- responsable opérationnel ;
- qualification explicite de la préexistence du besoin par rapport au contact avec FRONTIÈRE ;
- échéance utile ;
- plan que l’institution suivrait sans FRONTIÈRE ;
- hypothèse initiale de FRONTIÈRE ;
- au moins une preuve initiale avec provenance.

Le logiciel refuse le scellement prospectif lorsqu’une recherche a déjà commencé.

## Scellement du point zéro

L’action `/episodes/{code}/prospective/lock` enregistre un événement `CAS_PROSPECTIF_PRE_ENREGISTRE`.

Le contenu canonique comprend l’identité du cas, la version active du besoin et les preuves disponibles au moment du scellement. Une empreinte SHA-256 du point zéro est conservée dans le journal d’audit.

Une modification ultérieure du besoin passe par une nouvelle version. Le point zéro historique reste inchangé.

## Comparaison appariée

Avant toute intervention de FRONTIÈRE sur un cas prospectif scellé, un plan apparié est obligatoire.

Le plan fixe :

- la méthode habituelle ;
- la méthode FRONTIÈRE ;
- le responsable de chaque voie ;
- la mesure principale ;
- la date d’observation ;
- la règle gouvernant les interactions entre les deux recherches ;
- les budgets de temps prévus lorsque ceux-ci sont définis.

Le plan reçoit sa propre empreinte SHA-256 et l’événement `COMPARAISON_APPARIEE_PRE_ENREGISTREE`.

Après scellement prospectif et avant ce second événement, l’application bloque la compilation de la requête de capacité, la recherche publique, l’enregistrement de ressources, l’évaluation de voies et la décision d’orientation.

## Recherche publique prioritaire

La première recherche documente séparément :

- la méthode ;
- le périmètre ;
- les sources consultées ;
- le temps analyste ;
- la suffisance de la recherche ;
- l’existence d’une capacité publique pertinente ;
- sa mobilisabilité.

La conclusion reste l’une des quatre classes déjà définies :

- P0 : recherche insuffisante ;
- P1 : capacité publique trouvée et mobilisable ;
- P2 : capacité publique trouvée, mobilisation difficile ;
- P3 : aucune capacité publique pertinente trouvée après une recherche jugée suffisante.

## Mesures de la comparaison

Le point de comparaison principal doit être fixé avant recherche. La mesure recommandée pour le premier cas est le temps jusqu’à une ressource réellement mobilisable pour la mission.

Conserver également :

- temps humain total ;
- temps de vérification ;
- ressources utiles trouvées exclusivement par une méthode ;
- moment et contenu des éventuelles interactions entre les deux voies ;
- première contribution utile ;
- résultat observé à la date fixée.

La portée d’un seul cas reste descriptive et opérationnelle.

## Preuve d’antériorité

L’API `/api/v1/episodes/{code}/preregistration` expose, pour les cas admissibles au prototype public, les événements de pré-enregistrement et leurs empreintes.

La séquence recherchée est :

```text
besoin actuel
→ preuves initiales
→ point zéro prospectif scellé
→ plan apparié scellé
→ recherche habituelle et recherche FRONTIÈRE
→ ressources et mobilisabilité
→ première contribution utile
→ résultat à la date fixée
```

## Critère de réussite du premier cas

Le premier cas est exploitable pour l’apprentissage méthodologique si :

1. le point zéro précède toute recherche de FRONTIÈRE ;
2. le plan apparié précède l’intervention ;
3. les deux méthodes partent des mêmes informations initiales ;
4. les interactions sont enregistrées ;
5. le résultat est observé à une date fixée à l’avance ;
6. les limites de comparabilité restent explicites.
