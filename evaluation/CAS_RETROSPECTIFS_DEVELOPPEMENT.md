# Cas rétrospectifs de développement — version 1

Cet exercice sert à comparer plusieurs méthodes sur douze situations historiques issues du corpus public.

## Principe

Chaque méthode reçoit uniquement :
- `cas_retrospectifs_developpement_v1_questions.json` ;
- `categories_comparaison_v1.json` ;
- `cas_retrospectifs_developpement_v1_modele_reponses.json`.

Le fichier `cas_retrospectifs_developpement_v1_references.json` reste fermé jusqu'au gel des réponses.

## Déroulement

1. choisir une méthode ;
2. répondre aux douze cas ;
3. vérifier que seules les catégories admises ont été utilisées ;
4. figer le fichier de réponses ;
5. comparer les réponses aux références historiques ;
6. examiner les écarts cas par cas.

## Vérification

```bash
python scripts/verifier_reponses_retrospectives.py \
  --questions evaluation/cas_retrospectifs_developpement_v1_questions.json \
  --categories evaluation/categories_comparaison_v1.json \
  --reponses reponses.json
```

## Comparaison avec les références

```bash
python scripts/evaluer_cas_retrospectifs.py \
  --references evaluation/cas_retrospectifs_developpement_v1_references.json \
  --reponses reponses.json \
  --sortie resultats.json
```

Les résultats sur ces douze cas servent au développement. Ils ne constituent pas une preuve indépendante de généralisation.
