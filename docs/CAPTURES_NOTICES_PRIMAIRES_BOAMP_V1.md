# Captures primaires des six avis pilotes BOAMP

## Objet et relation avec le protocole

Le traitement de six avis pilotes dispose déjà d'un rapprochement avec les métadonnées de l'index BOAMP vérifié et, lorsque les identifiants coïncident strictement, avec les lignes BeauAMP. Le programme de ce dossier ajoute une **observation, à la date de sa consultation, de la réponse JSON complète** du service officiel de la DILA pour chacun de ces six identifiants.

Le service public documente son interface à l'adresse :
https://www.data.gouv.fr/dataservices/api-bulletin-officiel-des-annonces-des-marches-publics-boamp

L'outil utilise l'adresse d'interrogation déjà employée par les collecteurs du projet, en version 2.1, avec une clause exacte sur le champ `idweb`. Le programme refuse les redirections HTTP, impose un plafond de réponse et rejette tout identifiant ambigu, toute incohérence de pagination et tout écart de date par rapport au registre pilote.

Le système conserve exactement les octets du corps de réponse HTTP reçus pendant la consultation, leur empreinte SHA-256, leur longueur et l'adresse complète de la requête. L'horodatage indique le moment de la capture, pas la date historique à laquelle les informations ont été disponibles au public. **Il n'atteste pas qu'une réponse reconstituée en octobre 2026 était identique à l'avis publié en 2025 ou en août 2026.**

## Utilisation

Depuis la racine du dépôt, avec Python 3.11 ou ultérieur :

~~~bash
python scripts/collecter_notices_pilotes_boamp.py \
  --registre evaluation/cas_pilotes_boamp_v1.json \
  --sortie /chemin/nouveau-dossier-de-capture

python scripts/collecter_notices_pilotes_boamp.py \
  --verifier /chemin/nouveau-dossier-de-capture
~~~

Le dossier de sortie doit être inexistant. Il reçoit un fichier JSON par identifiant et un `rapport.json` décrivant les observations et les empreintes. Les octets sont écrits dans un répertoire provisoire. Une anomalie sur un seul avis interrompt la capture complète sans produire de dossier final partiel.

Une réponse indiquant zéro avis est conservée avec le statut `non_retrouve_lors_de_ce_releve`. Ce statut signifie uniquement que le service interrogé n'a restitué aucune notice au cours de **cette consultation**. Il ne démontre ni absence de publication historique ni disparition d'un marché.

Le rapport ne déduit jamais l'existence d'un besoin de recrutement, une pénurie de spécialistes, la disponibilité d'une équipe ou un délai de contribution utile.

## Vérification et exécution périodique

Les tests hors connexion vérifient l'intégrité des octets, la cohérence de l'identifiant et de la date, les réponses nulles ou ambiguës, les refus de remplacement et le comportement en cas d'échec avant publication.

La procédure GitHub Actions `.github/workflows/captures-notices-pilotes.yml` exécute les tests, consulte les six avis, vérifie localement toutes les réponses archivées puis conserve le dossier sous forme d'artefact associé à l'exécution, pendant **30 jours**. Elle est indépendante de la reconstruction quotidienne des index BOAMP. Une indisponibilité de l'API de consultation n'empêche donc pas la construction des index historiques.

Une exécution réussie établit la fiabilité structurelle et l'intégrité de la capture de cette exécution. La pertinence scientifique des six avis et leur pouvoir explicatif restent à évaluer. Une exécution sans correspondance comporte des lacunes documentaires, pas des observations négatives de capacité.

## Prochaines exploitations scientifiques

1. Comparer les champs officiels complets avec les métadonnées normalisées déjà indexées, en conservant les désaccords sous forme de versions datées.
2. Identifier les références directes à des pièces contractuelles ou techniques éventuellement présentes dans les réponses, sans inventer de documents ni suivre des liens non vérifiés.
3. Extraire les renseignements documentaires vérifiables sur le résultat attendu, les caractéristiques scientifiques et techniques, les échéances et les différentes formes de ressources nécessaires.
4. Constituer des exemples négatifs et indéterminés à partir des mêmes règles, puis mesurer précision et rappel sur un corpus d'évaluation distinct.

Le résultat attendu est une meilleure caractérisation empirique des besoins et des moyens mobilisés, et non une augmentation artificielle du nombre de cas réputés confirmés.
