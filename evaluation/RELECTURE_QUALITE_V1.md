# Relecture de la qualité des ressources et des sources — protocole v1

**État : instrument préparatoire.** Aucune relecture réelle n'est réalisée par ce document. Cette étape intervient après le gel des trois fichiers de réponses et, si possible, avant révélation des méthodes aux relecteurs.

## Objet

Les scores de correspondance avec les voies historiques ne répondent pas aux questions suivantes : la ressource proposée existe-t-elle ? Est-elle adaptée au besoin précis ? Sa mobilisation est-elle établie au moment pertinent ? La source citée est-elle fiable et soutient-elle réellement la proposition ?

Deux personnes indépendantes doivent examiner ces éléments **sans disposer de la correspondance entre propositions et méthodes**. Elles peuvent consulter les sources publiques indiquées et d'autres éléments publics nécessaires à la vérification, dans les limites du protocole fixé.

## Conditions et séquence

1. Les trois réponses de méthodes distinctes sont complètes, validées et figées. Les manifestes de gel doivent correspondre aux fichiers remis.
2. Le responsable prépare un paquet commun et deux formulaires identiques. Chaque réponse reçoit une lettre réattribuée indépendamment pour chaque cas.
3. Les relecteurs n'accèdent ni aux références historiques privées, ni aux correspondances privées, ni aux réponses originales indiquant leur méthode. Ils déclarent tout indice qui leur permet de reconnaître une méthode.
4. Chaque jugement est individuel, justifié et conservé avant consultation du jugement de l'autre relecteur.
5. Après gel des deux relectures, le responsable confronte les évaluations et produit un bilan identifiant séparément les appréciations et leurs désaccords.

L'attribution aléatoire de lettres réduit les indices directs d'identité ; le style des réponses ou une connaissance antérieure de FRONTIÈRE peuvent néanmoins permettre de deviner la méthode. Une déclaration d'exposition antérieure reste nécessaire.

## Préparer les dossiers

Dans un environnement privé, depuis la racine du dépôt, utiliser les mêmes questions que lors du gel des réponses :

```bash
python scripts/preparer_relecture_qualite.py \
  --questions evaluation/jeu_reserve_v1_questions.json \
  --reponses /prive/analyste.json /prive/assistant.json /prive/frontiere.json \
  --gels /prive/analyste_gel.json /prive/assistant_gel.json /prive/frontiere_gel.json \
  --sortie /prive/relecture_qualite_001
```

Ce programme n'ouvre aucune référence historique. Il refuse toute divergence entre réponses et empreintes des manifestes. Il crée :

- `paquet_aveugle.json` : questions et propositions anonymisées par cas ;
- `jugements_relecteur_1_vierges.json` et `jugements_relecteur_2_vierges.json` : formulaires de jugement ;
- `correspondances_privees.json` : affectation entre propositions et méthodes, **réservée au responsable** ;
- `CONSIGNES_RELECTEURS.md` : guide opérationnel des catégories.

La destination doit être extérieure au dépôt public. Le responsable conserve les empreintes des dossiers et ne communique à chaque relecteur que le paquet, les consignes et un formulaire de jugement.

## Grille de jugement

Pour une **ressource nommée**, trois aspects sont distincts :

| Aspect | Appréciations possibles |
| --- | --- |
| Existence vérifiée | CONFIRMEE, NON_CONFIRMEE, INDETERMINEE |
| Pertinence pour le cas | FORTE, PARTIELLE, INSUFFISANTE, INDETERMINEE |
| Mobilisabilité à la date utile | CONFIRMEE, NON_CONFIRMEE, INDETERMINEE |

Pour une **source citée**, deux aspects sont distincts :

| Aspect | Appréciations possibles |
| --- | --- |
| Fiabilité et proximité de la source | PRIMAIRE, SECONDAIRE, INSUFFISANTE, INDETERMINEE |
| Appui apporté à la proposition | DIRECT, PARTIEL, AUCUN, INDETERMINE |

Une appréciation `A_VERIFIER` est une entrée provisoire : elle empêche la consolidation définitive. Toute appréciation, y compris une incertitude, doit être accompagnée d'un motif indiquant l'élément contrôlé.

La mobilisabilité peut rester indéterminée même lorsque l'existence et la pertinence d'un organisme sont établies. Une publication décrivant les compétences d'un laboratoire ne prouve pas qu'il peut intervenir dans la mission concernée.

Ces jugements ne remplacent ni une prise de contact, ni la vérification des conditions juridiques, administratives ou financières d'une mobilisation.

## Consolider les deux relectures

Une fois les jugements terminés et leurs fichiers figés, produire le bilan en environnement privé :

```bash
python scripts/consolider_relecture_qualite.py \
  --paquet /prive/relecture_qualite_001/paquet_aveugle.json \
  --correspondances-privees /prive/relecture_qualite_001/correspondances_privees.json \
  --jugements /prive/jugements_relecteur_1.json /prive/jugements_relecteur_2.json \
  --sortie /prive/bilan_relecture_qualite.json
```

Le programme rejette les formulaires incomplets, les propositions manquantes, les catégories invalides et les identifiants de relecteurs identiques. Il conserve les comptages séparés pour chacun des deux jugements ainsi que la liste des désaccords, avec chaque appréciation initiale. **Aucun consensus ni score composite n'est fabriqué automatiquement.**

## Restitution et limites

La restitution doit indiquer le nombre de ressources et de sources effectivement examinées, les cas sans ressource ni source citée, les éléments indéterminés, les désaccords et la décision éventuelle d'un arbitre indépendant. La qualité des réponses ne se réduit pas à la quantité des propositions ou des URL.

Il faut préserver dans l'analyse les réponses pertinentes non prévues dans les références historiques, les appréciations contradictoires et les situations dont la mobilisabilité reste inconnue.

Aucune conclusion sur un avantage propre à FRONTIÈRE ne découle du seul lancement de cette procédure. Les résultats demeurent conditionnés à des relectures effectivement conduites.
