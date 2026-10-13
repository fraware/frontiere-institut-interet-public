# Balayage borné de trois fichiers consolidés DECP complets

## Objectif

Le rapprochement initial des **sept références de contrat déclarées** dans les avis BOAMP examinés n'a donné aucune piste à SIRET concordant dans le relevé AIFE–DGFiP partiel de 3 008 identités documentaires. Cette absence n'est pas une absence de contrat national.

Les ministères économiques et financiers publient des [fichiers consolidés mensuels de données essentielles de la commande publique](https://www.data.gouv.fr/datasets/donnees-essentielles-de-la-commande-publique-fichiers-consolides), comprenant des données issues de plusieurs circuits. Les mois initiaux examinés sont **août 2025, février 2026 et avril 2026**. Ce choix se rapporte aux périodes de publication d'avis analysés ; il ne garantit pas que les marchés correspondants y figurent. L'absence d'un contrat dans ces trois mois n'établit pas qu'il soit absent des DECP.

## Protocole de capture et périmètre

Le programme `scripts/balayer_fichiers_consolides_decp.py` recharge la fiche **officielle actuelle** du catalogue consolidé et recoupe, pour chaque mois, l'identifiant de ressource, le titre exact, le format et le volume avec le catalogue déjà archivé dans `institutionnel/decp/etat_ressources.json`. Seules les trois ressources mensuelles prévues sont admissibles.

Le volume maximum est de **110 Mo par fichier** et **250 Mo au total**. Une réponse redirigée hors des domaines documentés de data.gouv.fr, un dépassement de volume, une variation de taille entre métadonnées et réponse, un objet JSON illisible ou un fichier tronqué provoquent l'arrêt. Le programme conserve dans son résultat l'adresse d'origine, les octets bruts de chaque fichier, l'empreinte SHA-256 de ce dernier, son identifiant administratif et le relevé des catégories d'enregistrements.

Le balayage réemploie le lecteur de fichiers JSON DECP et son normalisateur de marchés déjà testés dans le dépôt. Il parcourt l'intégralité des fichiers admis en mémoire bornée et compte séparément les marchés lus, les marchés acceptés par le profil, les marchés rejetés avec le motif, les concessions hors périmètre et les répétitions de clés documentaires à l'intérieur de chaque mois.

**Limites de l'analyse des dénominateurs :** une notice rejetée par les règles de normalisation n'est pas comparée. Le pourcentage de rejets est publié et toute analyse d'absence de correspondance doit le mentionner. Une même identité peut paraître dans différents mois ; les nombres d'identités mensuelles ne sont pas additionnés comme autant de contrats nationaux distincts. Les fichiers consolidés recouvrent potentiellement les publications AIFE et DGFiP déjà étudiées.

## Préselection des contrats

La liste des cibles est tirée du rapport officiel des 17 avis, conservé dans l'exécution GitHub n° 38480457531. Son empreinte SHA-256 est contrôlée exactement :

`8a9f220a66f61a4a0e1ea0104e3fd9c7a23395e791866e997b10922bfcaf82b8`

Le programme extrait seulement les **sept** références contractuelles compactes avec leurs SIRET acheteurs et l'avis où elles figurent. Il refuse une modification du nombre de références ou de leur provenance.

Pour chaque marché normalisé des trois fichiers, un rapprochement impose simultanément une référence contractuelle comparable et le SIRET de l'acheteur identique. La référence brute DECP, le numéro d'établissement, les dates et le mois de source sont préservés. Les références comparables apparaissant avec un **autre acheteur** sont présentées comme collisions documentaires, jamais comme piste de lien contractuel confirmé.

Même une égalité exacte des deux éléments est classée **piste documentaire**. La validation juridique exigerait encore les pièces contractuelles correspondantes, les références de lot, les différentes dates et le contrôle d'identité du marché au-delà d'une recherche textuelle.

## Reproduction

Le protocole est intégré à `.github/workflows/balayage-decp-consolides.yml`. Lors du premier passage sur la branche principale, la procédure vérifie les règles sans réseau, récupère le rapport de chaînage BOAMP à empreinte fixée, télécharge les trois fichiers consolidés officiels, parcourt leur contenu et conserve **le rapport et les octets primaires** en pièce jointe GitHub pendant quatorze jours. L'exécution manuelle est aussi possible. Il ne s'agit pas d'une couverture nationale permanente.

```bash
python -m pytest -q tests/test_balayer_fichiers_consolides_decp.py
python scripts/balayer_fichiers_consolides_decp.py \
  --chaines /source/chaines-documentaires-17.json \
  --etat institutionnel/decp/etat_ressources.json \
  --sortie /tmp/decp-trois-mois
```

Une mise à jour des fichiers administratifs sur data.gouv.fr peut modifier leur taille et entraîner un arrêt : cette précaution évite de considérer deux versions d'une même ressource comme identiques sans preuve. Les archives complètes conservées par GitHub permettent de reproduire l'étude pendant leur durée de conservation.

## Résultat autorisé

L'étude mesure le nombre de références de contrat BOAMP retrouvées parmi les marchés normalisés des trois fichiers mensuels précisément datés. Elle ne mesure ni un besoin toujours ouvert, ni un délai de mobilisation scientifique, ni un contrat juridiquement identifié. Les résultats ne sont généralisables ni au répertoire national complet des marchés ni à un échantillon représentatif des besoins technologiques.
