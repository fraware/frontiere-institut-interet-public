# Compte rendu vérifié — chronologies des six pilotes BOAMP

**Observation réalisée le 11 octobre 2026 (UTC).** Travail empirique exploratoire. Cette note est une restitution documentaire, non une conclusion causale ni une estimation représentative des difficultés de mobilisation des compétences publiques.

## Identité de la preuve

- Révision d'exécution : `d24f96b69764a81c6c96e754c91e414348fae079`.
- Exécution des captures et reconstructions : https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38184805903
- Archive des onze fichiers : https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38184805903/artifacts/11718654679
- Réussite sur les trois vérifications de `main` : https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38184805907
- Six avis de référence recherchés, six retrouvés ; un avis antérieur lié recherché, un retrouvé.
- Deux avis d'attribution ; trois avis d'appel d'offres initiaux ; un rectificatif.
- Trois résultats de lots explicitement codés dans les deux avis d'attribution : deux attribués, un non attribué.
- Nombre de délais observables du besoin à la première contribution utile : **zéro**. Ce chiffre mesure l'absence de tels délais dans les documents étudiés, et non une durée nulle.

## Tisséo — lien entre la consultation et sa correction

| Élément | Avis initial | Avis rectificatif |
| --- | --- | --- |
| Identifiant | `26-81640` | `26-83870` |
| Parution BOAMP | 2026-08-20 | 2026-08-29 |
| Nature | `APPEL_OFFRE` | `APPEL_OFFRE` |
| État | `INITIAL` | `RECTIFICATIF` |
| Objet déclaré | Audits de cybersécurité, ligne C du métro toulousain | Même objet déclaré |
| SHA-256 des octets HTTP de la réponse | `c435991dc020c6d561b8ecfd1aef85be5c3881c8eecef868480d9d7afaf825a5` | `1838cd3ae3b98868ca4361baf791e64f3dced68c8b61985d9b510c0d2c35ad5c` |

Le champ de référence `annonce_lie` du rectificatif contient littéralement `26-81640`. Le document structuré rectificatif contient une modification `efac:Changes/efac:Change/efbc:ChangeDescription`, portant sur la section `PROCEDURE` et formulée : « Au lieu de Sans objet, lire Les variantes sont interdites ».

L'identité, l'antériorité et le contenu des deux réponses ont été vérifiés. Elles attestent la consultation et sa correction documentaire ; elles ne renseignent pas une difficulté à trouver un auditeur disponible ni un délai jusqu'à la production d'un audit exploitable.

## Météo-France — calcul intensif

- Avis `26-74896`, publié le **28 juillet 2026**, de nature `ATTRIBUTION`.
- Titulaire déclaré `BULL SAS`.
- Champ `efac:SettledContract/cbc:AwardDate` : **20 juillet 2026**.
- Champ `efac:SettledContract/cbc:IssueDate` : **22 juillet 2026**.
- Lot `LOT-0001`, résultat `selec-w`, contrat `CON-0001`.
- SHA-256 des octets HTTP : `e5ee314a83f42135e0a6cf47976f03e52964ba6524a71b91363d1d2309b9109c`.

La différence entre décision et publication décrit uniquement un intervalle documentaire. La livraison, l'installation, l'accès aux calculs et la première utilisation scientifique demeurent inconnus.

## Université de Caen Normandie — télédétection radar

- Avis `26-30147`, publié le **25 mars 2026**, de nature `ATTRIBUTION`.
- Titulaire déclaré `ACTIMAR`.
- Champ `efac:SettledContract/cbc:AwardDate` : **24 septembre 2025**.
- Champ `efac:SettledContract/cbc:IssueDate` : **7 octobre 2025**.
- Lot `LOT-0001` : `selec-w`, contrat `CON-0001`.
- Lot `LOT-0002` : `clos-nw`, motif `no-rece`, sans contrat associé dans le résultat.
- SHA-256 des octets HTTP : `8be622f29d7490ec32fa28153f2f856b4a89202290f1f53ef5e7424e14c9eb3f`.

La publication est intervenue 182 jours après la date d'attribution déclarée. Il s'agit d'un **écart de publication**, sans démonstration de retard d'exécution ou de mobilisation de compétences. Il est impératif de conserver le résultat négatif du lot 2, car l'avis ne décrit pas une attribution intégrale.

## Règles de reproductibilité et limites

Les deux programmes `scripts/reconstituer_chronologies_pilotes_boamp.py` et `scripts/collecter_avis_lies_boamp.py` sont testés hors connexion et exécutés sur les captures officielles. Ils conservent les chemins des champs de preuve, les identifiants, les liens documentaires et les empreintes de réponses.

La date `cbc:AwardDate` placée dans un autre nœud `cac:TenderResult` contient dans les avis observés une valeur sentinelle du 1er janvier 2000. Elle est volontairement exclue au profit de la date explicitement portée par `efac:SettledContract`.

Aucune analyse n'a encore établi : la date d'origine du besoin, les démarches internes de recherche de compétences, l'offre réellement mobilisable, le début des travaux, la réception effective, la première contribution utile, ni une amélioration causale imputable à FRONTIÈRE. Ces rubriques restent **non observées**.

## Prochaine analyse admissible

1. Vérifier les dates et étapes de livraison ou de réception à partir de documents primaires explicitement rattachés aux marchés attribués.
2. Vérifier les documents de consultation de Tisséo pour identifier les compétences et exigences techniques réellement demandées.
3. Reconstituer séparément les mécanismes concurrents : acquisition ordinaire, prestation indépendante, contraintes techniques et éventuelle difficulté de mobilisation des compétences.
4. Construire des cas négatifs et indéterminés, puis tester les classements sur un échantillon indépendant.

L'objectif demeure de repérer les obstacles documentés entre un besoin scientifique ou technique et la première contribution utile, sans convertir des métadonnées de marchés publics en preuves de pénurie.
