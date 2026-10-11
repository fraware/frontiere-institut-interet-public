# Croisement documentaire entre annonces techniques et capacités publiques

## Objectif

Ce programme cherche des **pistes de correspondance vérifiables** entre certains avis du Bulletin officiel des annonces des marchés publics (BOAMP) et les descriptions publiques d'organismes administratifs ou scientifiques. Il fait progresser l'étude FRONTIÈRE de la simple collecte de notices vers l'identification méthodique de ressources publiques à examiner.

Les deux ensembles restent distincts. Un marché publié ne démontre ni un manque de compétences internes, ni une difficulté de recrutement. Une mission ou discipline publiée par un organisme ne démontre ni sa disponibilité, ni sa capacité à répondre au marché particulier.

## Délimitation et construction

L'entrée BOAMP comprend un index SQLite vérifié, la preuve de sa fabrication et un bilan lexical complet. Le programme reconstruit le bilan, compare l'intégralité de son contenu au fichier fourni, puis reproduit la sélection de douze pistes au plus par domaine, avec deux avis au plus par acheteur et par domaine. Les règles de sélection sont les sept familles lexicales publiées dans `scripts/analyser_historique_boamp.py`.

L'entrée institutionnelle comprend le référentiel public et son index dédié. Le programme vérifie que **tous les fichiers sources du référentiel sont identiques aux fichiers utilisés pour construire cet index**, avant d'effectuer le moindre rapprochement.

Pour chaque piste, il utilise uniquement les expressions expressément retrouvées dans le champ `objet` de l'avis. La recherche documentaire sur ces expressions produit des candidats. Un organisme n'est ensuite conservé que si l'expression entière apparaît comme séquence de mots contigus dans un passage de capacité, de mission ou de domaine scientifique publié et sourcé. Une simple correspondance de nom est conservée séparément. Une ressemblance portant sur un seul mot d'une expression plus longue est écartée.

Cette méthode est volontairement plus restrictive que la recherche institutionnelle usuelle. Elle ignore notamment les synonymes, descriptions implicites, relations entre organismes et ressources absentes des notices publiées. Elle ne réalise aucune résolution de l'identité de l'acheteur par rapprochement incertain de noms.

## Classes et limites

Les résultats sont classés en quatre catégories documentaires : capacité publiée, mission publiée, domaine scientifique publié et concordance nominale seule. Chaque résultat possède l'identifiant de l'organisme, sa famille, les extraits justifiant la concordance, les références de provenance et la date du relevé institutionnel. Les expressions retrouvées, les paramètres de recherche et les limites de restitution sont conservés.

Les résultats sont bornés à vingt-cinq candidats restitués par catégorie du moteur et par requête, puis à trois organismes affichés par classe et par piste par défaut. Une catégorie saturée est déclarée tronquée. Les résultats négatifs sont exprimés comme **absence de concordance dans les bornes explorées**.

Chaque dossier porte explicitement les états non validés : besoin scientifique, capacité opérationnelle, disponibilité de la ressource, lien contractuel avec l'acheteur et qualification humaine. Ces états ne signifient pas que les réalités correspondantes sont absentes ; ils signalent qu'aucune vérification n'a été effectuée dans ce programme.

## Production reproductible

Depuis la racine du dépôt, après les étapes de construction des deux index et du bilan documentaire :

```bash
python scripts/croiser_pistes_capacites.py \
  --index-boamp /chemin/index-avis-boamp.sqlite3 \
  --preuve-index /chemin/preuve-index.json \
  --bilan /chemin/bilan-documentaire.json \
  --index-institutions /chemin/index-capacites-publiques.sqlite3 \
  --entites institutionnel/entites \
  --sortie /chemin/croisements-avis-capacites.json
```

La procédure automatique `.github/workflows/index-boamp-historique.yml` produit désormais le fichier `croisements-avis-capacites.json`, en conservant conjointement les bilans des deux index. Elle échoue si une preuve de source manque ou si les fichiers institutionnels ont évolué depuis la construction de l'index. Les tests hors connexion utilisent exclusivement des avis et organismes artificiels.

## Usage dans l'enquête

Le rapprochement doit servir à vérifier une hypothèse concrète, par exemple : une mission publique publiée recoupe-t-elle le domaine d'une commande technique ? L'étape suivante doit confronter les textes intégraux, l'objet réel de la commande, les ressources de l'acheteur, la compétence pratique du candidat, ses mécanismes de mise à disposition et les délais mesurés.

Aucun taux de pénurie, de recours externe substituable ou de performance de FRONTIÈRE ne découle du nombre de correspondances affichées. Le corpus de travail est délibérément sélectif ; les statistiques décrivent les seules pistes retenues. Une évaluation de l'utilité exige des jugements indépendants et des cas observés jusqu'à une première contribution réelle.
