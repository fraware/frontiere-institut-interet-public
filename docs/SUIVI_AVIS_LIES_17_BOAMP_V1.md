# Reconstitution des avis explicitement liés aux 17 dossiers indépendants BOAMP

## Population et question

L'examen des **17 avis associés à 16 identifiants d'établissement** provenant du tirage indépendant de 36 avis constate **trois références explicites** dans le champ `annonce_lie` :

| Avis original | Nature de l'avis étudié | Avis cité |
| --- | --- | --- |
| 26-37752 | ATTRIBUTION, Le Grand Charolais | 25-122175 |
| 26-35619 | APPEL_OFFRE, AP-HP | 26-25119 |
| 26-60102 | APPEL_OFFRE, DGAC | 26-59281 |

Un seul des **six avis d'attribution** porte ce type de référence. Les cinq autres ne sont pas qualifiés « sans consultation initiale » : l'absence de champ renseigné ne vaut pas recherche historique exhaustive.

## Chaîne de preuve

Le programme `scripts/suivre_avis_lies_independants_boamp.py` relit les 36 avis capturés lors de [l'exécution de l'index BOAMP](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38474330466) et leur manifeste de réponse, ainsi que le [rapport des 17 chaînes](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38480457531). La relecture vérifie le nombre d'avis, chaque identifiant, les longueurs et les empreintes SHA-256 des octets primaires pertinents avant d'extraire les trois références textuelles.

La procédure `.github/workflows/suivi-avis-lies-independants.yml` ne recherche auprès de l'API de la DILA que ces **trois identifiants déjà déclarés**. Elle archive chacune des réponses HTTP sans transformation, avec son empreinte et l'URL de consultation. Un avis est qualifié de retrouvé seulement si son identifiant est exact et que sa date de publication précède ou égale celle du document qui le cite. Les résultats absents restent « non retrouvé lors du relevé » ; des réponses ambiguës, des dates futures, des structures invalides ou des octets altérés interrompent l'enquête.

Une concordance de référence interne de procédure, si les deux documents contiennent un identifiant exploitable, est distinguée d'une concordance de numéro d'établissement. Les discordances sont conservées comme observations, et aucune ressemblance de dénomination ou de numéro n'est présentée comme une identité juridique de marché.

## Valeur et limites

Le résultat probant attendu est l'existence et la qualification documentaire de chaque **lien cité**. La chronologie des publications ne constitue ni la chronologie contractuelle, ni le délai besoin–mobilisation, ni le délai jusqu'à la première contribution utile.

La récupération des avis d'une autre période ne constitue pas une récupération de dossier de consultation ou d'acte contractuel. Les liens de portail de marché figurant dans certaines notices demeurent des références annoncées, sans preuve que les annexes sont accessibles ou ont été téléchargées. Aucun acte signé, réception, autorité de représentation ou déficit de compétence n'est inféré.

## Reproduction

```bash
python -m pytest -q tests/test_suivre_avis_lies_independants_boamp.py

python scripts/suivre_avis_lies_independants_boamp.py \
  --archive-boamp /archives/historique.zip \
  --chaines /archives/chaines-documentaires-17.json \
  --sortie /tmp/frontiere-avis-lies

python scripts/suivre_avis_lies_independants_boamp.py \
  --archive-boamp /archives/historique.zip \
  --chaines /archives/chaines-documentaires-17.json \
  --verifier /tmp/frontiere-avis-lies
```

L'archive `historique.zip` ne contient que le manifeste `releve-issues-36/rapport.json` et les 36 réponses `releve-issues-36/<identifiant>.json` récupérées dans l'archive GitHub officielle, sans aucune modification de leurs octets. Le rapport officiel de l'exécution documente les trois qualifications et leur provenance. La prochaine étape documentaire consiste à contrôler, dans les avis réellement retrouvés, les adresses de pièces de consultation et le périmètre des lots sans franchir de mécanisme d'identification ni assimiler un portail à un acte contractuel.
