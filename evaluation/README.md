# Jeu réservé — version 1

Ce dossier contient les éléments publics nécessaires à une évaluation indépendante de FRONTIÈRE.

## Fichiers

- `jeu_reserve_v1_questions.json` contient les dix questions ;
- `jeu_reserve_v1_manifeste.json` contient l'empreinte cryptographique du fichier privé de référence ;
- `CONSIGNES_EVALUATEUR.md` décrit les règles de l'évaluation ;
- `modele_reponses.json` donne la structure attendue des réponses.

Les réponses de référence, leurs sources et les voies attendues sont conservées hors du dépôt public.

## Procédure

1. remettre les questions et les consignes à un évaluateur qui n'a pas vu les références ;
2. obtenir un fichier de réponses complet ;
3. vérifier sa structure avec `scripts/verifier_reponses_jeu_reserve.py` ;
4. figer le fichier de réponses ;
5. seulement ensuite, comparer les réponses au fichier privé de référence avec `scripts/evaluer_jeu_reserve.py`.

L'empreinte cryptographique garantit que le fichier privé utilisé pour l'évaluation correspond à celui préparé avant les réponses de l'évaluateur.

## Contrôles d'intégrité des réponses

La vérification préalable contrôle les champs obligatoires, les identifiants de cas, les types des listes, les valeurs numériques finies et les durées positives ou nulles. Le programme d'évaluation refait cette vérification avant de lire les résultats.

Le rapport produit par `scripts/evaluer_jeu_reserve.py` conserve désormais les empreintes SHA-256 des **références privées** et du **fichier de réponses évalué** (`empreinte_sha256_reponses`). Pour préserver une attestation d'antériorité, l'empreinte des réponses doit être enregistrée auprès d'un tiers ou sur un support indépendant **avant** ouverture des références privées. La simple présence d'une empreinte dans le rapport généré après évaluation n'établit pas cette antériorité.

Ces contrôles ne vérifient ni l'exactitude des sources citées, ni l'indépendance de l'évaluateur, ni la pertinence des ressources nommées. Ces dimensions exigent une vérification humaine séparée.

## Gel des réponses avant ouverture des références

Une fois le fichier de réponses complet et validé, l'évaluateur ou le responsable indépendant exécute :

```bash
python scripts/geler_reponses_jeu_reserve.py \
  --questions evaluation/jeu_reserve_v1_questions.json \
  --reponses /chemin/prive/reponses_analyste.json \
  --manifeste /chemin/prive/gel_analyste.json
```

Le programme écrit un nouveau manifeste sans écraser un fichier existant. Il conserve les empreintes SHA-256 des questions et des réponses, la méthode et la date locale d'enregistrement. Le manifeste ne contient pas les réponses individuelles.

Pour vérifier ultérieurement l'identité des fichiers, reprendre la commande avec `--verifier`. Conserver le fichier de réponses et le manifeste dans un emplacement approprié ; **communiquer l'empreinte du manifeste à un tiers indépendant avant de consulter les références privées**. Conserver la preuve de réception datée. Cette attestation est une étape procédurale humaine : elle n'est pas automatisée par le présent programme.

Lors de la correction, `scripts/evaluer_jeu_reserve.py` exige désormais `--gel-reponses /chemin/prive/gel_analyste.json`. Il refuse un fichier modifié après le gel, y compris si ses champs restent valides. Le rapport conserve aussi l'empreinte SHA-256 du manifeste de gel réellement présenté. La procédure d'évaluation doit employer pour `--questions` le même fichier octet pour octet que celui utilisé pour créer le gel.

Exemple de correction locale **après attestation extérieure** :

```bash
python scripts/evaluer_jeu_reserve.py \
  --questions evaluation/jeu_reserve_v1_questions.json \
  --manifeste evaluation/jeu_reserve_v1_manifeste.json \
  --references /chemin/prive/references.json \
  --reponses /chemin/prive/reponses_analyste.json \
  --gel-reponses /chemin/prive/gel_analyste.json \
  --sortie /chemin/prive/rapport_analyste.json
```

La comparaison avec `scripts/evaluer_jeu_reserve.py` n'est autorisée qu'après cette étape. Pour chaque méthode évaluée, conserver un manifeste distinct ; ne jamais publier les références privées dans le dépôt.

## Comparer les trois méthodes après correction

Une fois les trois fichiers de réponses figés, les références ouvertes par le responsable autorisé et les trois rapports individuels produits hors du dépôt public, exécuter :

```bash
python scripts/comparer_methodes_jeu_reserve.py \
  --rapports /chemin/prive/rapport_analyste.json /chemin/prive/rapport_assistant.json /chemin/prive/rapport_frontiere.json \
  --sortie /chemin/prive/comparaison_appariee.json
```

Le programme refuse les méthodes répétées, les codes de cas différents et les empreintes de référence différentes. Il calcule séparément les scores moyens des voies et des formes de ressources, les temps humains, le nombre de durées calendaires observées et les écarts sur les mêmes cas. Les scores manquants sont exclus seulement des paires correspondantes ; les durées totales sont inconnues si un cas n'a pas de durée mesurée.

**Limites :** cette comparaison est descriptive. Elle ne mesure ni la pertinence des ressources nommées, ni la qualité réelle des preuves citées, ni la mobilisabilité effective. Ces dimensions exigent une évaluation indépendante supplémentaire. Ne publier aucun résultat tant que les trois méthodes n'ont pas été évaluées.

## Vérification de cohérence des rapports

Le programme de correction et le programme de comparaison exigent un chemin de sortie **extérieur au dépôt public**. Ils refusent l'écrasement automatique d'un rapport déjà présent.

Le comparateur vérifie, avant calcul, la cohérence des trois rapports individuels : appartenance aux méthodes prévues, empreintes des réponses, des références et des gels, exactitude des scores harmoniques, validité des durées et correspondance entre totaux, moyennes et observations par cas.

L'analyste manuel est une référence de comparaison explicitement désignée dans le protocole. Les écarts sont rapportés pour **assistant généraliste contre analyste**, **FRONTIÈRE contre analyste** et **FRONTIÈRE contre assistant généraliste**, sur les seules paires où la mesure est définie. L'ordre des chemins passés au programme n'influence plus la méthode de référence.

Le programme exige par défaut **dix cas**. L'option `--nombre-cas-attendus` permet uniquement les essais artificiels ou les études distinctes avec une taille préalablement définie. Une absence de données demeure inconnue et ne vaut pas un score nul.

Les contrôles internes ne prouvent pas l'origine indépendante des données. Toute attestation d'antériorité et toute correction qualitative restent consignées séparément.

## Préparer les trois séances indépendantes

Le protocole [d'exécution indépendante](PROTOCOLE_SESSIONS_INDEPENDANTES_V1.md) fixe les conditions d'admission, les trois méthodes, le journal de séance, le budget commun et les précautions contre la divulgation des références.

Le programme `scripts/preparer_sessions_jeu_reserve.py` prépare **hors du dépôt public** trois dossiers contenant des questions identiques, des consignes propres à chaque méthode, un fichier de réponses vide et un journal de séance vide. Il exige un budget explicite, refuse l'écrasement d'une séance et n'ouvre aucune référence privée.

Les dossiers produits doivent être transmis aux opérateurs dans un environnement privé. Un manifeste commun identifie les questions, les conditions de préparation et les empreintes des documents. Le responsable enregistre ce manifeste auprès d'un tiers avant le début de l'expérience.

## Relecture indépendante des chronologies historiques

Le [protocole de double relecture des sources](PROTOCOLE_RELECTURE_SOURCES_HISTORIQUES_V1.md) définit la vérification indépendante des **45 événements** du corpus actif. Les scripts `preparer_relecture_evenements.py` et `consolider_relecture_evenements.py` produisent des dossiers identiques, des jugements vierges, un manifeste d'intégrité et un bilan conservant tous les désaccords. Le paquet présenté aux relecteurs n'inclut pas les conclusions ni les réserves préalables de l'assistant.

Ce dispositif est **préparatoire** : aucun jugement humain indépendant n'est encore disponible et aucun accord entre relecteurs n'est revendiqué. Les fichiers individuels et leurs empreintes doivent rester dans un environnement privé, avec preuve d'antériorité extérieure.

## Recrutement des deux relecteurs documentaires

La [charte de recrutement et d’indépendance](CHARTE_RECRUTEMENT_RELECTEURS_V1.md) explicite les qualifications, conflits d'intérêts, déclarations d'exposition préalable, choix des rôles, conditions d'engagement et séquence de gel à fixer **avant** le premier jugement humain. La [fiche de mission](FICHE_MISSION_RELECTURE_V1.md) décrit les 45 assertions, le livrable attendu et une invitation de premier contact réutilisable.

Ces documents ne déclarent ni relecteur recruté, ni rémunération financée, ni consentement obtenu, ni message envoyé. Les identités et conditions privées de participation doivent être conservées hors du dépôt public, et la disponibilité des candidats doit être vérifiée par prise de contact réelle. Le suivi d'exécution est la [tâche n° 84](https://github.com/fraware/frontiere-institut-interet-public/issues/84).


## Identité des questions dans les trois rapports réservés

Chaque rapport individuel issu de `scripts/evaluer_jeu_reserve.py` contient désormais `empreinte_sha256_questions`, l'empreinte exacte du fichier de questions utilisé pour la méthode concernée. Le programme de comparaison exige que les trois rapports présentent **la même empreinte des questions**, en plus d'une même empreinte de références privées et du même ensemble de codes H01–H10. Deux fichiers peuvent contenir les mêmes identifiants tout en décrivant des besoins différents ; comparer leurs scores constituerait un rapprochement invalide.

Les anciens rapports dépourvus de cette empreinte ne satisfont pas au contrôle renforcé. Avant toute analyse, retrouver les fichiers originaux, leurs manifestes et les questions, puis **reproduire une correction autorisée** à partir des réponses restées inchangées et de leurs gels vérifiés ; ne jamais compléter une empreinte manquante par estimation ni modifier silencieusement un rapport original.

Ce contrôle établit l'identité des fichiers de questions utilisés lors de la correction ; il ne prouve pas, à lui seul, que les trois opérateurs ont effectivement reçu et respecté les mêmes consignes, tâche qui reste couverte par les journaux et la procédure indépendante.
