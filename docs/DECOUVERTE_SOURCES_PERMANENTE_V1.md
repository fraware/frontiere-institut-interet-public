# Découverte récurrente des sources publiques — première réalisation

## Finalité

FRONTIÈRE entretient deux ensembles complémentaires :

- le registre institutionnel déjà suivi dans `institutionnel/sources_v1.json`, associé aux collectes de l'administration, des territoires et de la recherche ;
- le catalogue de notices découvertes par interrogation régulière de sources publiques, enregistré dans `institutionnel/decouverte/candidats_data_gouv.json`.

Les métadonnées servent à repérer de nouveaux jeux, leur producteur, leur licence déclarée, leurs ressources et leurs dates de modification. **La découverte d'un jeu n'établit ni sa pertinence opérationnelle, ni son exactitude, ni la permission de recopier intégralement les données sous-jacentes.**

## Première source interrogée

La première collecte automatisée utilise l'[interface officielle du catalogue data.gouv.fr](https://guides.data.gouv.fr/api-de-data.gouv.fr/reference/datasets).

Le fichier `institutionnel/decouverte/recherches_v1.json` énumère **38 recherches thématiques** touchant notamment les institutions, la recherche, les marchés publics, les compétences, les laboratoires, les métiers, le financement et les territoires. Trois pages supplémentaires présentent les ressources récemment actualisées, indépendamment d'un sujet particulier. Les interrogations sans deuxième page disponible sont désormais écartées, afin de ne pas assimiler une fin de liste à une panne. La recherche des dernières actualisations utilise des réponses plus petites pour éviter des transferts excessifs.

Pour chaque résultat, sont conservés : identifiant stable, titre, organisme producteur, licence déclarée, date de modification, date d'actualisation des ressources, fréquence déclarée et liens vers un nombre limité de fichiers. Le programme déduplique les identifiants et conserve les notices déjà enregistrées lors d'une indisponibilité partielle de l'interface.

La recherche est **bornée**, par expression et par nombre de pages. Son résultat ne constitue pas un inventaire exhaustif des données de data.gouv.fr, de toutes les administrations ni de tous les sites Internet. Le [catalogue complet fourni par data.gouv.fr](https://www.data.gouv.fr/datasets/catalogue-des-donnees-de-data-gouv-fr) est également inscrit dans le registre. Ses exports de plusieurs centaines de mégaoctets à un gigaoctet sont traités séparément des notices légères.

Le premier [essai automatisé](https://github.com/fraware/frontiere-institut-interet-public/pull/130) a conservé 500 notices distinctes. Il a réussi 46 des 79 demandes initiales et consigné 33 anomalies, essentiellement sur des secondes pages non disponibles. La présente révision utilise le nombre de résultats annoncé et le lien de page suivante afin d'éviter les interrogations sans suite ; le rapport suivant devra confirmer la diminution réelle de ces échecs.

## Balayage général indépendant des mots-clés

Le programme `scripts/balayer_catalogue_national.py` ajoute une deuxième méthode de découverte : parcourir **toutes les pages du catalogue national**, y compris celles dont le titre ne correspond à aucune recherche thématique.

Le curseur figure dans `institutionnel/decouverte/balayage_etat.json`, et chaque page traitée est conservée séparément sous `institutionnel/decouverte/balayage_pages/page_XXXXX.jsonl`. Un cycle traite jusqu'à **60 pages de 50 notices**, soit 3 000 notices reçues au maximum par exécution, puis repart de la page suivante lors du prochain passage. À la fin du catalogue, il reprend au début pour actualiser les pages.

Les fichiers conservent seulement les identifiants officiels, titres, producteurs, licences, dates de mise à jour, liens de notices et nombres de ressources. Les descriptions libres et fichiers bruts ne sont pas copiés dans cet inventaire général. Les pages historiques sont conservées en cas d'échec réseau ; le curseur ne franchit jamais une page inaccessible. Un tour complet de pages n'est pas une preuve de présence de chaque jeu publié, car le catalogue évolue au cours du balayage.

Les tableaux des recherches thématiques et du balayage général sont complémentaires. Le premier privilégie les sources utiles au projet ; le second cherche l'étendue et rend les omissions plus faciles à détecter. Le volume final se mesure par les fichiers effectivement présents et non par une promesse d'exhaustivité.

## Actualisation permanente

La procédure `.github/workflows/decouverte-sources.yml` est programmée **toutes les six heures**, à 1 h 11, 7 h 11, 13 h 11 et 19 h 11 UTC, et est également exécutable à la demande. Les collectes DILA, territoriales, universitaires et de surveillance déjà présentes conservent leurs propres programmations.

Le nouveau processus :

1. vérifie le programme à l'aide de cas entièrement fictifs ;
2. interroge exclusivement l'interface publique autorisée, avec une limite de volume par réponse et une temporisation entre demandes, puis avance dans le balayage général ;
3. conserve cumulativement les notices, leur provenance et les anomalies de téléchargement ;
4. ouvre une proposition technique limitée aux notices, aux états de suivi et aux pages du balayage général ;
5. déclenche explicitement les vérifications Python 3.11, Python 3.12 et conteneur sur l'empreinte exacte de cette branche ;
6. **fusionne automatiquement uniquement ces fichiers de métadonnées strictement autorisés**, uniquement après réussite des trois contrôles et vérification des chemins et de l'empreinte ;
7. en cas d'échec, garde la proposition ouverte, conserve les données antérieures et signale l'incident dans les journaux.

Cela organise l'actualisation continue du catalogue **dans GitHub**, dans la limite de la disponibilité de GitHub Actions et de l'interface source. Aucune garantie d'instantanéité n'est avancée. La branche principale n'est jamais écrite directement par cette procédure.

## Accès depuis le site

L'application comporte la page `/sources-publiques` et l'interface de lecture `/api/v1/sources-publiques`. Elles affichent les données versionnées dans le déploiement courant, avec la date de la dernière collecte et le nombre de pages échouées. Le catalogue est consultable par titre ou par producteur et se présente en pages.

**Condition opérationnelle distincte :** un déploiement de l'application doit être reconstruit depuis la version récente de GitHub pour présenter les nouveaux résultats. Cette contribution ne met pas à elle seule en place un hébergement ou un déploiement permanent.

## Droits et qualité des informations

Les [conditions de la Licence Ouverte 2.0](https://www.data.gouv.fr/pages/legal/licences/etalab-2.0) autorisent une large réutilisation avec attribution et respect de la protection des données personnelles. L'absence de mention de licence, une restriction propre à l'interface ou la présence de données personnelles empêchent de présumer qu'un fichier brut est librement redistribuable.

Cette première collecte conserve les **métadonnées et les URL**, sans télécharger automatiquement les fichiers bruts. Le champ `reutilisation_potentielle` ne constitue qu'un indice fondé sur la licence déclarée. Une copie de contenu nécessitera un contrôle distinct de la licence, des conditions techniques d'accès, de la pertinence et de l'absence d'informations sensibles.

Les notices ne prouvent ni l'existence actuelle d'une compétence, ni sa disponibilité pour une mission, ni la réalité d'un besoin institutionnel. La recherche de ressources et leur mobilisation demeurent des questions distinctes.

## Collecte indépendante du catalogue de la recherche

Le programme `scripts/decouvrir_catalogue_scientifique.py` interroge directement l'[interface de données du ministère chargé de la recherche](https://data.enseignementsup-recherche.gouv.fr/api-console/explore/v2.1/). Les notices du catalogue sont distinctes de celles enregistrées dans data.gouv.fr, ce qui permet de détecter des ensembles absents ou moins récents dans l'agrégateur général.

Les résultats sont conservés sous `institutionnel/decouverte/catalogue_mesr.json`, avec le dernier état et les erreurs dans `institutionnel/decouverte/catalogue_mesr_etat.json`. Un identifiant de jeu, un titre, la licence déclarée, une date de modification disponible et un lien de provenance sont retenus. **Aucune donnée d'enregistrement, pièce jointe, fichier personnel ou archive complète n'est copiée.**

La collecte est déclenchée dans le même cycle de six heures que l'inventaire national. Elle est indépendante : une erreur sur ce portail déclenche une alerte d'exécution et conserve les données antérieures, sans empêcher la publication des autres catalogues. La première collecte sur ce portail reste à observer ; une source inscrite dans le code ne représente pas une interrogation réussie.

Le site expose les notices du ministère dans `/sources-recherche` et `/api/v1/catalogue-recherche`, séparément du catalogue national.

## Diversification des catalogues

Le registre `institutionnel/decouverte/catalogues_officiels_v1.json` recense des portails complémentaires : annuaire de l'administration, Bulletin officiel des annonces des marchés publics, publication européenne des marchés, recherche d'entreprises, données scientifiques, Répertoire national des structures de recherche et textes juridiques. Il distingue précisément les sources déjà ingérées, le catalogue nouvellement interrogé et les sources **encore à intégrer**.

Les prochains travaux porteront sur la lecture du catalogue complet, la découverte d'interfaces nouvelles par analyse des ressources et le téléchargement contrôlé de fichiers effectivement autorisés, avec déduplication et conservation des changements.

## Vérification locale

```bash
python -m pytest -q tests/test_decouverte_sources_publiques.py tests/test_catalogue_public_api.py
python scripts/decouvrir_sources_publiques.py
```

La seconde commande interroge le service externe et réécrit seulement les deux fichiers de résultats, sans fusion distante. Le contrôle est réalisé dans une instance de test ; les réponses sont conservées avec leur date et leurs erreurs éventuelles.
