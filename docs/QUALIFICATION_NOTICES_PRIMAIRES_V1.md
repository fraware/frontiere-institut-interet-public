# Qualification documentaire des six captures BOAMP — v1

## Fonction scientifique

L'outil `scripts/qualifier_captures_notices_boamp.py` classe les avis publics observés par **nature documentaire**, sans déduire un déficit de compétences. Il utilise exclusivement les réponses primaires conservées sous empreinte SHA-256 par le collecteur, puis compare le registre préenregistré de six cas à l'empreinte figurant dans le rapport de capture.

La qualification sépare les trois dimensions suivantes :

- Nature déclarée par la source : appel d'offres, attribution ou autre type.
- État déclaré : initial, rectificatif ou autre état.
- Liens explicites vers des avis antérieurs, sans supposer que leur contenu soit disponible.

L'avis qualifié comme `ATTRIBUTION` est un **avis d'attribution publié**, et non la preuve d'une mise en service ou d'une contribution scientifique déjà obtenue. Un avis `INITIAL` portant sur une attribution n'est pas le premier avis de consultation. De même, un `RECTIFICATIF` ne remplace pas son avis antérieur comme preuve de publication initiale.

## Constat du premier relevé réel

Capture officielle du 11 octobre 2026, exécution GitHub Actions 38183881456, artefact 11718911414, six réponses contrôlées :

| Avis | Nature officielle | État documentaire | Information distincte |
| --- | --- | --- | --- |
| 26-77392, SGDSN | APPEL_OFFRE | INITIAL | Marché de services |
| 26-81972, INRAE | APPEL_OFFRE | INITIAL | Fournitures, robot NGS |
| 26-74896, Météo-France | ATTRIBUTION | INITIAL | Titulaire déclaré BULL SAS |
| 26-30147, université de Caen Normandie | ATTRIBUTION | INITIAL | Titulaire déclaré ACTIMAR |
| 26-83870, Tisséo | APPEL_OFFRE | RECTIFICATIF | Renvoi explicite à 26-81640 |
| 25-71164, IAE de Paris | APPEL_OFFRE | INITIAL | Prestation de services |

L'ensemble compte **trois appels d'offres initiaux, deux avis d'attribution et un rectificatif**. Les six avis restent des cas intentionnels, sans représentativité statistique revendiquée. Aucun lien vers un avis antérieur ne signifie que l'avis initial est absent du corpus ou qu'il n'a pas existé.

Le champ `datefindiffusion` du service officiel indique une **date de fin de diffusion**, jamais une date de démarrage de la procédure ou du travail scientifique. L'outil de qualification ne l'utilise pas pour calculer les délais.

## Commande de reproduction

~~~bash
python scripts/qualifier_captures_notices_boamp.py \
  --captures /chemin/extrait-des-captures \
  --registre evaluation/cas_pilotes_boamp_v1.json \
  --sortie /chemin/qualification-nature.json
~~~

Le résultat comporte les catégories exactes, les noms de titulaires effectivement présents dans les avis, les dates de publication et de limite de réponse, les liens explicites vers des avis antérieurs, les références des fichiers capturés et leurs empreintes. Il désigne les lacunes de preuve sans fabriquer une classification causale.

La procédure `.github/workflows/captures-notices-pilotes.yml` exécute les tests hors connexion, effectue la nouvelle capture, puis qualifie les avis. Elle dépose une restitution JSON dans le même artefact d'exécution.

## Suite expérimentale

En premier lieu, récupérer la notice antérieure 26-81640 explicitement désignée par le rectificatif Tisséo. Son contenu n'a pas encore été examiné dans le premier relevé.

Pour les avis d'attribution, confronter les renseignements officiels à d'autres documents primaires sur la date de la décision, les étapes de livraison et la première utilisation. La date de publication d'une attribution ne mesure aucun délai de mobilisation.

Enfin, confronter chaque cas à des mécanismes concurrents : achat d'équipement, prestation spécialisée, expertise indépendante, capacité publique disponible et besoin réellement non satisfait. La catégorie « indéterminé » demeure une issue valide.
