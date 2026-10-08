# Exécution indépendante du jeu réservé — protocole v1

**État : préparation.** Aucun résultat indépendant n'est encore enregistré. Ce document fixe la procédure à suivre avant d'exécuter les comparaisons. Il complète `CONSIGNES_EVALUATEUR.md`, `README.md` et `docs/EVALUATION_TECHNIQUE_V0.5.md`.

## 1. Question et périmètre

Comparer sur les dix questions H01–H10, sans accès aux références privées, trois méthodes : recherche manuelle compétente, assistant généraliste disposant de recherche en ligne, et procédure FRONTIÈRE menée avec son logiciel et une vérification humaine.

Cette expérience évalue la qualité de l'orientation et des formes de ressources proposées au regard de références historiques. **Elle ne démontre pas à elle seule la disponibilité actuelle, la mobilisabilité ou l'effet institutionnel de FRONTIÈRE.** Les formulations des questions peuvent être reconnues dans des sources historiques ; cette fuite possible doit être mesurée et signalée.

## 2. Responsabilités et prévention des conflits

- **Responsable d'étude :** arrête les conditions avant la première réponse, conserve les preuves d'antériorité et contrôle les écarts.
- **Trois opérateurs de méthode :** suivent chacun une condition prédéfinie. Une personne ne doit pas passer d'une méthode à une autre sur ces dix cas au cours de cette première étude.
- **Détenteur des références privées :** conserve hors du dépôt le fichier de référence, vérifie son empreinte publique et n'accède aux réponses qu'après leur gel.
- **Évaluateur de la qualité des preuves :** juge en aveugle, dans un second temps, si les sources soutiennent les propositions et si les ressources sont véritablement pertinentes.

Une personne ayant consulté les références, des notes de conception des cas ou leur origine historique ne peut être présentée comme évaluateur indépendant et aveugle. Le personnel ayant construit FRONTIÈRE peut opérer l'outil dans la condition FRONTIÈRE, à condition de déclarer ce rôle ; la comparaison devra préciser le biais possible lié à cette expertise.

## 3. Conditions à fixer avant la première séance

1. **Périmètre :** H01 à H10, une réponse par méthode et par cas ; mêmes questions initiales.
2. **Mesures :** score harmonique des voies comme mesure principale descriptive ; score des formes de ressource, temps humain direct, temps de vérification, durée écoulée et examen qualitatif des sources comme mesures complémentaires. Aucune note composite.
3. **Budget :** même plafond de temps par cas, choisi et consigné avant ouverture des questions aux opérateurs ; il peut être calibré exclusivement sur le jeu de développement. Ne pas confondre plafond et durée mesurée.
4. **Ordre :** même ordre H01–H10 pour les trois méthodes dans cette version. Les effets d'ordre et de fatigue sont une limite explicite.
5. **Outils :** relever la version exacte du logiciel FRONTIÈRE, celle de l'assistant généraliste, les accès à la recherche en ligne, les éventuels outils supplémentaires et le coût de leur utilisation.
6. **Arrêt :** à l'expiration du budget, rendre l'état des travaux, y compris les propositions incomplètes ; ne pas laisser un autre opérateur compléter la réponse.
7. **Recherche d'origine :** interdiction explicite de rechercher le corrigé, le dépôt, ses discussions ou les formulations exactes pour identifier les cas historiques. Consigner néanmoins toute découverte fortuite d'une source révélant la solution.
8. **Interactions :** aucun partage d'informations, de sources ou de réponses entre les trois méthodes avant gel de la dernière réponse.

Le plan, le budget, l'identité des opérateurs et les règles de déviation doivent être déposés auprès d'un tiers indépendant avant le démarrage. Les informations nominatives demeurent dans un espace privé.

## 4. Préparer les dossiers sans divulguer les références

Depuis la racine du dépôt, choisir un **chemin de sortie extérieur au dépôt public** et un budget arrêté à l'avance, puis exécuter :

```bash
python scripts/preparer_sessions_jeu_reserve.py \
  --questions evaluation/jeu_reserve_v1_questions.json \
  --modele evaluation/modele_reponses.json \
  --sortie /chemin/prive/sessions_etude_001 \
  --identifiant-session etude_001 \
  --budget-minutes-par-cas 25
```

**La valeur 25 minutes est uniquement un exemple de commande.** Le budget réel doit résulter d'une décision consignée avant lancement. Le programme refuse d'écrire à l'intérieur du dépôt public ou d'écraser une sortie existante.

Il produit un `manifest_preparation.json` et trois dossiers : `analyste/`, `assistant_generaliste/`, `frontiere/`. Chaque dossier contient les mêmes questions épurées de métadonnées inutiles, des consignes propres à la méthode, un modèle vierge de réponse et un journal de séance vierge. Ni les références privées ni leurs corrections ne sont lues.

Le responsable d'étude conserve le manifeste et transmet son empreinte à un tiers. L'empreinte locale ne démontre pas, seule, l'antériorité.

## 5. Exécuter les sessions

Pour chaque cas, renseigner le journal de séance privé : heure réelle du début et de la fin, temps intellectuel humain direct, temps de vérification, versions des outils, accès au réseau, sources utilisées, interruptions, anomalies, dépassements de budget et reconnaissance fortuite d'un cas historique.

Les réponses doivent conserver les mêmes codes et les mêmes structures, avec des listes vides lorsqu'aucune proposition n'est suffisamment justifiée. La variable `duree_secondes` correspond au temps écoulé de la séance ; `minutes_analyste` et `minutes_verification` mesurent le temps humain, sans considérer les temps de calcul comme du travail humain.

Si une réponse est manquante, ne jamais inventer une valeur. Une séance interrompue doit être signalée au responsable et traitée selon une règle décidée avant toute correction.

## 6. Geler les trois réponses avant correction

Valider chaque fichier avec `scripts/verifier_reponses_jeu_reserve.py`. Puis générer, pour chacune des trois méthodes, un manifeste avec `scripts/geler_reponses_jeu_reserve.py`.

Faire enregistrer les trois empreintes auprès d'un tiers indépendant **avant** que le détenteur des références ne consulte les réponses. Conserver une attestation datée ; déposer séparément les journaux privés, sans secrets ni données sensibles dans GitHub.

Seul le détenteur autorisé ouvre ensuite les références privées, en vérifie l'empreinte annoncée dans `jeu_reserve_v1_manifeste.json` et exécute `scripts/evaluer_jeu_reserve.py` pour chaque méthode. Le programme de correction exige `--gel-reponses`, vérifie le manifeste **avant** la lecture du corrigé privé, et refuse les réponses qui ne correspondent plus au gel. Conserver la preuve extérieure de l'antériorité du manifeste, indépendamment de ce contrôle interne. Ce programme demeure dans l'environnement privé au moment de l'évaluation.

## 7. Comparer sans falsifier les résultats

Exécuter `scripts/comparer_methodes_jeu_reserve.py` sur les trois rapports issus de la correction. Présenter les scores et leurs différences appariées, le nombre de paires réellement notées, les temps humains, le temps écoulé et les valeurs inconnues.

Le jugement sur les URL et sur les ressources concrètes est ajouté séparément par l'évaluateur de qualité ; compter les URL ne prouve pas leur valeur. Les réponses historiques ne constituent pas nécessairement l'ensemble complet des solutions correctes : conserver les contestations de référence et les réponses pertinentes non prévues. Effectuer une relecture indépendante avant de tirer une conclusion.

## 8. Conditions de restitution

Le rapport final doit donner les versions des outils, le budget annoncé, les écarts à la procédure, les empreintes des réponses, la référence cryptographique commune, les résultats bruts par cas, les limites d'indépendance, les éventuelles reconnaissances de cas et les jugements contradictoires.

Avec dix cas historiques, les écarts sont exploratoires et ne constituent ni une estimation représentative de l'administration française ni une preuve d'effet causal. La valeur en situation réelle devra être étudiée ultérieurement sur des cas prospectifs dont le besoin et les résultats sont préenregistrés.

**Décision après le premier cycle :** poursuivre, resserrer ou arrêter l'hypothèse technique seulement au regard de résultats réels, reproductibles et critiqués ; préserver aussi les résultats négatifs.
