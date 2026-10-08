# Orientation documentaire d'un besoin institutionnel verrouillé

## Objet

Cette fonction relie une **requête de capacité déjà enregistrée dans FRONTIÈRE** aux notices du référentiel institutionnel. Elle produit une liste de pistes vérifiables, avec les mots effectivement présents dans les missions, les domaines scientifiques et les noms d'organismes. Elle ne conclut jamais qu'un organisme dispose des moyens recherchés, ni qu'il serait en mesure de les mobiliser.

Cette première interface est un **programme local**. Aucun nouveau service accessible par le réseau n'est ouvert, compte tenu de l'absence actuelle d'authentification du prototype.

## Conditions de lancement

L'orientation exige un dossier existant de sensibilité 1, une seule version active du besoin **verrouillée**, ainsi qu'une requête de capacité active, verrouillée et rattachée précisément à cette version. Une requête devenue ancienne à la suite d'une révision du besoin est refusée.

Pour les cas prospectifs, le programme exige que les règles de comparaison aient été enregistrées si l'état initial du cas a déjà été figé. Chaque orientation réussie est consignée dans le journal du dossier ; cette intervention est ensuite prise en compte si l'on tente d'enregistrer rétrospectivement l'état initial. Une orientation déjà réalisée ne peut pas être effacée du raisonnement expérimental.

Le programme refuse les dossiers de sensibilité supérieure à 1, faute de contrôle des accès adapté. Le mode de production est également refusé. L'utilisateur de la commande doit travailler dans une instance locale isolée.

## Commande

À la racine du dépôt, commencer par reconstruire l'index institutionnel si les fichiers de la source ont changé.

```bash
python scripts/rechercher_capacites_institutionnelles.py --construire
python scripts/orienter_besoin_institutionnel.py \
  --episode EP-2026-0001 \
  --limite 8
```

Le code `EP-2026-0001` est uniquement un exemple : utiliser l'identifiant d'un dossier déjà présent dans la base de données locale.

Les chemins du répertoire institutionnel et de l'index peuvent être précisés avec `--entites` et `--index`. La base de dossiers est celle désignée par le réglage `FRONTIERE_DATABASE_URL`. Le programme refuse d'interroger un index dont les empreintes ne correspondent plus aux fichiers du référentiel.

Le résultat est affiché au terminal au format JSON. Il contient des expressions issues du besoin et doit être traité conformément au niveau de confidentialité du dossier. **Ne pas ajouter ces rapports au dépôt public**, ni les envoyer à un service extérieur sans vérification des autorisations.

## Décomposition de la recherche

Le programme exploite quatre groupes de clauses présents dans la requête de capacité :

1. Domaine technique déclaré.
2. Fonction technique recherchée.
3. Critères impératifs.
4. Critères souhaitables.

Chaque clause est recherchée séparément. Les critères facultatifs inutilisables comme requêtes lexicales sont signalés comme tels ; ils ne disparaissent pas silencieusement. Le domaine et la fonction sont obligatoires et doivent comporter des termes exploitables.

Le contexte opérationnel, la profondeur d'expertise, les formes de ressources souhaitées, les contraintes et l'échéance utile restent présents dans l'empreinte de la requête. **Ils ne sont pas validés par le moteur documentaire**, dont les sources ne renseignent généralement pas ces propriétés.

Pour chaque organisme, les termes trouvés et les passages publiés sont associés aux clauses qui les ont produits. Les résultats restent séparés selon trois niveaux : mission ou capacité explicitement publiée, domaine scientifique officiel, rapprochement par le nom uniquement.

Un critère impératif qui recoupe un mot d'une mission ou d'une discipline est signalé comme **recoupement lexical**. Il n'est pas considéré comme satisfait. La pertinence de l'organisme pour le besoin, sa disponibilité et sa mobilisabilité portent systématiquement les états « non vérifiée », « inconnue » et « non établie ».

## Traçabilité et interprétation

Chaque recherche réussie inscrit l'événement `ORIENTATION_DOCUMENTAIRE_EXECUTEE` dans le journal de la base de données. Cet événement mémorise uniquement des identifiants techniques, les versions du besoin et de sa requête, les empreintes de la requête, du référentiel et du contenu de la réponse, ainsi que les effectifs de la recherche. Le texte des besoins, les passages trouvés et les noms des organismes ne sont pas copiés dans l'événement d'audit.

Le rapport restitue son identifiant d'événement et l'empreinte de son contenu, calculée avant l'ajout des informations du journal et du contrôle des sources. Ces informations permettent de retrouver les conditions exactes de l'exécution et de constater une modification du rapport original, dans les limites d'un contrôle d'intégrité interne.

Une orientation **n'enregistre aucune découverte, aucune ressource mobilisable, aucune recherche publique déclarée complète et aucune décision**. Les conclusions sur une capacité pertinente, un délai ou une mobilisation relèvent d'autres éléments de preuve et d'une procédure séparée.

Le nombre de pistes et les recoupements lexicaux constituent des caractéristiques techniques de la recherche. Ils ne mesurent ni le rappel institutionnel, ni la précision de l'orientation, ni la valeur ajoutée de FRONTIÈRE.

## Essais et limites

Les tests automatiques emploient des besoins et organismes fictifs. Ils vérifient notamment l'association au bon besoin verrouillé, la séparation des preuves, les exigences de provenance, les index périmés, la protection des cas prospectifs, la confidentialité minimale, les critères non exploitables et l'absence de modification des tables consacrées aux recherches publiques et ressources vérifiées.

La recherche demeure tributaire des mots exacts, de la couverture des sources et de ses plafonds par catégorie. Des synonymes, équipements ou savoir-faire absents des notices peuvent produire des omissions. Une concordance lexicale est une piste documentaire à examiner, jamais une démonstration de compétence opérationnelle.

L'étape technique suivante consiste à mesurer les omissions et les correspondances trompeuses sur un jeu d'essai artificiel indépendant du corpus d'évaluation réservé, en conservant les justifications de chaque jugement.
