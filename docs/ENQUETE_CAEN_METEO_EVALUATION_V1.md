# Enquête comparative — Caen, Météo-France et échantillon indépendant

## Caen — première consultation et résultat négatif du lot 2

L'index officiel BOAMP (277 171 avis, 776 journées ; empreinte de l'index 2186a03b277182ef0bfd0788502f60590399d2463a28e0a9eb295a03b75216db) contient l'avis initial `25-67330` paru le **18 juin 2025**, sous le titre « Caractérisation de l'hydrodynamique de surface du raz Blanchard par télédétection radar ». L'avis d'attribution `26-30147` paraît le **25 mars 2026**. L'index couvre des journées documentées, sans attestation d'exhaustivité historique.

Une annonce secondaire indique une mise en ligne le **20 juin 2025** et une date limite de réponse au **18 juillet 2025**. Les deux dates du 18 et du 20 juin concernent des sources et des notions différentes ; la capture intégrale de l'avis primaire est nécessaire avant de fixer le calendrier contractuel définitif.

Source primaire de départ : https://www.boamp.fr/pages/avis/?q=idweb:25-67330

Annonce secondaire : https://www.marchesonline.com/appels-offres/avis/caracterisation-de-l-hydrodynamique-de-surface-du-raz/ao-9431380-1

Référence interne d'attribution `2025013AOPS038`, numéro de procédure publié `e4e7736a-46b6-49a0-b1ad-70318afc70eb`.

| Élément | Lot 1 | Lot 2 |
| --- | --- | --- |
| Objet | Données radar bande X | Traitement du signal et algorithmique radar HF |
| Durée prévue selon l'avis d'attribution | 5 ans | 5 ans |
| Résultat | Attribué à ACTIMAR | Aucun titulaire |
| Soumissions électroniques déclarées | 1 | 0 |
| Motif explicite de non-attribution | — | `no-rece`, absence d'offres |
| Date de conclusion publiée | 7 octobre 2025 | Aucune |
| Valeur maximale publiée | Accord-cadre attribué : 600 000 € | Propre au lot 2 : **inconnue** |

L'avis d'attribution décrit des critères de compétences et références, ressources humaines et techniques, méthodologie, planning détaillé, coûts, responsabilité sociale et environnementale, et facilité de mise en œuvre. Il ne révèle ni un cahier des charges complet, ni la pondération précise, ni une preuve de contrainte de recrutement.

Dans l'index vérifié, la recherche exacte du terme « Blanchard » retrouve ces deux avis de Caen et deux avis de travaux concernant une rue homonyme à Saint-Barthélemy. **Aucune relance portant ce terme n'a été retrouvée dans ce périmètre indexé**, ce qui n'exclut pas une procédure renommée ou absente des journées couvertes.

Le nouveau collecteur `scripts/etudier_consultation_caen.py` capture l'avis initial via la source officielle DILA, contrôle sa date, l'identité de l'acheteur et les références du marché, puis extrait les champs publiés pour chaque lot sans fabriquer de budget ou de calendrier. Toute divergence entre identifiants européens de procédure est enregistrée distinctement.

Hypothèses concurrentes à départager : spécialisation technique, budget et partage des risques, durée et calendrier, découpage des lots, disponibilité de l'offre et modalités de participation. Aucune n'est démontrée par un lot sans offre à lui seul.

## Météo-France — distinguer contrat récent et parc antérieur

Le marché interne `METEO-FRANCE2432F0342` a été publié en 2024, avec clôture annoncée au 28 novembre 2024 sur la plateforme PLACE. L'attribution officielle `26-74896` déclare BULL SAS retenu le **20 juillet 2026**, un contrat conclu le **22 juillet 2026**, une publication au **28 juillet 2026** et une valeur contractuelle de **217 millions d'euros hors taxes**.

Source : https://www.marches-publics.gouv.fr/index.php?id=2636711&orgAcronyme=d4t&page=Entreprise.EntrepriseDemandeTelechargementDce

Résultat officiel : https://op.europa.eu/da/web/public-procurement/procurement-details/-/procurement/8268f394-ed72-4ca8-b65f-74a5914549f5

Les articles institutionnels sur Belenos et Taranis attestent que ces machines **sont opérationnelles depuis 2021** ; une page de presse de mars 2026 les mentionne également. Elles ne constituent pas une attestation de livraison du système attribué en juillet 2026.

Sources : https://meteofrance.com/meteo-a-z/les-supercalculateurs-de-meteo-france et https://meteofrance.com/presse/meteo-france-deploie-ses-deux-nouveaux-supercalculateurs

**Calendrier public de déploiement du nouveau parc.** Météo-France annonçait en janvier 2025 un premier déploiement en 2027, un renforcement de la puissance en 2029 et un contrat jusqu'en 2033. Le projet annuel de performances pour 2026 indique un report d'un an de la mise en service, alors envisagée **à partir de mi-2027**. Le Sénat distingue le coût global du programme, estimé à **415 millions d'euros sur 2025–2033**, du montant du marché attribué en juillet 2026, **217 millions d'euros**. Il s'agit de prévisions et de périmètres comptables distincts, jamais de preuves d'achèvement.

Sources : https://meteofrance.fr/actualite/presse/meteo-france-renouvelle-ses-supercalculateurs ; https://www.budget.gouv.fr/documentation/file-download/30943 ; https://www.senat.fr/rap/l25-139-310-3/l25-139-310-32.html

Données non obtenues pour le marché 2026 : livraison initiale, installation, réception, mise en production, première simulation ou prévision effectivement produite par la nouvelle machine. Aucune de ces dates ne peut être inférée de l'attribution ou de la mise en service d'équipements antérieurs.

## Évaluation indépendante — séparation du tirage et des résultats

Le corpus historique réservé H01–H10 dispose déjà d'une procédure de comparaison de trois méthodes, sans évaluation indépendante effectuée à ce jour. Le nouvel échantillon BOAMP porte sur la **classification des résultats de consultation** et les erreurs de diagnostic de besoins spécialisés.

Le programme `scripts/tirer_jeu_independant_boamp.py` prépare 36 cas indépendants des dix notices de développement (six mois fixés, six avis techniques par mois, semence fixe, contrôle SHA-256 de l'index, dédoublonnage acheteur–objet). Le tirage ne consulte aucun résultat d'attribution. Les étiquettes de référence devront être établies ensuite, à partir de réponses officielles intégrales et **par lot**, en distinguant « attribué », « sans offre » et « indéterminé ».

La comparaison prévue mesure séparément l'exactitude par classe, les abstentions, les faux diagnostics de pénurie, la provenance des sources, le temps de traitement et l'effort humain. Le fait de publier un échantillon reproductible ne constitue pas une évaluation indépendante réalisée. La couverture technique lexicale est intentionnelle et non représentative de toute la France.

**Critère de poursuite :** obtenir le formulaire primaire initial de Caen, identifier toute trace de relance, trouver une preuve contractuellement reliée de livraison Météo-France et faire établir des étiquettes indépendantes du modèle sur les nouveaux cas. Les cas sans preuve restent indéterminés.
