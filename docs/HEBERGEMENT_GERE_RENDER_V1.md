# FRONTIÈRE — Publication gratuite, sans serveur permanent

## Décision budgétaire

Le financement d'un service Render à **37,50 dollars par mois** n'est pas
autorisé. Le Blueprint actif (`render.yaml`) est désormais limité à un
**site statique gratuit** dans le projet Render `Frontiere`, environnement
`Production`. Il ne commande ni processeur permanent facturé ni disque.

Le service proposé publie uniquement les fichiers de
`site_frontiere/`. Le contenu constitue une présentation documentaire
de trois corpus prioritaires : BOAMP, emplois publics et DECP.

**Ce site ne collecte pas les données et ne dispose pas de base
persistante.** Les composants de collecte construits précédemment sont
conservés dans GitHub pour étude, reprise ou exécution sur un environnement
réel adapté. Ils ne sont pas lancés par le Blueprint gratuit.

## Pourquoi ne pas déployer l'application actuelle sur Render Free ?

Les services Web gratuits de Render possèdent un stockage local éphémère.
Ils peuvent être mis en veille après quinze minutes d'inactivité ; un
redémarrage ou un nouveau déploiement fait disparaître les fichiers créés,
y compris les bases SQLite. Le calcul gratuit ne résout donc pas le
problème de conservation des archives BOAMP, emplois et DECP.

Une base Postgres gratuite sur Render est limitée en volume et expire
après trente jours. Elle ne constitue pas une solution durable pour ce
projet. Le disque persistant Render est réservé aux offres payantes.

Documentation Render :
- https://render.com/docs/free
- https://render.com/docs/disks
- https://render.com/docs/blueprint-spec

## Déployer le site de présentation

Depuis le projet Render existant :

https://dashboard.render.com/project/prj-db8ddpjrjlhs73e09flg

1. Ouvrir ou recharger le déploiement Blueprint du dépôt
   `fraware/frontiere-institut-interet-public`, branche `main`.
2. Vérifier que le fichier `render.yaml` annonce le type
   `web`, l'exécution `static` et le répertoire
   `./site_frontiere`.
3. Vérifier que le montant présenté est **0 dollar de forfait mensuel**
   et qu'aucun disque ni base de données payants ne figurent dans le
   récapitulatif.
4. Autoriser uniquement le site statique si ces conditions sont réunies.

Les mises en ligne automatiques sont désactivées dans cette première
configuration afin de limiter les usages de construction et les
changements non examinés. Les futures mises à jour du site devront
être publiées explicitement dans Render.

**Attention :** les sites statiques gratuits consomment des allocations
mensuelles de bande passante et de construction. Un dépassement peut
engendrer des frais si un moyen de paiement est enregistré. Contrôler
les limites et les paramètres de facturation du compte, et suspendre
le service si elles sont proches du plafond. Aucun coût strictement
nul ne peut être garanti indépendamment de l'usage.

## Collecte gratuite à reconstruire sans perdre la rigueur

La prochaine architecture cible trois opérations séparées :

1. Des programmes d'acquisition bornés, lancés périodiquement par
   GitHub Actions sur le dépôt public, en conservant les vérifications
   de provenance, de structure et de complétude déjà implémentées.
2. Des résultats documentaires limités, versionnés et datés dans Git,
   avec contrôle de taille. Aucun téléchargement national massif ne
   doit être ajouté directement aux commits sans stratégie de stockage.
3. Une publication statique présentant les observations vérifiées.
   Les corpus volumineux pourront ensuite être distribués en archives
   compressées par lots, avec une politique de taille et de conservation.

Les exécutions GitHub Actions sur des machines standard sont gratuites
pour les dépôts publics, selon les règles GitHub applicables. Les archives
temporaires d'exécution ne sont pas un entrepôt documentaire permanent.
La pérennité de données volumineuses doit être mesurée et résolue
séparément.

https://docs.github.com/en/billing/concepts/product-billing/github-actions

## Principes de validation

- Toujours signaler la date du dernier relevé effectivement importé.
- Ne jamais confondre affichage statique et collecte continue.
- Ne jamais annoncer une couverture nationale exhaustive sans contrôles
  par source et période.
- Préserver une référence d'origine pour chaque donnée publiée.
- Ne créer aucune ressource payante sans accord préalable explicite.
