# Inventaire des producteurs et des canaux de publication

## Objet

Un premier inventaire des organismes et de leurs moyens de publication doit partir de ce qui a réellement été rencontré, et conserver explicitement les zones non couvertes. Ce programme rapproche deux sources que FRONTIÈRE collecte déjà :

1. les pages locales du catalogue national `institutionnel/decouverte/balayage_pages/page_*.jsonl`, identifiants de jeux de données et libellés des producteurs publiés ;
2. les neuf flux RSS et Bluesky répertoriés dans `institutionnel/flux_publics/sources_v1.json`, reliés explicitement à trois institutions par `institutionnel/canaux_publics/configuration_v1.json`.

Les correspondances de producteurs data.gouv.fr sont faites **sur des libellés configurés**, pas sur des suppositions d'identité. Deux noms différents demeurent séparés, y compris s'ils semblent parler du même ministère. Aucun rapprochement avec les identifiants d'entreprises ni ceux du référentiel administratif de l'État n'est revendiqué.

## Statistiques produites

L'inventaire calcule les pages réellement présentes, les lacunes dans leur numérotation, les lignes lues, les identifiants de jeux distincts, les répétitions entre pages et les éditeurs distincts d'après leur **libellé publié**. Il détaille les 600 éditeurs les plus représentés dans la portion du catalogue disponible et conserve aussi les éditeurs correspondant aux trois organismes de référence, même si leur classement est inférieur.

Pour chaque libellé : nombre de jeux distincts observés, quelques titres de jeux, date d'actualisation déclarée la plus récente. Pour les trois organismes de référence : liens vers les pages officielles documentant les neuf canaux RSS et Bluesky.

**Absence de canal dans l'inventaire = aucune association enregistrée**, jamais preuve que cet organisme ne dispose d'aucun site, compte social, lettre d'information ou portail.

Le catalogue national est parcouru de manière progressive. Même un lot de pages numérotées de 1 à 1 000 ne constitue pas nécessairement une photographie cohérente : les jeux et leur pagination changent entre relevés. L'inventaire déclare donc explicitement `pages_homogenes_temporellement_verifiees=false` et `couverture_exhaustive_du_catalogue_attestee=false`.

## Exécution

```bash
python -m pytest -q tests/test_inventorier_canaux_publics.py
python scripts/inventorier_canaux_publics.py
```

Résultat : `institutionnel/canaux_publics/inventaire_v1.json`.

La procédure `.github/workflows/inventaire-canaux.yml` l'actualise quatre fois par jour, à partir des pages **déjà archivées** du catalogue. Elle ne télécharge aucun nouveau site externe et conserve les exigences de validation avant fusion des fichiers de sortie. Les pages manquantes doivent continuer à être prises en charge par le dispositif de balayage national existant.

## Travaux nécessaires pour la vraie couverture des organismes

Le présent inventaire constitue un point de départ mesuré, pas encore un répertoire exhaustif des administrations. Les prochaines étapes sont :

- rapprochement progressif des producteurs avec les identifiants du référentiel d'organisation administrative de l'État, de l'Annuaire et des répertoires d'entreprises, en gardant les ambiguïtés ;
- recherche des sites officiels propres à chaque organisme et analyse de leurs en-têtes RSS/Atom, cartes de site et pages de publications ;
- collecte des appels à projets, consultations, rapports, annonces de mission et autres signaux pertinents ;
- ajout des comptes sociaux uniquement par références institutionnelles explicites ou vérification d'identité technique ;
- mesure des délais entre publication, première détection et première qualification d'un besoin, avec des alertes de sources indisponibles.

Des dizaines de milliers de fiches publiées ne correspondent pas nécessairement à autant de producteurs ou à autant de missions. Le nombre de canaux vérifiés est distinct du nombre de pages inventoriées.
