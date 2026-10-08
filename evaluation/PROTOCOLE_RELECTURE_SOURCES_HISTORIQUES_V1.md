# Double relecture indépendante des événements historiques — protocole v1

**Statut : prêt pour une première utilisation contrôlée.** Les deux programmes préparent et vérifient des dossiers documentaires. Aucune relecture humaine indépendante réelle n'a été conduite par leur création.

## Question de contrôle

Pour chaque événement historique retenu par FRONTIÈRE, une source officielle publique est identifiée. Il reste à déterminer si cette pièce est accessible, si elle étaye réellement le fait, si elle permet de fixer la date rapportée et si le degré de précision temporelle est conservé sans extrapolation.

Les **45 événements** des dix chronologies actives ne sont pas 45 besoins indépendants ni 45 expériences prospectives. Ils constituent un ensemble de vérification documentaire, distinct de l'évaluation comparative des méthodes.

## Séparation des responsabilités

Le responsable de l'étude remet le même paquet à deux relecteurs distincts qui ne doivent connaître ni le jugement de l'autre, ni le résultat préliminaire de l'assistant. Chacun déclare une exposition antérieure éventuelle au corpus. Les rôles, conditions de recrutement, déclarations de conflits d'intérêts et attestations de datation sont conservés hors du dépôt.

Le responsable ne fournit aux relecteurs ni les conclusions déjà attribuées aux passages, ni les limitations formulées par l'assistant. Le paquet contient les assertions originales, leur date déclarée, leur précision temporelle et les sources candidates avec l'endroit où chercher.

## Préparation des dossiers

Depuis la racine du dépôt, choisir un répertoire privé **situé hors du dépôt public**, puis :

```bash
python scripts/preparer_relecture_evenements.py \
  --registre donnees/registre_verification_evenements_v7.json \
  --passages donnees/passages_sources_evenements_v6.json \
  --sortie /chemin/prive/relecture_evenements_001
```

Le programme valide d'abord la cohérence des passages, puis crée deux dossiers `relecteur_1` et `relecteur_2`, chacun contenant le même paquet et un formulaire vierge. Le manifeste administratif contient les empreintes des fichiers utilisés et celle du paquet commun.

Le responsable enregistre l'empreinte du paquet auprès d'un tiers avant remise des dossiers. Une empreinte locale ne démontre pas, à elle seule, l'antériorité d'un fichier.

## Jugement documentaire

Chaque relecteur attribue à chaque événement, **sans concertation**, une valeur `OUI`, `NON` ou `INDETERMINE` sur quatre dimensions :

1. **Pièce retrouvée :** le document réellement examiné correspond-il à la source proposée ?
2. **Fait étayé :** le contenu de ce document soutient-il le fait allégué ?
3. **Date étayée :** le document établit-il la période ou le jour qui lui est attribué ?
4. **Précision respectée :** l'événement n'est-il pas présenté avec une précision temporelle supérieure à celle de la source ?

Chaque avis exige une justification. Une pièce déclarée retrouvée doit comporter une localisation réellement consultée. Les sources complémentaires découvertes sont mentionnées dans cette justification. Il est essentiel de conserver les résultats indéterminés : un lien inaccessible n'est pas équivalent à une réfutation.

Le formulaire initial laisse toutes les dimensions à `A_VERIFIER` et les champs narratifs vides. La préparation de fichiers n'enregistre **aucun** verdict.

## Gel et consolidation

Lorsque les deux relecteurs ont terminé leur travail, le responsable vérifie leurs identifiants, enregistre séparément les deux empreintes et fait attester leur antériorité avant examen conjoint.

Puis :

```bash
python scripts/consolider_relecture_evenements.py \
  --paquet /chemin/prive/relecture_evenements_001/paquet_commun.json \
  --jugements /chemin/prive/avis_relecteur_1.json /chemin/prive/avis_relecteur_2.json \
  --sortie /chemin/prive/bilan_evenements_001.json
```

Le programme rejette les avis incomplets, les identifiants dupliqués et les jugements portant sur un paquet différent. Il calcule un tableau d'accords par dimension et énumère chaque désaccord avec les deux avis originaux. **Aucun consensus n'est produit automatiquement.** Une éventuelle décision d'arbitrage doit constituer un document distinct, daté et motivé.

## Restitution

Le rapport de recherche distingue : faits acceptés par les deux relecteurs, faits contestés, passages insuffisants, datations indéterminées et désaccords résiduels. La comparaison des jugements ne transforme pas l'ensemble des événements en une mesure statistique représentative des administrations françaises.

Les relectures seront déclarées **réalisées** uniquement après réception effective des deux fichiers individuels, validation de leurs empreintes et conservation des preuves de leur origine. La vérification des documents ne prouve pas le bénéfice opérationnel de FRONTIÈRE, qui exige les expériences comparatives et cas prospectifs définis ailleurs dans le projet.
