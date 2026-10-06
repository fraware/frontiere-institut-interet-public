# Ingestion de l'Annuaire de l'administration — services locaux

## Objet

Cette ingestion étend le graphe institutionnel de FRONTIÈRE de l'organisation administrative de l'État vers les implantations et guichets publics locaux publiés par la Direction de l'information légale et administrative.

La source canonique utilisée est l'API de l'Annuaire de l'administration :

https://api-lannuaire.service-public.gouv.fr/

La page de référence du jeu de données est :

https://www.data.gouv.fr/datasets/service-public-gouv-fr-annuaire-de-ladministration-base-de-donnees-locales

## État observé au 6 octobre 2026

L'export courant contient **93 782 enregistrements** répartis en trois catégories DILA :

| Catégorie | Nombre | Traitement FRONTIÈRE |
| --- | ---: | --- |
| SI | 7 903 | déjà ingérés par le Référentiel de l'organisation administrative de l'État |
| SL | 79 585 | ingérés par cette ingestion |
| SIL | 6 294 | ingérés par cette ingestion |
| **Total** | **93 782** | **couvert par l'union des deux ingestions DILA** |

FRONTIÈRE possède donc un objet canonique pour chaque enregistrement du snapshot courant de l'Annuaire DILA. Cette complétude est **relative à ce référentiel et à cette date**. Elle ne signifie pas que les 93 782 objets constituent l'intégralité des personnes morales, organismes, collectivités, opérateurs, établissements de santé ou structures de recherche du secteur public français.

Les catégories SL et SIL produisent **85 879 entités locales canoniques**.

### Couverture des attributs locaux

| Attribut | Entités |
| --- | ---: |
| Coordonnées | 85 696 |
| Territoire directement publié | 85 581 |
| SIRET | 54 651 |
| SIREN | 44 048 |
| Mission publiée | 29 905 |
| Responsable publié | 5 201 |
| Fondement juridique | 1 546 |

Les absences restent des absences de la source utilisée. FRONTIÈRE ne complète pas un champ manquant par inférence silencieuse.

## Hiérarchie et croisement avec le référentiel de l'État

L'ingestion produit **4 155 relations hiérarchiques résolues** à partir des liens publiés par la DILA. **3 536 entités locales** reçoivent un parent principal directement justifié par un lien `Service Fils`.

Le snapshot local conserve **100 références hiérarchiques non résolues**. Leur identifiant cible n'apparaît ni parmi les 85 879 objets SL/SIL courants ni parmi les 7 903 objets SI courants. Le dépôt les conserve dans `institutionnel/anomalies_annuaire_local.json` et ne leur attribue aucune cible par similarité de nom.

L'apport du croisement des deux flux est mesurable : les **158 références hiérarchiques du ROAE qui restaient orphelines dans le seul flux SI sont toutes résolues par des identifiants présents dans le flux local**. Le résultat est enregistré dans `institutionnel/resolution_roae_local.json`.

## Compétence géographique

La DILA publie séparément un jeu de compétence géographique qui associe une commune, un type de service local et un ou plusieurs identifiants de services compétents.

Le jeu est interrogé directement via :

https://api-lannuaire.service-public.gouv.fr/

Ce graphe comporte plusieurs millions d'enregistrements. FRONTIÈRE ne le recopie pas intégralement dans Git. Le dépôt conserve une interface d'interrogation directe vers la source officielle et résout les identifiants retournés vers les entités canoniques locales ou SI.

Exemple reproductible :

```bash
python scripts/rechercher_competence_geographique.py --commune 75056 --type mairie
```

Le contrôle en intégration continue du 6 octobre 2026 a retourné pour la commune Insee `75056` et le type `mairie` l'identifiant DILA de **Mairie - Paris - Hôtel-de-Ville**, résolu vers son identifiant canonique FRONTIÈRE.

Cette stratégie sépare deux objets :

- le **stock institutionnel canonique**, versionné dans Git ;
- le **graphe massif de compétence géographique**, interrogé à la source au moment de la requête.

La séparation évite de transformer le dépôt Git en entrepôt de plusieurs millions d'arêtes tout en conservant une réponse fondée sur le référentiel officiel courant.

## Identité et provenance

Chaque entité locale possède un identifiant de la forme :

```text
FRONTIERE-INST-DILA-LOCAL-<IDENTIFIANT DILA>
```

L'identifiant DILA d'origine, les SIREN, les SIRET, les identifiants partenaires, les territoires, les coordonnées, les missions et les autres champs disponibles restent séparés.

Chaque objet conserve :

- l'identifiant dans la source ;
- l'adresse de la source ;
- la date de collecte ;
- une empreinte de l'enregistrement ;
- les champs structurés utiles à l'exploitation opérationnelle.

Les identifiants DILA locaux du snapshot courant sont disjoints des identifiants DILA SI du ROAE. Cette propriété est vérifiée automatiquement.

## Stabilité des mises à jour

L'export JSON de l'API peut varier au niveau des octets ou de l'ordre des enregistrements sans changement sémantique du référentiel.

FRONTIÈRE calcule donc deux empreintes :

1. l'empreinte SHA-256 du fichier transporté ;
2. une empreinte sémantique construite à partir des empreintes triées de tous les enregistrements.

L'empreinte sémantique courante est :

```text
766773e42de8e5cff961c03c9f9bde3c2e7f6d2e2753ca535b366a8a90a0c6d8
```

Une variation d'ordre dans l'export ne produit ainsi aucun faux changement institutionnel et aucun commit inutile.

## Sorties

```text
institutionnel/
  entites/locales/
    annuaire_local_000.jsonl
    ...
    annuaire_local_127.jsonl
  relations/locales/
    hierarchie_locale_000.jsonl
    ...
    hierarchie_locale_031.jsonl
  instantanes/
    annuaire_local_manifest.json
  statistiques_annuaire_local.json
  anomalies_annuaire_local.json
  resolution_roae_local.json
```

Les 85 879 entités sont réparties dans 128 partitions. Les relations sont réparties dans 32 partitions.

## Vérifications automatiques

La suite de tests vérifie notamment :

- les empreintes et tailles de toutes les partitions ;
- les nombres d'entités et de relations ;
- l'unicité des identifiants ;
- la disjonction des identifiants DILA SI et locaux ;
- l'existence des deux extrémités de chaque relation ;
- la justification de chaque parent principal ;
- la provenance de chaque entité locale ;
- la cohérence entre les trois catégories DILA et l'export complet ;
- la résolution croisée des 158 références du ROAE ;
- le décodage des champs structurés transportés sous forme de chaînes JSON ;
- la recherche de compétence géographique.

Les tests du snapshot sont écrits en lecture progressive afin de contrôler environ 230 Mo de représentation canonique sans charger le corpus entier en mémoire.

## Mise à jour

Une action GitHub quotidienne exécute l'ingestion après l'actualisation du ROAE.

Elle :

1. vérifie l'importeur ;
2. télécharge l'export courant de l'Annuaire ;
3. calcule son empreinte sémantique ;
4. reconstruit le snapshot uniquement si nécessaire ;
5. vérifie le snapshot complet ;
6. interroge une compétence géographique réelle comme contrôle de bout en bout ;
7. écrit un commit uniquement en présence d'un changement sémantique.

## Limites et prochaine vague

L'union ROAE + Annuaire fournit désormais une couverture complète du **snapshot courant de l'Annuaire DILA**, y compris ses objets SI, SL et SIL.

La construction du référentiel public français reste plus large. Les prochaines sources prioritaires sont :

- le Code officiel géographique pour les collectivités et l'historique territorial ;
- BANATIC pour les intercommunalités, syndicats et compétences ;
- le périmètre budgétaire des opérateurs de l'État ;
- les structures publiques d'enseignement supérieur et de recherche ;
- FINESS pour les structures sanitaires, sociales et médico-sociales ;
- les participations publiques ;
- les textes et événements juridiques.

La règle reste identique : chaque nouvelle source doit augmenter une couverture mesurée, conserver sa provenance et exposer explicitement ce qu'elle laisse encore inconnu.
