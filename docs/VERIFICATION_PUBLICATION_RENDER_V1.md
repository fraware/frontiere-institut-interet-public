# Vérification de la publication statique FRONTIÈRE — version 1

## Objet

Le dépôt conserve des archives et reconstruit plusieurs index. Le site public Render est un déploiement distinct, qui peut être construit à partir d'une révision Git plus ancienne. L'existence d'un déploiement déclaré « actif » ne garantit ni son actualité ni l'intégrité des fichiers réellement servis.

Le [premier audit local](ETAT_INITIAL_CHAINE_DOCUMENTAIRE_2026-10-16.md) et le programme `scripts/auditer_chaine_publication.py` contrôlent les populations archivées et les deux projections construites sur une même révision. Le programme `scripts/verifier_site_publie.py` complète cette vérification par une **lecture directe des fichiers du site actuellement publié**.

## Contrôle effectué

L'inspection récupère uniquement des fichiers JSON du domaine fixe `frontiere-observatoire-public.onrender.com`, sans authentification :

1. `recherche-index.json` — extrait principal de 1 900 documents au plus, selon les plafonds de construction actuels ;
2. `partitions/manifeste.json` — liste des partitions et leurs empreintes ;
3. `metadonnees-index.json` — révision et dates déclarées ;
4. tous les fichiers `partitions/part-<source>-<annee>-<numero>.json` déclarés dans le manifeste distant, avec bornes de taille, contrôle SHA-256 et dénombrement des documents.

Le contrôle compare les trois révisions déclarées, vérifie les identifiants uniques, les sources, les années, le nombre de documents et le contenu commun aux deux index publics. **Si la révision du site est exactement celle du travail GitHub**, il compare en outre les empreintes complètes du manifeste distant et de l'index principal avec celles des sorties construites dans le travail de vérification sur cette même révision.

Cette dernière comparaison est volontairement conditionnelle : deux révisions distinctes ne doivent pas être comparées comme si elles étaient identiques.

## États du rapport

| État | Signification |
| --- | --- |
| `a_jour_et_concordant` | Révision publiée égale à la révision attendue ; tous les documents contrôlés et octets déterministes concordants |
| `revision_distincte` | Pièces publiées cohérentes entre elles, mais révision différente de celle attendue |
| `revision_non_verifiable` | Les documents sont cohérents, mais la révision n'est pas attestée et l'actualité ne peut être affirmée |
| `publication_inaccessible` | Accès distant interrompu ; aucune vérification d'intégrité revendiquée |
| `publication_incoherente` | Une preuve, un décompte, un document ou une relation entre manifestes a échoué au contrôle |

Un site inaccessible ne sera jamais enregistré comme « à jour ». Les incidents d'accès distants sont inscrits dans le rapport sans faire échouer l'ensemble des contrôles locaux, afin de distinguer une indisponibilité externe temporaire d'une régression documentaire. Une incohérence intrinsèque des documents publics est considérée comme un défaut du contrôle de publication.

## Déclenchement et reproductibilité

Les essais entièrement synthétiques s'exécutent dans les travaux Python généraux. La procédure principale de GitHub construit les deux index statiques sur les archives réelles ; sur une exécution **push vers main**, elle interroge ensuite le site Render en lecture seule et archive le rapport JSON durant 14 jours, sans enregistrement dans les fichiers sources de Git.

Commande manuelle en environnement ayant accès au site public :

```sh
python -m scripts.verifier_site_publie \
  --revision "<SHA du commit attendu>" \
  --rapport /tmp/frontiere-publication.json
```

Cette commande réalise des requêtes réseau. Les tests synthétiques du fichier `tests/test_verifier_site_publie.py` n'effectuent aucune requête externe.

## Limites et gestion du déploiement

- Le programme ne modifie ni le dépôt distant ni le service Render, et n'engage aucune dépense supplémentaire.
- Les fichiers ne donnent accès qu'à l'extrait statique déclaré ; ils ne prouvent pas la présence des index SQLite intégraux sur Render.
- Une empreinte correcte établit une cohérence entre les octets présents et l'attestation du manifeste. Elle ne prouve pas l'exactitude de la donnée chez son producteur.
- Le script contrôle le contenu publié, mais ne vérifie pas le cache de chaque utilisateur, les performances, ni la continuité de disponibilité.
- Une mise à jour du site nécessite un déploiement distinct, décidé sur une révision vérifiée. L'autodéploiement reste désactivé.

Pour la [tâche n° 537](https://github.com/fraware/frontiere-institut-interet-public/issues/537), le résultat attendu est un rapport contenant l'état exact du site et ses dénominateurs, suivi d'une décision explicite sur une éventuelle publication d'une révision plus récente.
