# Structures de recherche publiques actives — importation RNSR

## Source, objet et portée

FRONTIÈRE complète les notices administratives de la Direction de l’information légale et administrative par une source spécialisée du ministère chargé de l’enseignement supérieur et de la recherche : [Structures de recherche publiques actives](https://data.esr.gouv.fr/donnees-ouvertes/ods-fr-esr-structures-recherche-publiques-actives), issue du Répertoire national des structures de recherche (RNSR).

Le jeu comporte environ **4 767 enregistrements** dans la publication observée en 2026 et fournit notamment un identifiant national de structure, une dénomination, un type d’unité et, selon les notices, des classifications scientifiques. Ce périmètre concerne les **structures considérées comme actives dans la publication source** ; il ne fournit pas une mesure en temps réel de l’activité, des effectifs, des équipements disponibles ou des conditions de collaboration.

Le registre institutionnel distingue cette collection active (`mesr_rnsr_structures_actives`) du jeu général RNSR, qui comprend également des structures historiques ou inactives.

## Transformation conservatoire

Le programme `scripts/ingerer_structures_rnsr.py` récupère les enregistrements officiels par pages et valide la pagination complète, l’unicité des identifiants RNSR et la présence des noms. Il reconstruit ensuite des notices au format institutionnel FRONTIÈRE.

Chaque structure reçoit un identifiant de la forme `FRONTIERE-INST-RNSR-<IDENTIFIANT>`. Ce nouvel espace d’identifiants évite de fusionner par inadvertance une structure de recherche avec un service de l’Annuaire portant un nom semblable. Les éventuels raccordements futurs devront utiliser des identifiants partagés ou des relations expressément publiées.

Une notice peut contenir, selon ce qui figure dans la source : nom et sigle, type de structure, commune, site officiel, fiche RNSR, classification par domaine scientifique, classification européenne de recherche et codes officiels associés. Les codes et leurs libellés restent séparés. Une classification absente reste absente.

Les classifications scientifiques sont enregistrées dans `domaines_recherche`. Les champs `missions` et `capacites` sont volontairement **vides** pour cette source : un rattachement disciplinaire, un intitulé de laboratoire ou un code européen ne démontre pas, à lui seul, qu’une compétence technique particulière soit disponible ou mobilisable.

Les noms de responsables et autres informations personnelles figurant éventuellement dans la publication originale ne sont pas reproduits dans ces nouvelles notices.

## Identité temporelle et provenance

Chaque notice conserve l’identifiant national exact de la source, l’adresse de la publication, la date de collecte et une empreinte SHA-256 calculée sur l’enregistrement source. Les enregistrements inchangés conservent leur date d’observation précédente lors d’une actualisation. Les changements sont détectés indépendamment de l’ordre des lignes reçu depuis le service officiel.

Le traitement refuse les identifiants répétés, les noms manquants, les pages incomplètes, les variations du nombre total d’enregistrements en cours de collecte et une diminution de plus de 15 % du nombre de structures sans examen préalable. Il ne supprime ni ne fusionne silencieusement des organisations.

Les sorties sont réparties dans huit fichiers sous `institutionnel/entites/rnsr/`. Le manifeste figure dans `institutionnel/instantanes/rnsr_manifest.json`, et les mesures de couverture dans `institutionnel/statistiques_rnsr.json`.

## Actualisation autonome

Pour exécuter l’importation depuis la racine du dépôt :

```bash
python scripts/ingerer_structures_rnsr.py
```

Pour éprouver une réponse enregistrée sans accès extérieur :

```bash
python scripts/ingerer_structures_rnsr.py \
  --source-json /chemin/vers/reponse-complete.json \
  --destination /chemin/vers/repertoire-experimental
```

La procédure automatisée `.github/workflows/ingestion-rnsr.yml` vérifie les essais sur des notices fictives, récupère le jeu public, examine la couverture et, après réussite, enregistre les nouvelles notices dans le dépôt lors d’une exécution sur la branche principale. L’importation des structures RNSR ne modifie pas les fichiers de la DILA.

## Limites expérimentales

L’indexation du RNSR fournit des **pistes de structures et de domaines scientifiques**, non une liste certifiée de personnes, d’instruments ou d’équipes prêtes à intervenir. Une structure absente du jeu des unités actives peut être présente dans le registre historique ou dans d’autres catalogues. Le contrôle des disciplines, de la pertinence pour un besoin et de la disponibilité réelle exige des sources complémentaires.

L’intégration d’une nouvelle source ne représente pas un résultat comparatif favorable à FRONTIÈRE. La séparation entre identité administrative, mission publiée, discipline recensée, capacité technique et mobilisation effective doit être maintenue dans tout outil de recherche.
