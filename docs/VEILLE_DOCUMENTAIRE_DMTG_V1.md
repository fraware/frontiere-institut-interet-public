# Veille documentaire DMTG — surveillance de cinq publications officielles

**Mise en place : 14 octobre 2026.** **Statut initial : procédure proposée ; première consultation effective et constitution d'un état de référence à confirmer après intégration.**

## Question de recherche et limites

L'enquête FRONTIÈRE sur les statistiques successorales cherche à déterminer si le renfort du Département des études statistiques et fiscales annoncé pour septembre 2026 a été affecté, si les traitements de déclarations successorales produisent des données vérifiées et si un premier résultat statistique détaillé est publié. La consultation des publications accessibles au 14 octobre n'a pas permis d'établir ces trois événements.

Le [rapport d'information du Sénat n° 760](https://www.senat.fr/rap/r25-760/r25-760_mono.html) rapporte **0,5 ETP consacré au chantier en juin 2026**, un ETP supplémentaire annoncé pour septembre et une cible de première diffusion de microdonnées en 2028. La [réponse ministérielle du 10 mars 2026](https://questions.assemblee-nationale.fr/q17/17-11677QE.htm) décrit des travaux en cours d'enrichissement de la base nationale des données patrimoniales et des essais de télédéclaration notariale. La [fiche DGFiP de février 2026](https://www.pass.fonction-publique.gouv.fr/files/2026-02/Fiche_stage_otim_26%20nouvelle%20version.pdf) décrit un stock annuel à traiter, des travaux engagés et des compétences recherchées ; elle ne confirme ni une embauche ni une production achevée.

## Sources surveillées

Le fichier `institutionnel/programmes_scientifiques/sources_veille_dmtg_v1.json` déclare cinq URL HTTPS officielles et fermées :

1. [DGFiP Statistiques 2026](https://www.impots.gouv.fr/dgfip-statistiques-2026), pour repérer les études et séries nouvelles ;
2. [Recettes fiscales DGFiP](https://www.impots.gouv.fr/recettes-fiscales), pour suivre les tableaux et leurs dates de publication ;
3. [Droits de mutation DGFiP](https://www.impots.gouv.fr/droits-de-mutation), catalogue qui comporte surtout des données relatives aux mutations à titre **onéreux** et dont l'évolution doit rester séparée de celle des microdonnées de successions ;
4. [Réponse parlementaire n° 11677](https://questions.assemblee-nationale.fr/q17/17-11677QE.htm), référence des essais et de l'enrichissement statistique ;
5. [Rapport sénatorial n° 760](https://www.senat.fr/rap/r25-760/r25-760_mono.html), référence des moyens annoncés et des recommandations.

Ce périmètre est **ciblé**, ni exhaustif des publications administratives, ni une mesure de disponibilité nationale des compétences. Il ne comprend aucune donnée fiscale individuelle.

La [page des publications statistiques DGFiP 2026](https://www.impots.gouv.fr/dgfip-statistiques-2026) présente notamment le **n° 49 de septembre 2026**, consacré aux recettes du premier semestre. Ces bulletins existent et sont distincts d'une nouvelle production de microdonnées successorales. Ils ne prouvent pas le rétablissement d'une enquête DMTG 2.0.

## Procédure

`scripts/surveiller_publications_dmtg.py` contrôle les cinq adresses HTTPS, les domaines exacts, les redirections, le type HTML attendu, le délai et un volume maximum de trois millions d'octets par réponse. Le texte principal est transformé en empreinte SHA-256 suivant le traitement déjà utilisé par le dispositif de suivi des programmes scientifiques ANR. Les pages de navigation et les pieds de page sont écartés dans la mesure permise par la structure HTML de la source.

`institutionnel/programmes_scientifiques/etat_veille_dmtg_v1.json` est initialisé avec une liste **vide** : aucune consultation ni signature n'est inventée. Une exécution réelle réussie fournit les premières empreintes. Les états suivants distinguent les documents identiques, les versions modifiées et les accès refusés. Une erreur réseau laisse les signatures précédentes disponibles, sans conclure à une disparition de la publication.

La procédure `.github/workflows/veille-publications-dmtg.yml` est prévue **une fois par jour** et comporte un lancement manuel. Elle teste le programme sans réseau, effectue ensuite le relevé et conserve un rapport JSON et Markdown durant 30 jours. Elle est référencée dans le contrôle transversal des procédures avec une fenêtre de retard de 72 heures.

Lors des déclenchements programmés ou d'un lancement manuel explicitement configuré, seuls les changements du **fichier d'empreintes** sont proposés via `scripts/publier_mise_a_jour_institutionnelle.py --source dmtg --publier`. Le mécanisme doit ouvrir une proposition de fusion, soumise aux vérifications du dépôt. Il n'écrit pas directement dans `main` et ne modifie pas les fiches scientifiques.

## Interprétation scientifique autorisée

Une nouvelle signature sur la page de la DGFiP signale uniquement une **nouvelle version technique**. Elle peut correspondre à une modification de présentation, une actualisation d'une table, une nouvelle étude ou une évolution sans rapport avec DMTG. L'examen documentaire doit vérifier son objet et sa date.

Une déclaration administrative indiquant un agent attendu ne confirme pas son affectation. Une offre de stage ne prouve pas que le poste est pourvu. Une quantité annuelle de PDF à traiter ne constitue pas un volume de documents extraits. Une publication de recettes agrégées ne constitue pas une nouvelle enquête de microdonnées successorales.

La valeur empirique du dossier dépend en priorité de quatre pièces : **affectation effective des personnels au chantier**, **nombre et qualité des documents traités**, **première production statistique détaillée** et **usage administratif vérifiable**. Leur absence dans le corpus recensé correspond à un statut **non établi**, jamais à une valeur nulle.

## Reproduction et surveillance de fonctionnement

Contrats hors réseau :

`python -m pytest -q tests/test_surveiller_publications_dmtg.py tests/test_publication_institutionnelle.py`

Relevé direct sans fusion automatique :

`python -m scripts.surveiller_publications_dmtg --bilan-json /tmp/dmtg-bilan.json --bilan-markdown /tmp/dmtg-bilan.md`

La première exécution réelle sur `main` doit confirmer le type, l'accessibilité et la stabilité des cinq pages. Les réponses inaccessibles ou incompatibles seront consignées. Le suivi actuel ne garantit pas l'exhaustivité des publications ni une notification instantanée des nouvelles pièces.

Dossier de recherche : [DMTG — moyens et échéances](DMTG_SUIVI_MOYENS_EFFECTIFS_ET_ECHEANCES_2026_10_14.md). Suivi d'enquête : [problème n° 442](https://github.com/fraware/frontiere-institut-interet-public/issues/442).
