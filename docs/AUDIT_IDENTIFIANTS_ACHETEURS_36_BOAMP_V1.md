# Audit des identifiants d'acheteurs sur 36 avis indépendants

## Objet et unité d'observation

Le programme `scripts/auditer_identifiants_acheteurs_independants_boamp.py` analyse **36 avis BOAMP préalablement tirés**, en six mois de six avis, sans nouvelle recherche de cas ni collecte de réponses. Les données proviennent de `releve-issues-36/` déjà constitué dans la procédure d'indexation historique. La méthode conserve l'ordre, les dates, les identifiants de notices et l'empreinte des réponses primaires.

L'unité est **l'avis**, non le marché, le contrat, le lot ou l'organisme. Plusieurs avis d'une même procédure ne doivent pas être interprétés comme plusieurs besoins distincts.

## Intégrité et traçabilité

Avant la lecture d'une identité, le programme revérifie la version et l'empreinte du tirage indépendant, le nombre de fiches, l'ordre exact des identifiants, chaque adresse de requête officielle, chaque nom de fichier, chaque longueur et chaque empreinte SHA-256. Le statut et la date annoncés dans le registre sont confrontés à l'enveloppe officielle ; les absences et divergences datées conservent un état inconnu, sans tentative de correction implicite. Les distributions de statuts sont comparées à celles du relevé initial.

Le rapport produit dans `audit-identifiants-acheteurs-36.json` conserve, pour chaque avis, le SHA-256 de la réponse, l'identité textuelle de l'acheteur lorsqu'elle est qualifiable, le chemin du champ de preuve, la qualification de la référence interne et les limites d'interprétation.

## Classes séparées

L'extracteur réemploie les règles de lecture conservatrices de `scripts/extraire_references_boamp_decp.py` :

- **SIRET explicitement qualifié** : identifiant de quatorze chiffres avec schéma SIRET déclaré, attribuable univoquement au rôle `cac:ContractingParty`. La présence d'une référence interne de projet n'est pas nécessaire pour cette mesure.
- **Identifiant de quatorze chiffres sans schéma** : observation numérique explicitement reliée au rôle acheteur, sans conclusion sur son statut administratif.
- **Identité inconnue** : absence, dates divergentes, format ou rôle non interprétable, identifiants ambigus et toutes les situations restantes.

Les identifiants des titulaires ne sont jamais attribués à l'acheteur. Aucun rapprochement avec le répertoire SIRENE ni contrôle indépendant d'existence administrative n'est encore effectué. Une correspondance numérique ne devient jamais une identité de contrat vérifiée.

## Reproduction et interprétation

Exécution sans réseau à partir d'une archive produite par le programme `relever_issues_echantillon_independant.py` et du fichier de tirage conservé dans **la même exécution** :

```bash
python -m pytest -q tests/test_auditer_identifiants_acheteurs_independants_boamp.py
python scripts/auditer_identifiants_acheteurs_independants_boamp.py \
  --echantillon /chemin/echantillon-independant-technique.json \
  --releve /chemin/releve-issues-36 \
  --sortie /chemin/audit-identifiants-acheteurs-36.json
```

Les dénominateurs publiés permettent de distinguer la disponibilité d'un avis, la lisibilité de son formulaire et la récupération d'une identité acheteuse. L'échantillon est enrichi sur des domaines techniques et sur des mois prédéfinis ; **il ne représente pas la France entière**. Ses mesures ne caractérisent ni les besoins toujours ouverts ni le délai de mobilisation de compétences.

## Prochaine étape

Comparer les identifiants candidats avec des données officielles d'établissements, en conservant distinctement le contrôle arithmétique du numéro, son existence au répertoire et son rattachement au pouvoir adjudicateur. Étendre ensuite les observations à d'autres cohortes temporelles sans modifier rétroactivement le tirage initial.
