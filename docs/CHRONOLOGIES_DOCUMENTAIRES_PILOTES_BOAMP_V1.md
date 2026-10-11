# Chronologies documentaires des pilotes BOAMP — première extension

## Portée et sources observées

Cette extension poursuit les six captures BOAMP primaires ayant réussi dans l'exécution GitHub Actions 38184210146 du 11 octobre 2026 (artefact 11718124467). Elle extrait les **champs de décision d'attribution et d'émission du contrat**, ainsi que les **résultats des lots**, directement depuis le document structuré `donnees`. Un second programme récupère les avis que les rectificatifs désignent explicitement dans `annonce_lie`.

L'ensemble exclut les contacts, déclarations orales, déductions sur les ressources humaines et résultats inventés. Les informations proviennent de la source officielle BOAMP/DILA consultée à la date de capture. Les copies documentaires conservent le corps exact des réponses et une empreinte SHA-256. Les documents ne sont ni des rapports d'utilisation de l'équipement, ni des comptes rendus de réalisation scientifique.

## Jalons déjà établis par le premier relevé

| Dossier | Date d'attribution déclarée dans le contrat | Date d'émission du contrat déclarée | Publication BOAMP | Résultat par lot |
| --- | --- | --- | --- | --- |
| Météo-France, 26-74896 | 2026-07-20 | 2026-07-22 | 2026-07-28 | LOT-0001 : selec-w |
| Université de Caen Normandie, 26-30147 | 2025-09-24 | 2025-10-07 | 2026-03-25 | LOT-0001 : selec-w ; LOT-0002 : clos-nw, motif no-rece |

Les codes de résultat sont conservés tels quels. `selec-w` désigne une offre retenue ; `clos-nw` indique un lot clos sans titulaire. Le code `no-rece` se rapporte à l'absence de soumissions reçues. La qualification par lot empêche de traiter le marché de Caen comme une attribution intégrale.

Les dates d'émission et d'attribution correspondent aux champs XML structurés `efac:SettledContract/cbc:IssueDate` et `cbc:AwardDate`. Leur existence ne démontre pas une signature effective, une date de livraison ni le commencement des travaux. Le champ `cac:TenderResult/cbc:AwardDate` contenant, dans les notices observées, une valeur sentinelle du 1er janvier 2000 est volontairement exclu.

## Chaîne de provenance

Le programme `scripts/reconstituer_chronologies_pilotes_boamp.py` valide les empreintes des six réponses, la concordance du registre de référence et la structure du formulaire de l'avis d'attribution. Il restitue le chemin de chaque champ étudié dans le document structuré. Il distingue les éléments uniques des listes, puisque les convertisseurs XML vers JSON font varier leur représentation.

Le programme `scripts/collecter_avis_lies_boamp.py` suit exclusivement les identifiants `annonce_lie` déclarés par les avis marqués `RECTIFICATIF`. La première capture indique que 26-83870 cite 26-81640. Le nouveau traitement vérifie l'identité et la date de l'avis précédent, conserve ses octets et autorise une observation absente sans conclure à une inexistence historique.

Aucun calcul de délai de mobilisation de compétences n'est publié. Le début d'exécution, la réception, l'accès scientifique réel et la première contribution utile restent inconnus.

## Exécution reproductible

~~~bash
python scripts/reconstituer_chronologies_pilotes_boamp.py \
  --captures /chemin/captures-notices-pilotes \
  --registre evaluation/cas_pilotes_boamp_v1.json \
  --sortie /chemin/chronologies.json

python scripts/collecter_avis_lies_boamp.py \
  --principaux /chemin/captures-notices-pilotes \
  --sortie /chemin/nouveau-dossier-avis-anterieurs

python scripts/collecter_avis_lies_boamp.py \
  --principaux /chemin/captures-notices-pilotes \
  --verifier /chemin/nouveau-dossier-avis-anterieurs
~~~

La procédure `captures-notices-pilotes.yml` teste les deux programmes hors réseau, puis exécute la collecte et les contrôles sur les réponses officielles actuelles. Les rapports et archives sont associés à l'identifiant de cette exécution pour permettre la reproduction.

## Critère scientifique du prochain cycle

Pour obtenir une chronologie complète, il faudra identifier et vérifier des événements supplémentaires : date de définition du besoin, ouverture de consultation, décision, formalisation du contrat, livraison, réception, accès opérationnel et première contribution scientifique utile. Un événement absent demeure une donnée manquante. Les documents de marchés ne suffisent pas à qualifier la difficulté de recrutement ni la présence ou la disponibilité d'une compétence scientifique publique.
