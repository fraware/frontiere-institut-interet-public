# Rectificatif de datation — ASNR, compétences internes et appuis extérieurs

**8 octobre 2026.** Ce rectificatif traite l'événement précédemment référencé S042-E04 dans la chronologie des tensions de recrutement de l'IRSN et de la construction de l'ASNR.

## Formulation historiquement enregistrée

La version 8 indiquait, au mois de **mai 2025**, que la nouvelle autorité présentait un modèle combinant compétences techniques internes et recours extérieur pour certaines compétences rares.

La première revue documentaire n'a pas retrouvé de pièce de mai 2025 établissant que cette présentation constituait une initiative datée à ce mois ou une mobilisation extérieure effectivement réalisée. La formulation liait ainsi une orientation institutionnelle et une date d'exécution sans preuve suffisante.

## Pièce parlementaire antérieure

Lors de la [séance publique du Sénat du 7 février 2024](https://www.senat.fr/seances/s202402/s20240207/s20240207_mono.html), les débats présentent la réforme destinée à regrouper les compétences techniques de l'ASN et de l'IRSN, à renforcer l'attractivité des métiers et à permettre à la future autorité de s'appuyer sur **des compétences internes fortes complétées par des partenaires externes**.

La date du débat est vérifiable. Sa portée est celle d'un **modèle d'organisation proposé pour la future autorité**, avant sa création au 1er janvier 2025. Ce document ne démontre ni une prestation extérieure réalisée en mai 2025 ni sa date de mobilisation.

Le [rapport annuel ASNR 2025](https://reglementation-controle.asnr.fr/annual_report/2025-fr/) documente, pour sa part, les premières mesures de recrutement unifié, de mobilité et de gouvernance, ainsi que le recrutement d'un directeur scientifique. Il ne reconstitue pas un épisode individuel de recours externe correspondant à l'ancienne ligne S042-E04.

## Décision de correction et conservation

La chronologie **version 9** conserve la séance parlementaire de février 2024 sous l'identifiant **S042-E02**, en explicitant ses orientations, et **retire S042-E04** du corpus courant au titre d'une attribution temporelle non confirmée.

Ce retrait est formalisé dans `retraits_evenements_non_confirmes` : ancien identifiant, ancienne date, ancienne formulation, motif, pièce primaire et assertion conservée. La version 8, où figure encore la formulation précédente, reste archivée et reproductible.

Il ne s'agit pas de cacher un résultat négatif ou de supprimer une observation adverse : la date de mai 2025, insuffisamment étayée, ne doit pas être transformée en observation factuelle. La question de savoir si l'ASNR a réellement eu recours à des compétences externes en mai 2025 demeure **ouverte** et pourra constituer ultérieurement un nouvel événement si une trace individuelle est retrouvée.

## Effet sur les décomptes

Les dix chronologies sont conservées. Le corpus actif passe de **46 à 45 événements documentaires distincts**. Les **45 événements restants** disposent d'une première lecture localisée dans `passages_sources_evenements_v6.json`, y compris les 45 événements déjà couverts avant ce retrait.

Cette couverture complète signifie uniquement qu'une pièce publique pertinente a été localisée pour chaque événement conservé. **Aucune relecture humaine contradictoire indépendante n'a été exécutée** et aucune valeur ajoutée opérationnelle de FRONTIÈRE n'est inférée de ce résultat.

Le programme `scripts/verifier_corpus_public.py` empêche désormais la réintroduction silencieuse de l'identifiant retiré dans la version 9, et `scripts/verifier_passages_sources.py` contrôle l'absence d'événements sans passage individuel.
