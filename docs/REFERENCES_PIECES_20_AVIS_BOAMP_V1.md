# Inventaire des références documentaires de 20 avis BOAMP

## Sources contrôlées

Les **17 avis indépendants**, issus du tirage de 36 avis conservé dans [l'exécution 38474330466](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38474330466), ont été complétés par les trois avis explicitement cités et retrouvés dans [l'exécution 38486850694](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38486850694) :

- Grand Charolais : attribution `26-37752` vers consultation initiale `25-122175`, du 4 novembre 2025. Référence interne `2025CC05` et numéro d'établissement identiques.
- AP-HP : avis `26-35619` vers avis initial `26-25119`, du 12 mars 2026. Référence `25-39_IT` et numéro d'établissement identiques.
- DGAC : avis `26-60102` vers avis initial `26-59281`, du 17 juin 2026. Référence `2026-SNARP-001` et numéro d'établissement identiques.

Le programme `scripts/inventorier_pieces_17_et_3_avis_boamp.py` examine les vingt réponses primaires dont les empreintes sont contrôlées. Il ne consulte aucun portail extérieur.

## Unité d'observation

Seuls les champs officiels `cac:ProcurementProjectLot/cac:TenderingTerms/cac:CallForTendersDocumentReference` sont dépouillés, avec distinction de la position du lot, de la référence textuelle de document et de l'adresse `cac:Attachment/cac:ExternalReference/cbc:URI`.

Le relevé initial a identifié **22 mentions documentaires parmi 14 avis**, sachant que plusieurs lots réutilisent la même adresse. Le programme conserve les mentions à l'unité du lot et publie également les comptes dédupliqués d'adresses par avis et dans l'ensemble du corpus. Il ne traite pas un même portail général comme un dossier de consultation identifié.

Une adresse est catégorisée à partir de sa forme textuelle, sans consultation du site :

- **Adresse de dossier référencée** : URL contenant un identifiant explicite de consultation dans l'adresse, tel que `PCSLID`, une page structurée de marché ou un identifiant de consultation du portail public.
- **Portail ou page générale** : adresse HTTPS sans identifiant de dossier clairement extrait.
- **Redirection externe non suivie** : lien de protection ou de réécriture d'une adresse, dont la destination n'est pas assimilée à une pièce vérifiée.
- **Adresse absente ou inexploitable** : adresse sans structure HTTPS admissible.

La catégorie « dossier référencé » désigne **un emplacement cité dans l'avis** ; elle ne certifie ni la disponibilité du dossier, ni l'authenticité des annexes, ni la possibilité de les obtenir sans identification.

## Concordances entre les trois paires d'avis

La consultation initiale du **Grand Charolais**, `25-122175`, comporte deux mentions du même lien de consultation, une par lot. L'avis d'attribution `26-37752` ne publie aucune adresse dans le champ documentaire étudié. Le lien explicite entre avis est vérifié, et l'adresse du dossier provient de l'avis initial.

L'avis initial **AP-HP `26-25119`** et l'avis ultérieur **`26-35619`** citent littéralement la même adresse de consultation sur PLACE, avec l'identifiant `2957868`. Cette concordance d'adresse renforce le rapprochement documentaire des deux avis, sans preuve que le contenu du dossier a été téléchargé ni qu'un contrat a été signé ou exécuté.

Les avis **DGAC `26-59281` et `26-60102`** citent le même domaine général de marchés publics. La concordance du portail est conservée, mais elle ne constitue **pas** une concordance d'identifiant de dossier.

## Protocole et limites

La procédure `.github/workflows/inventaire-pieces-20-avis.yml` récupère les archives déjà publiées et contrôlées. Elle reconstruit les références à partir des octets d'origine, conserve les chemins eForms et produit un rapport de provenance. Aucune authentification ni aucun téléchargement de document tiers ne sont tentés.

Les champs séparés `document_telecharge`, `acte_contractuel_verifie` et `premiere_contribution_utile_mesuree` restent à `false` ou zéro, en l'absence des pièces primaires nécessaires. Le fait que deux avis partagent une référence ou un lien de consultation ne démontre pas l'identité juridique du marché, les pouvoirs de signature, une réception contractuelle, un délai de mobilisation ou un déficit de compétences scientifiques.

## Reproduction

```bash
python -m pytest -q tests/test_inventorier_pieces_17_et_3_avis_boamp.py
python scripts/inventorier_pieces_17_et_3_avis_boamp.py \
  --archive-boamp /sources/historique.zip \
  --chaines /sources/chaines-documentaires-17.json \
  --avis-lies /sources/avis-lies \
  --sortie /tmp/frontiere-inventaire-pieces-20.json
```

La suite de l'enquête doit privilégier les documents **publiquement accessibles**, dont la provenance, les octets et la date peuvent être vérifiés, en excluant systématiquement les annexes sous restriction et les espaces nécessitant une authentification. Le prochain seuil est la possession d'une pièce authentique attribuable à une procédure précise ; les références de portail demeurent une étape documentaire distincte.
