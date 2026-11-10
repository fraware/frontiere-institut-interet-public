# Programme 147 — audit Ci.Ville 2 et lancement du pilote documentaire

**Frontière / Institut pour l’intérêt public — 9 novembre 2026. Statut : étude exploratoire, observations documentaires uniquement.**

## Sources et méthode

Dépôt public : https://github.com/anct-carto/ci-ville2 ; commit `999ba72cf7230842c192f8a261ced86351283e61`.
Sources : `src/assets/subventions-2024.json` (blob `45f326a3cf2387177f347a5824ef3ef9d3005f3e`, 16 717 279 octets) et `src/assets/subventions-2025.json` (blob `9f3f541f9adcd948f0867515ab0c151475b66f8e`, 15 488 987 octets). Les contenus ont été lus via le connecteur GitHub et analysés par parcours exhaustif des tableaux JSON. L'objet échantillonné demeure la **ligne du JSON dérivé**, distincte d'un dossier administratif, d'un versement et d'une activité réalisée.

## Résultats indépendamment recalculés

| Mesure | 2024 | 2025 |
| --- | ---: | ---: |
| Lignes | 39079 | 38372 |
| Identifiants d'action distincts | 39079 | 38368 |
| Codes tiers distincts | 13667 | 13522 |
| Somme des montants (euros) | 380 874 731,52 | 360 521 032,00 |
| Lignes à montant nul | 0 | 7 |
| Lignes sans champ `insee_dep` | 1537 | 1218 |

Échelles 2024 : nat=404, reg=1133, dep=302, cdv=37240. Échelles 2025 : nat=186, reg=1032, cdv=37154; la valeur `dep` est absente. Les quatre identifiants d'action réutilisés en 2025 sont `00327440`, `00338070`, `00352813`, `00371219`. Le contrôle de Luhn sur les identifiants `code_tiers` à 14 chiffres de 2025 n'a relevé aucun échec, ce qui ne vérifie ni l'existence des établissements dans Sirene ni leur statut juridique. Le fichier 2025 contient sept lignes à montant nul, à considérer comme anomalies de représentation à élucider et **non** comme preuve d'une subvention effectivement versée de zéro euro.

## Échantillon de faisabilité documentaire — 12 lignes

Voir `donnees/p147/echantillon_faisabilite_12_2025.csv`. Six lignes couvrent trois identifiants `id_action` réutilisés, afin de vérifier si elles renvoient à plusieurs décisions d'attribution ou à plusieurs ventilations d'une même action. Six autres lignes apportent un cas par thème (1 à 6) à l'échelle `cdv`, en cherchant des départements et porteurs différents.

Sélection déterministe : inclure toutes les lignes de `00338070`, `00371219` et `00327440`, puis parcourir les thèmes `1` à `6`. Pour chaque thème, considérer uniquement les lignes `cdv` avec montant entre 3 000 et 50 000 euros, titre de 25 à 160 unités UTF-16, code tiers de 14 chiffres, département renseigné, porteur et département absents de la sélection déjà retenue et identifiant hors des trois groupes doublés. Choisir le candidat de rang minimal selon FNV-1a 32 bits du texte ASCII `ANCT-FRONTIERE-2026-11-09|id_action|code_tiers|row_index_0based`, puis départager par index source. La sélection explore la diversité et les mécanismes d'échec ; **aucun taux populationnel n'en est inférable**.

Le fichier `donnees/p147/sentinelles_montant_nul_2025.csv` recense séparément toutes les sept lignes nulles. Ces sentinelles sont des contrôles de qualité et restent hors de l'échantillon documentaire de 12 lignes.

## Prochaines opérations réelles

1. Identifier l'administration détentrice et/ou attributrice par action en comparant les informations de la plateforme et les notices administratives. Aucun service attributaire n'est confirmé par ces seuls fichiers JSON.
2. Envoyer une demande écrite de communication pour les pièces existantes : décision ou convention, comptes rendus financiers, bilans disponibles et éventuels documents contenant les résultats annoncés. Conserver le courriel initial, la date et l'accusé.
3. Documenter la réponse propre à chaque action : `not_requested`, `requested`, `received`, `pending`, `refused`, `not_located`, `not_yet_due`, `not_communicable` ; ne jamais assimiler absence de document et absence d'exécution.
4. Pour chaque pièce reçue, conserver une empreinte SHA-256, un identifiant documentaire, la période d'exécution, la décision d'attribution, le mode de rapprochement et une évaluation de fiabilité. Respecter les occultations légales avant publication.
5. Après la vérification de cette faisabilité, lancer séparément l'échantillonnage probabiliste des 120 lignes prévu dans le protocole v0.5 et documenter les non-réponses, sans transposer les résultats des 12 dossiers.

**Cadre légal** : article 10 de la loi n° 2000-321, https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000045213404 ; guide officiel ANCT sur la justification, https://anct.gouv.fr/programmes-dispositifs/politique-de-la-ville/subventions-de-la-politique-de-la-ville ; accès aux documents administratifs, https://www.service-public.fr/particuliers/vosdroits/F2467 ; Cerfa 15059*02, https://www.service-public.fr/particuliers/vosdroits/R46623.

## Limites et garde-fous

Aucun compte rendu Dauphin n'a été reçu. Aucun courrier n'a été envoyé. Les sources analysées sont des représentations secondaires utilisées par Ci.Ville 2. Les fichiers CSV natifs des administrations, les décisions d'attribution et les paiements Chorus restent à rapprocher. Les deux contenus JSON complets ont été lus via GitHub, sans téléchargement des octets originaux dans le répertoire de travail local. Les sommes sont calculées en centimes entiers depuis les montants du JSON. Les observations ne démontrent ni prestation effective ni causalité.
