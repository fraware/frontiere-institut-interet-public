# Ingestion progressive des données XML de la DGFiP

## Provenance et périmètre

Les fichiers XML du jeu [Données essentielles de la commande publique transmises via PES Marché depuis 2024](https://www.data.gouv.fr/datasets/donnees-essentielles-de-la-commande-publique-transmises-via-le-pes-marche-depuis-2024) sont une source complémentaire à l'API DECP de l'État et aux consolidations nationales. Ce circuit de la DGFiP concerne notamment les collectivités territoriales, établissements publics locaux et établissements publics de santé ; **il ne couvre pas les marchés de l'État**.

Le programme `scripts/ingerer_fichier_decp_xml.py` est fondé sur les exemples XML publics du [référentiel de données essentielles](https://github.com/139bercy/format-commande-publique/tree/master/exemples/xml), avec une enveloppe `marches`, des éléments `marche` et, éventuellement, `contrat-concession`. Les espaces de noms XML sont acceptés.

Les marchés sont ramenés au même **profil réduit** que les notices JSON AIFE : identifiant interne, SIRET de l'acheteur, objet, code CPV, dates, montant, nombre d'offres. Le profil ne contrôle pas l'intégralité du schéma réglementaire. Les concessions sont dénombrées séparément, sans fusion avec les marchés.

## Collecte par petits lots

Le programme `scripts/sonder_lot_decp_dgfip.py` s'appuie sur les **150 ressources récentes** déjà connues du catalogue local `institutionnel/decp/etat_ressources.json`. Pour chaque ressource choisie, il recoupe identifiant, format, taille et adresse avec la fiche publique actuelle de data.gouv.fr.

Il traite au plus **quatre fichiers XML par passage**, chacun limité à 1,5 Mo au téléchargement, avec origine HTTPS et redirections strictement contrôlées. L'analyse XML intervient en flux ; les déclarations d'entités ou DTD sont refusées. Le programme conserve le SHA-256 du fichier, les comptes de notices, les motifs de rejet et au plus 200 premières notices normalisées.

L'historique `institutionnel/decp/lot_dgfip_xml.json` conserve les **versions réellement téléchargées et analysées**, identifiées par identifiant de ressource, taille déclarée et date de modification du catalogue. Une ressource ayant échoué ne fait pas progresser le curseur. Une version déclarée différente peut être réanalysée. Le registre est limité à 2 000 versions documentaires et ne prétend pas couvrir l'ensemble des ressources DGFiP.

La procédure `.github/workflows/lot-decp-dgfip.yml` effectue un passage à **05 h 17 et 17 h 17 UTC**, sous réserve des délais de GitHub Actions. Les résultats ne sont proposés sur la branche principale qu'avec les vérifications Python 3.11, Python 3.12 et conteneur réussies sur le commit correspondant.

## Reproduction

```bash
python -m pytest -q tests/test_ingerer_fichier_decp_xml.py tests/test_sonder_lot_decp_dgfip.py

python scripts/ingerer_fichier_decp_xml.py \
  --entree /chemin/vers/ressource.xml \
  --source dgfip_pes_marche \
  --ressource-id 118544f1-b022-43d4-b8e0-3856f66a8b1d \
  --sortie /tmp/decp-xml-releve.json

python scripts/sonder_lot_decp_dgfip.py
```

## Limites de mesure

Un fichier décrit par le catalogue n'est pas une attribution nouvelle ; deux fichiers différents peuvent contenir le même marché. Les compteurs de ce premier dispositif sont des **compteurs par fichier** et ne constituent pas un total de marchés indépendants sur plusieurs ressources. La déduplication inter-fichiers demande un index de versions fondé sur l'identité composée `SIRET de l'acheteur + identifiant du marché`, déjà introduit dans le projet pour le JSON AIFE.

Les notices rejetées sont enregistrées par motif, sans reconstruction de valeurs absentes. Les fichiers contenant plus de 200 marchés normalisés disposent d'un compte total exact pour les objets observés, tout en indiquant que seuls 200 extraits sont conservés dans le relevé. Une véritable couverture nationale exige une ingestion de chaque ressource, un stockage persistant externe et un appariement documenté des attributions avec les avis BOAMP.

Le traitement XML n'établit ni la réalité d'un besoin encore ouvert, ni un délai de mobilisation, ni une première contribution utile. Ces faits appartiennent aux travaux de reconstitution des épisodes d'exécution.
