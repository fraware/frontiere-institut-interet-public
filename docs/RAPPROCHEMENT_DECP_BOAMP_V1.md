# Rapprochement documentaire conservateur BOAMP / DECP

## Portée

Le programme `scripts/rapprocher_decp_boamp_identifiants.py` prépare des pistes de correspondance entre les avis BOAMP et l'index local des marchés DECP issu des données AIFE et DGFiP.

**Il ne récupère pas automatiquement les identifiants BOAMP manquants.** Le premier intrant est un registre d'observations de références explicitement relevées dans des avis officiels. Ces références doivent encore être confrontées à la réponse primaire : le programme n'effectue pas cette vérification et le signale dans chaque résultat.

La correspondance s'effectue sur l'égalité stricte du couple (SIRET de l'acheteur, identifiant du marché). Aucun rapprochement de nom d'organisme, d'objet ou de date n'est admis. Plusieurs clés possibles restent ambiguës. Une clé égale constitue seulement une **piste**, pas une identité juridique prouvée.

## Entrées

Construire d'abord l'index à partir des relevés déjà archivés :

```bash
python scripts/consolider_attributions_decp.py --base /tmp/frontiere-decp.sqlite3
```

Exemple de format d'attestations, avec des **valeurs fictives** qui ne doivent jamais être utilisées pour produire des résultats empiriques :

```json
{
  "version": "references-boamp-decp-v1",
  "avis": [
    {
      "id_boamp": "26-30147",
      "url_source": "https://www.boamp.fr/exemple-fictif",
      "references": [
        {
          "acheteur_siret": "12345678901234",
          "id_marche": "M-1",
          "chemin_preuve": "/results/0/donnees/EFORMS/reference"
        }
      ]
    }
  ]
}
```

Chaque avis utilisé en pratique doit être saisi depuis la réponse officielle, avec un chemin effectif et complet pour la preuve. Le programme ne fait aucune affirmation selon laquelle le chemin fourni existe dans la réponse.

```bash
python scripts/rapprocher_decp_boamp_identifiants.py \
  --base /tmp/frontiere-decp.sqlite3 \
  --attestations /tmp/references-boamp-verifiees.json \
  --sortie /tmp/rapprochements-boamp-decp.json

pytest -q tests/test_rapprocher_decp_boamp_identifiants.py
```

## Interprétation

- `cle_exacte_candidate` : une identité DECP distincte porte la clé transcrite depuis l'avis.
- `plusieurs_cles_candidates` : plusieurs marchés correspondent aux références fournies, sans résolution arbitraire.
- `aucune_cle_commune` : absence de correspondance dans la base **partielle** examinée, sans implication sur le marché réel.

Le champ `liens_juridiques_verifies` est toujours nul. Un suivi ultérieur devra vérifier les octets de la source BOAMP, les rôles exacts des identifiants, les changements de procédure, les lots, et la relation entre avis initial, attribution et contrat. Aucun résultat ne constitue une mesure de rareté des compétences ni de temps jusqu'à une contribution utile.

## Étape suivante

Extraire directement depuis les réponses BOAMP originales les références contractuelles, les SIRET et les chemins JSON de preuve, puis intégrer une vérification cryptographique de chaque source avant toute qualification supérieure à « piste documentaire ». La couverture actuelle du DECP reste limitée aux relevés conservés.
