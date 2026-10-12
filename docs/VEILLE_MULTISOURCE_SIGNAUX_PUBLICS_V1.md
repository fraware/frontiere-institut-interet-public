# Veille multisource des signaux publics — première extension (12 octobre 2026)

## Objet

FRONTIÈRE dispose déjà d'un relevé BOAMP, d'une extraction des offres de la fonction publique, d'un rattrapage historique et de collecteurs de métadonnées nationales. Ce nouveau circuit couvre les **flux de publication institutionnels** qui n'appartiennent pas à ces jeux structurés : appels à projets, actualités administratives et messages des comptes sociaux officiels. Ces sources sont complémentaires, non interchangeables.

**Une publication observée n'est pas un besoin public établi.** Le champ `nature_signal=publication_publique_non_qualifiee` interdit de confondre la présence d'une annonce avec une demande effectivement financée, une mission nouvelle ou une difficulté de mobilisation. Aucune extrapolation nationale ne découle de ce relevé.

## Trois sources primaires initiales

| Identifiant | Producteur | Canal | Origine officielle et portée |
| --- | --- | --- | --- |
| `anr_appels` | Agence nationale de la recherche | RSS des appels à projets | [Page officielle des trois flux](https://anr.fr/fr/flux-rss-et-reseaux-sociaux/) ; [filtre des appels à projets](https://anr.fr/rss/?aap=) |
| `service_public_pro` | DILA / Service Public | RSS des actualités professionnelles | [Documentation du fil](https://entreprendre.service-public.gouv.fr/P10008) ; [flux RSS](https://www.service-public.gouv.fr/abonnements/rss/actu-actu-pro.rss) |
| `anr_bluesky` | Agence nationale de la recherche | Compte officiel Bluesky | [Lien fourni par l'ANR](https://anr.fr/fr/flux-rss-et-reseaux-sociaux/) ; identifiant technique déclaré `did:plc:poa5nra3tnvjpki64nprt27d`. Le collecteur utilise l'[interface publique Bluesky](https://docs.bsky.app/docs/api/app-bsky-feed-get-author-feed) sans authentification. |

Le lien social est identifié par son identifiant décentralisé, en plus du nom de compte, pour écarter les messages publiés par des tiers et les repartages.

L'ANR diffuse publiquement trois flux RSS, dont un consacré aux appels à projets ; sa présence dans le catalogue ne signifie pas que chaque appel concerne un besoin administratif. Les actualités générales sont conservées comme signaux contextuels.

## Méthode de collecte

- Registre explicite dans `institutionnel/flux_publics/sources_v1.json`, avec producteur, type, identité, domaine autorisé, cadence et page de provenance.
- Requête réseau limitée à une liste fermée de domaines, sans redirection et sans téléchargement des liens contenus dans les messages.
- Lecture bornée à deux mégaoctets par source et cent entrées par relevé ; aucune collecte exhaustive des messages historiques ni des réseaux sociaux.
- RSS 2.0, Atom et interface publique Bluesky pris en charge ; titres, extraits courts, dates déclarées et liens conservés sans coordonnées privées.
- Déduplication entre relevés par identifiant de source et identifiant natif de publication ; empreinte des champs normalisés pour détecter une modification du contenu publié.
- Conservation de la première observation ; comptage des révisions constatées, sans prétendre obtenir l'historique complet des éditions intermédiaires.
- Une source indisponible conserve les observations antérieures, inscrit son erreur au bilan et ne devient pas un signal d'absence de besoins.
- Le catalogue annonce expressément `couverture_exhaustive_des_besoins_publics=false` et `qualification_de_besoins_effectuee=false`.

Le plafond courant est **25 000 publications distinctes** dans le fichier de travail du dépôt. En cas de saturation, le programme refuse de supprimer arbitrairement les anciennes observations. Le passage à une base de données persistante et à un stockage documentaire externe constituera alors une évolution explicite.

## Exécution locale

```bash
python -m pytest -q tests/test_collecter_flux_publics.py
python scripts/collecter_flux_publics.py
```

Sorties :

- `institutionnel/flux_publics/observations.json` — index des publications observées ;
- `institutionnel/flux_publics/etat_collecte.json` — nombre de sources réussies, échecs, nouveaux éléments, modifications, date de consultation.

## Exécution automatique

Le fichier `.github/workflows/veille-flux-publics.yml` prévoit quatre déclenchements quotidiens, à **02:41, 08:41, 14:41 et 20:41 UTC**, ainsi qu'un déclenchement lors de la modification du programme. GitHub Actions exécute les planifications de manière opportuniste : ces heures ne constituent pas un engagement de ponctualité.

Le programme produit une proposition de modification limitée aux deux sorties. Sa publication ne passe dans la branche principale qu'une fois les trois contrôles **Python 3.11, Python 3.12 et conteneur** réussis sur le commit exact et les chemins vérifiés. Les échecs du réseau sont diagnostiqués et ne remplacent pas les états précédents.

**Ce qui reste à construire pour la couverture nationale** : ajout progressif de centaines de flux et de catalogues validés ; alimentation depuis les plateformes territoriales, opérateurs et publications ministérielles ; rapprochement des identités d'organismes avec le référentiel administratif ; stockage externe des archives volumineuses ; mesure de fraîcheur, de retard et de couverture par institution ; qualification empirique des signaux selon le besoin exprimé, son échéance, son budget et sa nature. Les interfaces sociales non publiques ou limitées par accès ne sont pas présumées disponibles.

## Frontières d'interprétation

Les flux RSS et les réseaux sociaux peuvent omettre des publications anciennes, changer de format ou être temporairement indisponibles. Un délai de six heures entre interrogations ne constitue pas une surveillance en temps réel et ne garantit pas qu'un message supprimé entre deux passages soit enregistré.

Les marchés BOAMP, les offres CSP et ces nouveaux signaux ne peuvent pas être additionnés comme s'il s'agissait d'autant de besoins indépendants. Un même programme peut apparaître sur plusieurs canaux ; une future étape de rapprochement doit conserver séparément ses publications tout en les reliant à une même mission documentée.
