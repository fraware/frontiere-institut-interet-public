# Revue initiale des dix publications repérées — 14 octobre 2026

## Méthode

Le premier contrôle opérationnel du dispositif de veille a sélectionné 21 pistes, dont **dix publications de flux institutionnels** et onze références de délibérations SCDL. Cette note qualifie uniquement les dix publications de flux. Les onze actes demeurent suivis par l'enquête propre aux délibérations.

Le registre `institutionnel/veille/revue_signaux_2026_10_14.json` est un relevé **interprétatif provisoire établi sur les titres et extraits conservés dans le dépôt**, sans prétendre à une lecture des documents complets. Chaque entrée contient l'identifiant de l'observation, l'empreinte du texte consulté, le producteur, la date de publication déclarée, une question précise et la pièce primaire à obtenir.

Les cinq catégories ne constituent ni des notes de qualité, ni un classement statistique, ni la démonstration d'un besoin technique. Les entrées classées comme pistes de mécanisme scientifique ou institutionnel désignent uniquement des **comparateurs intéressants à instruire**.

## Répartition observée

| Orientation provisoire | Nombre | Nature |
| --- | ---: | --- |
| Mécanismes scientifiques à étudier | 2 | Appel ANR/NRF sur l'IA pour les biotechnologies ; appel ANR sur la coproduction des politiques publiques par l'expertise scientifique |
| Mécanisme institutionnel à étudier | 1 | Installation et programme du Conseil national de la commande publique |
| Contexte réglementaire | 5 | Règles de marchés publics, fiscalité et relations contractuelles |
| Contexte sectoriel | 1 | Baromètre numérique des entreprises |
| Commentaire général | 1 | Tribune sur le budget de la recherche |

**Ce dénombrement porte uniquement sur dix publications initialement sélectionnées par des expressions précises.** Il ne mesure ni la répartition nationale des besoins, ni la pertinence de l'ensemble des 287 publications archivées. La présence d'un terme ne suffit pas à qualifier le signal. L'une des publications provient d'une tribune relayée par un compte public : son contenu demeure celui d'une tribune et non une position institutionnelle vérifiée de l'organisme relais.

Quatre publications sont archivées sans date de publication exploitable. La date de collecte du flux n'est pas utilisée pour reconstituer ces dates.

## Enquêtes à privilégier

La première piste est l'appel [ANR « Science avec et pour la société — Co-construire les politiques publiques par l'expertise scientifique »](https://bsky.app/profile/agencerecherche.bsky.social/post/3m7s7rzgxv227). Il s'agit d'un comparateur potentiel particulièrement pertinent de mobilisation collective de recherche vers les institutions. L'enquête doit retrouver l'appel primaire, les projets financés, les partenaires publics, les résultats et les conditions de transfert. **L'annonce seule ne prouve aucune réalisation.**

La deuxième piste est la documentation du [Conseil national de la commande publique](https://www.economie.gouv.fr/daj/le-conseil-national-de-la-commande-publique-adopte-son-reglement-interieur-et-son-programme-de-travail). Le décret fondateur, les actes d'organisation et le programme de travail permettraient de qualifier un mécanisme institutionnel déjà en place. La date précise de l'annonce n'est pas établie par le flux archivistique.

La troisième piste concerne [l'appel ANR–NRF sur l'intelligence artificielle appliquée aux biotechnologies](https://bsky.app/profile/agencerecherche.bsky.social/post/3mivln4k3ws2b). Elle relève d'abord du financement scientifique : son rapprochement avec la capacité opérationnelle d'une administration demande des preuves supplémentaires.

La publication sur le baromètre France Num 2026 constitue un exemple de **source potentiellement utile pour des comparaisons de contexte**, si l'échantillon et les questions abordent les organismes qui intéressent l'étude. La disponibilité de cette information ne doit pas être supposée sans lecture de la méthodologie.

## Fiabilité des qualifications dans le temps

Une qualification humaine ne doit pas être propagée silencieusement vers une nouvelle version d'un texte institutionnel. Le programme `scripts/reverifier_qualifications_veille.py` compare les dix identifiants et empreintes enregistrés aux observations actuellement archivées et publie quatre états :

- `identique` : empreinte et producteur identiques au relevé de référence ;
- `revision_a_requalifier` : texte modifié sous le même identifiant ;
- `identite_source_modifiee` : rattachement du signal à un autre producteur ;
- `observation_absente` : source non retrouvée dans le registre courant.

Ce contrôle **ne requalifie jamais automatiquement le contenu** et ne garantit pas qu'une publication identique soit exacte. Il transmet les divergences comme points de relecture. Il ne bloque pas les collectes régulières lorsqu'un producteur corrige une publication.

Le contrôle transversal de veille produit des fichiers JSON et Markdown à chaque exécution et les conserve parmi les artefacts temporaires GitHub Actions. Le registre de qualification, quant à lui, reste un instantané documentaire daté.

## Limites et prochaine décision

Aucune de ces dix notices n'a été promue dans un registre d'épisodes de mobilisation, aucun besoin déficitaire n'a été certifié et aucune pièce juridique primaire n'a été considérée lue à partir du seul flux RSS ou du compte social. La suite consiste à confronter les trois comparateurs pressentis aux sources originales, puis à enregistrer séparément les conclusions positives, négatives ou indéterminées.
