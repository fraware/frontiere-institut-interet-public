# Collecte BOAMP directe et continue — première infrastructure autonome

**Première tranche exécutable ; aucun déploiement hébergé n'est présumé.**

## Fonctionnement

Un travailleur Python contacte directement l'API officielle BOAMP à
intervalle configurable (30 minutes par défaut), sans créer de modification
dans GitHub. Il réutilise le collecteur existant et ses règles de normalisation
des avis. Un état local garde les annonces récentes nécessaires aux prochains
passages ; les notices et leurs versions historiques sont persistées dans
la base de la plateforme.

Le collecteur interroge une fenêtre glissante de sept jours, en limitant les
avis déjà connus aux huit derniers jours. Les informations plus anciennes
restent dans la base de données, même si elles quittent le fichier glissant.

Un avis est une publication documentaire : aucune détection de besoin public
supplémentaire n'est encore déduite de cette seule collecte.

## Exécution locale

    python -m app.collecteur_boamp_continu \
      --base sqlite:////tmp/frontiere-boamp/avis.db \
      --repertoire /tmp/frontiere-boamp/releves

Pour activer les interrogations régulières :

    python -m app.collecteur_boamp_continu \
      --base sqlite:////tmp/frontiere-boamp/avis.db \
      --repertoire /tmp/frontiere-boamp/releves \
      --suivre --intervalle 1800

L'intervalle minimal admis pour le suivi automatisé est de quinze minutes.
Les résultats correspondent à la disponibilité de l'interface officielle,
et non à des créations de nouvelles annonces garanties à cette fréquence.

## Conteneur persistant

Sur une machine disposant de Docker Compose et d'un accès Internet :

    docker compose -f compose.collecte.yml up --detach --build

Le volume nommé stockage-frontiere-boamp conserve les relevés et la base
SQLite lors des redémarrages du conteneur. Le service redémarre
automatiquement sauf arrêt explicite.

Les archives historiques déjà présentes dans le dépôt sont montées en lecture
seule. Pour les importer dans cette même base, exécuter une fois :

    docker compose -f compose.collecte.yml run --rm collecte-boamp \
      python -m app.plateforme_boamp \
      --base sqlite:////var/lib/frontiere/avis_boamp.sqlite3 \
      importer --repertoire /opt/frontiere/archives

Cette importation peut être relancée sans créer de doublons. Son exécution
peut être longue selon la taille du corpus. Elle exploite les archives
effectivement présentes dans la copie locale du dépôt ; un historique
national complet ne doit pas être présumé.

Consulter les derniers événements :

    docker compose -f compose.collecte.yml logs -f collecte-boamp

La nouvelle image ne lance aucune interface Web. Les recherches dans la
base peuvent être exécutées par une commande du module
app.plateforme_boamp, ou reliées ultérieurement à l'application FastAPI.

Cette configuration fait fonctionner une seule instance SQLite. Un
déploiement distribué et l'usage simultané d'autres collecteurs exigeront
l'adaptation de la topologie de stockage, notamment PostgreSQL.

## Limites de couverture

- La collecte peut être partielle si la pagination dépasse le plafond
  fixé ou si l'interface officielle interrompt une requête.
- La fenêtre récente ne remplace pas le rattrapage quotidien des journées
  historiques ; celui-ci demeure assuré par les programmes existants.
- Des corrections rétroactives concernant des avis anciens peuvent échapper
  à la fenêtre courante ; leur suivi reste un chantier distinct.
- Aucune garantie de disponibilité permanente n'existe tant que le
  conteneur n'est pas réellement hébergé et son exploitation suivie.
- Une nouvelle capture du même contenu ne crée pas de doublon de version.

## Suite

Étendre l'infrastructure aux offres d'emploi public, aux contrats DECP,
puis aux avis TED. Relier ces corpus aux identifiants des acheteurs et
aux organismes du référentiel national. Ajouter ensuite l'extraction
des documents de consultation et le suivi des signaux budgétaires,
parlementaires et territoriaux.
