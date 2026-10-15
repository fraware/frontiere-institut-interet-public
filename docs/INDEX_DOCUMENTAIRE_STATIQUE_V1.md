# FRONTIÈRE — Index documentaire gratuit, borné et traçable

## Fonctionnement

Le site Render reste **statique et gratuit**. À chaque déploiement manuel du site, la commande `node scripts/construire_index_statique.mjs` lit les données déjà versionnées dans GitHub, vérifie les sources et produit `site_frontiere/recherche-index.json`. L'index est un fichier JSON public servi tel quel par le site, sans API permanente, sans service payant et sans nouvelle collecte réseau.

L'index n'est pas commité dans le dépôt : il est **reconstruit depuis les fichiers sources à chaque publication**. Les changements de données dans GitHub n'affectent le site que lors du déploiement Render suivant. La configuration actuelle désactive les déploiements automatiques.

## Trois sources et plafonds

- **BOAMP :** jusqu'à 700 avis les plus récents parmi les annonces archivées dans `institutionnel/besoins_publics/annonces_boamp.json`, avec identifiant, titre, acheteur et lien d'avis officiel lorsqu'il est présent.
- **Emplois publics :** jusqu'à 700 références retenues parmi les seize partitions `offres_postes/lot_*.jsonl`. Les fichiers sont parcourus en lecture progressive, sans charger les centaines de milliers de variantes en mémoire. Les empreintes des seize partitions et leur décompte sont comparés au manifeste versionné.
- **DECP :** jusqu'à 500 marchés attribués dans les deux relevés AIFE et DGFiP conservés dans GitHub. Les couples SIRET–identifiant de marché sont dédoublonnés ; l'objet et la date de notification sont conservés avec la provenance.

La sélection privilégie la date la plus récente parmi les documents effectivement présents, avec classement et dédoublonnage déterministes. La limite du fichier est **2 Mo**. Une erreur de structure ou de provenance bloque la construction au lieu de publier une couverture non vérifiée.

Aucun contact nominatif, adresse électronique, téléphone ou champ de compétences à texte libre n'est copié vers le navigateur. Les trois corpus ont des significations distinctes : un avis BOAMP décrit une consultation, une offre d'emploi décrit un poste et un marché DECP décrit une attribution. Aucun de ces objets ne suffit à démontrer le besoin encore ouvert d'une institution.

## Exécution locale et tests

Prérequis : Node.js 20 ou supérieur.

```sh
node --test tests/test_index_statique.mjs
node scripts/construire_index_statique.mjs
```

La deuxième commande produit l'index dans le répertoire publié par Render. La procédure de vérification GitHub contient un contrôle indépendant `Index documentaire` qui exécute les essais sur données synthétiques, construit le fichier à partir des véritables archives et vérifie sa taille et son périmètre.

## Évolution des données

Le dernier relevé archivé dans GitHub, la date du déploiement et la période des documents ne sont pas équivalents. Aucune « actualisation en temps réel » n'est annoncée. Le fichier publie les identifiants des sources archivées et leurs empreintes afin qu'une sélection puisse être rattachée aux fichiers qui l'ont produite.

Un service de recherche exhaustif ou le traitement de documents géants nécessite ultérieurement des index découpés ou un mécanisme de recherche spécialisé. Ce premier extrait consultable vise un coût fixe nul et une rigueur documentaire mesurable.
