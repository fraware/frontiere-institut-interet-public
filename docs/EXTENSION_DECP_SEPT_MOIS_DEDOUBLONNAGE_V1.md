# Extension DECP à sept mois et dédoublonnage entre fichiers

## Question examinée

Les premiers fichiers consolidés d'août 2025, février 2026 et avril 2026 totalisent 85 181 observations de marchés après interprétation correcte des 21 922 mentions `NC` dans le nombre d'offres reçues. Ils contiennent 3 841 répétitions **à l'intérieur des fichiers mensuels**. La présence de mêmes identifiants dans plusieurs fichiers n'était pas encore mesurée.

Pour élargir la couverture des **sept références contractuelles BOAMP**, l'étude ajoute **octobre 2025, décembre 2025, mars 2026 et mai 2026**. Le choix est documentaire : les dates de publication des avis BOAMP et les dates de publication des données de marchés ne coïncident pas nécessairement. L'échantillon reste ciblé et non représentatif du territoire ou de l'ensemble des marchés français.

## Conservation de la preuve

Le programme `scripts/etendre_balayage_decp_sept_mois.py` réemploie les trois fichiers de [l'exécution initiale](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38481650597), dont le rapport et les trois empreintes SHA-256 sont contrôlés. Il réutilise les sept références de contrat et leurs identités d'acheteur issues du [rapport de filiation des 17 avis](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38480457531).

Seuls les **quatre fichiers supplémentaires** sont téléchargés depuis les ressources de data.gouv.fr. Le titre exact, le format, l'identifiant de ressource et la taille publiée sont recoupés entre la liste locale et le catalogue distant courant. Les limites sont de **160 millions d'octets par ressource** et **430 millions d'octets pour les quatre nouveaux fichiers**, afin de rejeter une source modifiée au-delà des ressources prévues. Les redirections vers des domaines non autorisés sont refusées.

Chaque fichier est conservé intégralement dans son état reçu. Les empreintes SHA-256 permettent de le distinguer des versions ultérieures d'un fichier portant le même titre. L'ensemble de l'étude est abandonné si l'une des quatre ressources ne respecte pas les critères documentaires ou si l'analyse échoue ; aucun rapport partiel n'est publié comme observation complète.

## Unités et mesures

Le lecteur et le normalisateur existants traitent en flux les marchés des sept fichiers. Les concessions sont comptées séparément. Une notice rejetée par le normalisateur est comptée avec son motif et n'entre pas dans les recherches de références. `offresRecues: "NC"` est interprété comme un nombre **non communiqué**, sans supposer zéro offre.

L'identité documentaire de marché est le couple **(SIRET de l'acheteur, identifiant de marché publié)**. Pour chaque couple, un condensat est calculé sur l'enregistrement normalisé. L'index distingue ainsi :

- les observations de marchés, avec leurs répétitions éventuelles ;
- les identités documentaires distinctes **entre les sept mois** ;
- les variantes distinctes d'une même identité ;
- les répétitions de variantes déjà rencontrées ;
- les identités présentes dans plusieurs mois, même à contenu identique ;
- les identités ayant plusieurs variantes documentaires.

Une variante de montant, d'objet ou de date ne démontre pas à elle seule un avenant, une nouvelle commande ou une erreur. L'analyse ne déduit ni date de début de mission ni date de première contribution utile à partir de la date de publication des données.

Les références BOAMP sont examinées sous leur forme normalisée, avec conservation de la référence brute et du SIRET exact de l'acheteur. Les références identiques publiées sous d'autres SIRET sont consignées séparément. Une même piste observée dans plusieurs mois n'est comptée qu'une fois comme identité documentaire candidate, tout en préservant la liste de ses mois et de ses dates de notification déclarées.

## Reproduction

```bash
python -m pytest -q \
  tests/test_balayer_fichiers_consolides_decp.py \
  tests/test_etendre_balayage_decp_sept_mois.py

python scripts/etendre_balayage_decp_sept_mois.py \
  --chaines /archives-boamp/chaines-documentaires-17.json \
  --archives-precedentes /archives-decp-trois-mois \
  --inventaire institutionnel/decp/etat_ressources.json \
  --sortie /tmp/frontiere-decp-sept-mois
```

La procédure `.github/workflows/decp-sept-mois.yml` télécharge les archives primaires déjà conservées, vérifie leurs empreintes fixées, recueille les quatre nouveaux fichiers, calcule le bilan commun et publie un artefact temporaire comprenant les fichiers originaux supplémentaires et leur rapport. Les fichiers archivés précédemment ne sont pas dupliqués dans le nouvel artefact.

## Limites

Le traitement porte exclusivement sur les **sept mois définis**, à une version déterminée de chaque fichier. Le catalogue consolidé comprend potentiellement des données déjà publiées dans les circuits AIFE et DGFiP : ces ensembles ne sont pas additionnés à l'index sans un contrôle de leur recouvrement.

Même en présence d'une référence et d'un SIRET identiques, la recherche établit seulement **une piste de correspondance documentaire**. Il faut confronter les unités de lots, les dates, les références de procédure, les actes contractuels et les pouvoirs juridiques de l'acheteur avant de conclure à un contrat confirmé. Aucun état de déficit de compétences ni aucun délai de mobilisation ne découle de cet inventaire.
