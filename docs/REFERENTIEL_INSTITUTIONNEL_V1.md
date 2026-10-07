# Référentiel institutionnel vivant — version 1

## Finalité

FRONTIÈRE doit disposer d'une représentation à jour, traçable et interrogeable de l'écosystème public français.

L'objectif n'est pas de constituer un annuaire supplémentaire. Le référentiel doit permettre de répondre à des questions opérationnelles :

- quelle institution détient une compétence donnée ;
- de quelle autorité dépend-elle ;
- quelles unités lui sont rattachées ;
- quel territoire couvre-t-elle ;
- quels responsables exercent les fonctions pertinentes ;
- quels opérateurs, établissements, laboratoires ou services disposent d'une capacité scientifique ou technique mobilisable ;
- quels textes fondent son existence et ses compétences ;
- quels changements institutionnels récents modifient la réponse ;
- quelle voie de mobilisation existe entre un besoin public et cette capacité.

Le référentiel devient ainsi le socle commun de la recherche publique, de l'identification des capacités et du suivi institutionnel.

## Principe d'exhaustivité mesurable

L'exhaustivité absolue est une propriété impossible à affirmer durablement pour un système institutionnel qui évolue chaque jour.

FRONTIÈRE retient une définition vérifiable :

> le référentiel est complet pour un périmètre donné si toutes les familles institutionnelles déclarées dans la matrice de couverture sont alimentées par leurs sources de référence, si chaque source critique est à jour selon sa cadence attendue, et si chaque entité importée conserve sa provenance.

Le système doit donc publier en permanence :

- les familles couvertes ;
- les sources attendues ;
- la date de dernière observation ;
- la fraîcheur de chaque source ;
- le nombre d'entités intégrées ;
- les identifiants non résolus ;
- les relations non résolues ;
- les sources en erreur ;
- les changements en attente de validation humaine.

Une zone inconnue doit rester explicitement inconnue.

## Périmètre institutionnel

Le référentiel couvre progressivement onze ensembles.

### 1. Institutions constitutionnelles et Gouvernement

Présidence de la République, Gouvernement, Premier ministre, Parlement, Conseil constitutionnel, Conseil économique, social et environnemental et autres institutions prévues par les textes constitutionnels.

### 2. Administration centrale de l'État

Ministères, secrétariats généraux, directions générales, directions, services, sous-directions, bureaux, délégations, missions et services à compétence nationale.

### 3. Administration territoriale de l'État

Préfectures, sous-préfectures, directions régionales et départementales, services territoriaux, services déconcentrés et implantations locales.

### 4. Autorités indépendantes

Autorités administratives indépendantes et autorités publiques indépendantes, avec leur texte fondateur, leur statut, leur collège et leurs fonctions.

### 5. Opérateurs et établissements publics

Opérateurs de l'État, établissements publics administratifs, établissements publics industriels et commerciaux, établissements publics à caractère scientifique et technologique, grands établissements et autres personnes morales publiques.

### 6. Collectivités territoriales et intercommunalités

Régions, départements, collectivités à statut particulier, communes, établissements publics de coopération intercommunale, syndicats et autres groupements recensés par les référentiels officiels.

### 7. Santé et secteur médico-social public

Agences, établissements et structures publiques du champ sanitaire, social et médico-social, avec leurs activités et implantations lorsque les données de référence le permettent.

### 8. Enseignement supérieur et recherche publique

Universités, écoles, organismes de recherche, structures de recherche, unités, tutelles et relations entre établissements et laboratoires.

### 9. Justice et juridictions

Juridictions administratives et judiciaires, services associés et organisation territoriale.

### 10. Réseau diplomatique et opérateurs extérieurs

Ambassades, consulats, représentations permanentes, services économiques et autres implantations publiques à l'étranger.

### 11. Participations et entreprises sous contrôle ou influence publique

Portefeuille de l'Agence des participations de l'État et autres entités lorsque leur relation institutionnelle avec l'État est pertinente pour une capacité publique.

## Sources de référence

Le premier socle est le Référentiel de l'organisation administrative de l'État de la DILA. Le snapshot observé le 6 octobre 2026 contient **7 903 objets SI**, jusqu'au niveau de nombreuses unités internes, avec missions, hiérarchie, coordonnées et responsables selon les objets.

Le second socle est l'API de l'Annuaire de l'administration. Le même snapshot courant contient **79 585 objets SL** et **6 294 objets SIL**, soit **85 879 objets locaux**. L'union des ingestions SI, SL et SIL couvre ainsi les **93 782 enregistrements** de l'export DILA observé à cette date.

La DILA publie également un jeu distinct de compétence géographique reliant communes, types de services et identifiants de services compétents. Ce jeu massif est interrogé directement par FRONTIÈRE au moment d'une recherche territoriale. Il reste une source officielle du graphe même si ses millions d'arêtes ne sont pas recopiées dans Git.

Cette complétude concerne le périmètre de l'Annuaire DILA. Elle ne suffit pas à représenter l'ensemble de l'écosystème public. Le graphe doit encore être complété par le Code officiel géographique de l'Insee, BANATIC pour les intercommunalités, le budget de l'État pour les opérateurs, Légifrance et le Journal officiel pour les textes et changements, les données du ministère chargé de l'enseignement supérieur et de la recherche, FINESS pour la santé, et le portefeuille de l'Agence des participations de l'État.

Le registre exact des sources et de leur cadence figure dans `institutionnel/sources_v1.json`.

### Référentiel territorial distinct

Le Code officiel géographique alimente un espace d’identité territorial séparé du graphe institutionnel. Une commune, un département, une région, un arrondissement ou un canton constitue une unité territoriale ; une mairie, une préfecture, un conseil départemental ou une autre collectivité organisée constitue un objet institutionnel. FRONTIÈRE relie ces familles par des relations explicites au lieu de les fusionner.

Cette distinction vaut également pour les codes `CTCD` du COG. Le fichier Insee correspondant décrit des collectivités territoriales exerçant les compétences départementales. Ces codes restent conservés dans la provenance COG et feront l’objet d’une résolution institutionnelle dédiée ; ils ne deviennent pas des nœuds territoriaux par défaut.

## Modèle canonique

Chaque institution reçoit un identifiant interne stable `FRONTIERE-INST-...`.

Une entité canonique sépare plusieurs blocs.

### Identité

- nom officiel ;
- sigle ;
- anciens noms ;
- type institutionnel ;
- nature juridique ;
- personnalité morale ;
- état actif, transformé, fusionné ou supprimé.

### Identifiants externes

Selon les cas :

- identifiant DILA ;
- SIREN et SIRET ;
- code Insee ;
- identifiant UAI ;
- identifiant FINESS ;
- identifiant RNSR ;
- identifiants budgétaires ;
- identifiants propres aux sources sectorielles.

Les correspondances sont conservées avec leur provenance.

### Position institutionnelle

- autorité de rattachement ;
- ministère de tutelle ;
- entité parente ;
- entités filles ;
- opérateur ou programme budgétaire de rattachement ;
- territoire de compétence ;
- relations de tutelle scientifique ou administrative.

### Mission et compétences

Les missions et compétences sont enregistrées comme des assertions sourcées. Une formulation issue d'une source officielle reste distincte d'une interprétation analytique produite par FRONTIÈRE.

### Responsables

Pour chaque fonction :

- intitulé de la fonction ;
- titulaire ;
- date de prise de fonction lorsque disponible ;
- texte ou source de nomination ;
- date de dernière vérification.

Les changements de responsables sont des événements institutionnels.

### Capacités

Le référentiel ajoute progressivement une représentation des capacités scientifiques et techniques :

- domaines ;
- fonctions ;
- équipes ;
- infrastructures ;
- équipements ;
- données ;
- laboratoires ;
- compétences déclarées ;
- voies d'accès ou de mobilisation connues.

Une capacité inférée reste explicitement distincte d'une capacité documentée.

### Coordonnées et accès

- adresse ;
- téléphone ;
- courriel ;
- site ;
- formulaire ;
- implantation ;
- périmètre territorial ;
- canal de contact spécialisé lorsqu'il existe.

### Fondement juridique

- texte de création ;
- articles applicables ;
- textes de modification ;
- date d'entrée en vigueur ;
- date de fin lorsque l'entité est supprimée.

### Ressources

Lorsque disponibles :

- programme budgétaire ;
- crédits ;
- plafond d'emplois ;
- effectifs ;
- statut d'opérateur ;
- participations publiques.

Les millésimes budgétaires restent séparés.

## Relations

Le référentiel est un graphe institutionnel.

Les principales relations sont :

```text
DÉPEND_DE
TUTELLE_DE
FINANCE
CONTRÔLE
NOMME
DIRIGE
OPÈRE
PARTICIPE_À
CO_TUTELLE
COMPÉTENT_SUR
IMPLANTÉ_DANS
SUCCÈDE_À
FUSIONNE_AVEC
TRANSFÈRE_COMPÉTENCE_À
COOPÈRE_AVEC
DÉTIENT_CAPACITÉ
MOBILISABLE_PAR
```

Chaque relation contient une source, une date d'observation et, lorsque cela a un sens, une période de validité.

## Dimension temporelle

Le référentiel doit répondre à deux questions différentes :

1. **qu'est-ce qui était vrai à une date donnée ?**
2. **à quelle date FRONTIÈRE a-t-il appris ou vérifié cette information ?**

Chaque assertion importante dispose donc de deux temporalités :

- `valide_depuis` et `valide_jusqua` ;
- `observe_le`.

Cette séparation permet de reconstruire l'état institutionnel historique sans confondre la date d'un changement et la date de sa découverte.

## Événements surveillés

La surveillance transforme les différences entre deux observations en événements.

Types prioritaires :

- création ;
- suppression ;
- fusion ;
- scission ;
- changement de nom ;
- changement de rattachement ;
- transfert de compétence ;
- nomination ou départ d'un responsable ;
- ouverture ou fermeture d'une implantation ;
- modification de coordonnées ;
- entrée ou sortie du périmètre des opérateurs de l'État ;
- changement de programme budgétaire ;
- création ou suppression d'une structure de recherche ;
- changement de tutelle ;
- changement substantiel de mission.

Un changement détecté automatiquement reste marqué `À_VALIDER` tant que sa portée sémantique n'a pas été confirmée lorsque la différence est ambiguë.

## Résolution d'identité

Le même organisme peut apparaître sous plusieurs noms et identifiants.

La résolution suit une hiérarchie :

1. identifiant officiel stable partagé ;
2. SIREN ou SIRET ;
3. identifiant sectoriel ;
4. correspondance explicite dans une source officielle ;
5. rapprochement par nom, adresse et tutelle ;
6. validation humaine pour tout rapprochement ambigu.

Aucune fusion d'entités ne doit reposer uniquement sur une similarité textuelle.

## Provenance

Chaque assertion canonique doit pouvoir être remontée jusqu'à sa source.

Le minimum comprend :

- source ;
- adresse de la ressource ;
- date de publication ou de mise à jour lorsque disponible ;
- date de collecte ;
- identifiant de l'objet dans la source ;
- empreinte du contenu source ou de la ressource lorsque possible ;
- méthode d'extraction ;
- degré de confiance.

La provenance est une propriété de l'assertion, pas seulement de l'entité.

## Architecture des données

Le répertoire `institutionnel/` est organisé ainsi :

```text
institutionnel/
  README.md
  sources_v1.json
  schema_entite_v1.json
  schema_relation_v1.json
  couverture_cible_v1.json
  etat_sources.json
  alertes_sources.json
  entites/
  relations/
  evenements/
  instantanes/
```

Les gros fichiers bruts des producteurs publics ne sont pas recopiés quotidiennement dans Git. FRONTIÈRE conserve leur adresse, leur empreinte, leur date et la représentation canonique nécessaire au graphe. Les instantanés volumineux sont partitionnés. Les graphes massifs servant principalement à des requêtes ponctuelles, comme la compétence géographique DILA, peuvent rester interrogés directement auprès de la source officielle lorsque leur matérialisation intégrale dégraderait fortement la tenue du dépôt.

## Cadence de surveillance

### Quotidienne

- organisation administrative de l'État ;
- annuaire local ;
- Journal officiel ;
- composition du Gouvernement ;
- FINESS ;
- état des sources critiques.

### Hebdomadaire

- structures de recherche ;
- établissements d'enseignement supérieur ;
- changements de responsables et de coordonnées non couverts par un flux quotidien.

### Mensuelle

- rapprochement d'identifiants ;
- contrôle des doublons ;
- couverture des familles institutionnelles ;
- revue des entités sans source fraîche ;
- revue des relations ambiguës.

### Annuelle ou à publication

- Code officiel géographique ;
- opérateurs de l'État ;
- données budgétaires ;
- périmètre des participations publiques.

## Surveillance automatisée

Le programme `scripts/surveiller_sources_institutionnelles.py` vérifie la fraîcheur des sources enregistrées et produit :

- `institutionnel/etat_sources.json` ;
- `institutionnel/alertes_sources.json`.

Une action GitHub quotidienne exécute cette surveillance. Une modification du millésime, de la date de mise à jour, d'une ressource ou de son empreinte apparaît alors dans l'historique du dépôt.

La surveillance des sources est complétée par des ingestions canoniques du ROAE et de l'Annuaire local. Les deux ingestions sont reproductibles et versionnées. Une empreinte sémantique distingue un changement réel du contenu institutionnel d'une simple variation d'ordre dans un export.

## Mesure de couverture

La qualité du référentiel ne doit jamais être résumée par le nombre brut d'entités.

Le tableau de couverture doit publier au minimum :

- couverture par famille institutionnelle ;
- couverture par source ;
- fraîcheur ;
- proportion d'entités avec identifiant stable ;
- proportion avec parent institutionnel résolu ;
- proportion avec territoire résolu ;
- proportion avec mission sourcée ;
- proportion avec responsable sourcé ;
- proportion avec texte juridique ;
- proportion avec information budgétaire lorsque pertinente ;
- proportion avec capacité scientifique ou technique qualifiée ;
- nombre d'ambiguïtés non résolues.

## Lien avec FRONTIÈRE

Le référentiel transforme profondément la recherche publique.

Lorsqu'un besoin est enregistré, FRONTIÈRE doit interroger d'abord ce graphe pour identifier :

1. les institutions juridiquement ou opérationnellement compétentes ;
2. les ressources publiques déjà existantes ;
3. les laboratoires, équipes et opérateurs pertinents ;
4. les voies de saisine, mobilité ou coopération ;
5. les responsables ou services à contacter ;
6. les changements récents susceptibles d'invalider une ancienne réponse.

Le résultat recherché n'est plus une simple liste d'organismes. Il s'agit d'une carte des capacités publiques et des chemins institutionnels qui permettent de les mobiliser.

## Critère de réussite de la version 1

La version 1 est atteinte si :

- les sources de référence critiques sont enregistrées et surveillées ;
- le schéma canonique est stable ;
- la couverture est mesurée ;
- l'organisation centrale de l'État est ingérée ;
- les collectivités et intercommunalités sont ingérées ;
- les opérateurs et autorités indépendantes sont identifiés ;
- les structures publiques de recherche sont reliées à leurs tutelles ;
- les changements de source produisent une alerte traçable ;
- aucun élément canonique important n'est dépourvu de provenance.

La version suivante portera sur l'enrichissement des capacités et des voies de mobilisation.
