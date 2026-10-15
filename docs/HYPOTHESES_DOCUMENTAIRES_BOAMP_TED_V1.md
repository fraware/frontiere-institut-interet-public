# FRONTIÈRE — Hypothèses documentaires entre BOAMP et TED

FRONTIÈRE réunit désormais dans une recherche nationale les avis BOAMP,
les publications TED, les attributions DECP et les offres d'emploi public.
Le rapprochement entre deux avis peut aider à retrouver plusieurs
publications relatives à une même consultation, mais les informations
normalisées actuellement disponibles ne démontrent pas à elles seules
l'identité juridique de leurs procédures.

Cette première contribution crée des **hypothèses traçables de similitude
BOAMP–TED**, à examiner ensuite sur les documents originaux.

## Consultation

La route privée utilise le contrôle d'accès déjà en place :

    GET /hypotheses/boamp-ted?q=équipements&limite=20

Les réponses comprennent les identifiants et liens officiels BOAMP/TED,
les titres, les dates et les empreintes des versions courantes.
Chaque résultat est explicitement qualifié d'hypothèse documentaire,
avec \`meme_procedure_etablie=false\` et
\`identite_institutionnelle_etablie=false\`.

## Critères observables

Une suggestion n'apparaît que si :

- les libellés d'acheteur sont identiques après normalisation des accents,
  caractères et espaces ;
- au moins trois termes de titre discriminants sont partagés, hors mots
  génériques fréquents ;
- le coefficient de Jaccard des termes retenus atteint au moins 0,65 ;
- les dates de publication déclarées diffèrent de 60 jours au maximum.

Le résultat expose les termes communs, le coefficient calculé et l'écart
entre dates. **Ce coefficient est une mesure textuelle et jamais une
probabilité d'identité contractuelle.**

Les corpus sont explorés séparément avant le rapprochement, afin que les
avis d'une source abondante ne masquent pas les publications de l'autre.
La consultation est bornée à cent résultats par source et au plus
cinquante hypothèses affichées. Cette limite implique une couverture
de candidats partielle pour les recherches très larges.

Les documents doivent être comparés dans leur version officielle avant
toute attribution d'une relation établie. Les cas sans acheteur nommé ou
sans date de publication exploitable sont exclus par prudence.

## Pourquoi DECP reste distinct

L'index DECP actuel possède l'identifiant SIRET de l'acheteur et celui
du marché attribué. La projection BOAMP consultée contient principalement
le nom de l'acheteur, le titre, l'identifiant de l'avis et sa date ;
elle ne conserve pas un identifiant de procédure commun démontré.
Faire correspondre les contrats DECP sur la seule ressemblance des titres
produirait des associations incertaines.

La contribution ne fabrique donc aucun lien DECP. La suite devra
collecter les identifiants légaux des acheteurs depuis les données
officielles et conserver les preuves d'identité et de filiation des
procédures par source, version et date.

## Limites empiriques

Une égalité de nom ne prouve pas l'identité institutionnelle ; deux
organismes peuvent posséder des noms semblables. Un titre similaire
n'établit ni un appel d'offres commun ni une attribution. Les résultats
sont des priorités de vérification documentaire, non des observations
juridiques ou des besoins publics confirmés.

Aucun traitement de données personnelles supplémentaires n'est ajouté.
L'outil travaille sur les métadonnées publiques déjà stockées en lecture
seule. Le service doit être alimenté sur un hébergement réel avant
d'évaluer le nombre et la précision des hypothèses nationales.
