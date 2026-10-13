# Bilan documenté des sept mois de marchés publics

**Date du traitement : 13 octobre 2026.** Programme [FRONTIÈRE — Institut pour l'intérêt public](https://github.com/fraware/frontiere-institut-interet-public). L'exécution initiale des sept mois est [consultable dans GitHub Actions](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38484330790). Le rapport de cette exécution possède l'empreinte SHA-256 :

`3f97707eaeecce5f2b06bfad2c14e63ecb0caf978762decd891a48f0ca05ccde`

Le bilan pérenne et les sept empreintes primaires figurent dans `institutionnel/decp/bilan_sept_mois_2026_10_13.json`. La procédure d'exécution conserve temporairement les quatre fichiers ajoutés. Les trois précédents sont archivés dans [l'exécution source](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38481650597).

## Périmètre exact

Les ressources consolidées des ministères économiques et financiers ont été lues pour août, octobre et décembre 2025, ainsi que février, mars, avril et mai 2026. Les dates correspondent aux **fichiers mensuels publiés**, sans implication que les contrats BOAMP étudiés aient été attribués ou notifiés pendant ces mêmes mois. Le catalogue et le territoire national sont plus vastes que ces sept fichiers.

| Mesure | Valeur |
|---|---:|
| Objets documentaires lus, concessions comprises | 262 963 |
| Concessions isolées du traitement des marchés | 163 |
| Notices de marchés analysées et normalisées | 262 800 |
| Notices de marchés rejetées | 0 |
| Mentions d'offres reçues non communiquées, codées `NC` | 55 596 |
| Identités uniques entre les sept mois, par SIRET et numéro de marché | **202 081** |
| Variantes documentaires distinctes entre les sept mois | **228 375** |
| Répétitions de variantes strictement identiques | **34 425** |
| Identités apparaissant dans plusieurs mois | **28 819** |
| Identités associées à plusieurs variantes | **7 250** |

Les comptes satisfont l'égalité **262 800 = 228 375 + 34 425**. Une identité documentaire unique désigne le couple `(SIRET acheteur, identifiant de marché publié)`. Des modifications de données sous la même identité produisent plusieurs variantes distinctes, sans établir la nature juridique de la modification.

Le cumul sans dédoublonnage des identités uniques **à l'intérieur de chaque fichier** est de 241 696. Cette somme ne constitue pas un nombre de marchés distincts sur sept mois, car certaines identités figurent dans plusieurs ressources. Le nombre intermensuel contrôlé est **202 081**.

## Examen des sept références contractuelles BOAMP

Les cibles proviennent du rapport de filiation documentaire des 17 avis BOAMP, dont sept contrats présentent une référence compacte exploitable. L'extraction distingue les codes locaux des résultats de lots et les références contractuelles déclarées.

Parmi les 262 800 notices normalisées, **aucune** n'associe une des sept références contractuelles BOAMP au **SIRET du même acheteur** dans les sept fichiers.

Une concordance isolée sur la seule référence `20251954` concerne le numéro d'acheteur DECP `26310012500016`, différent du numéro `26630746100019` porté par l'avis BOAMP. Elle est qualifiée de **collision de référence entre acheteurs**, sans prétention à l'identité du contrat.

**Interprétation :** aucun lien contractuel BOAMP–DECP confirmé dans le périmètre des sept fichiers. La couverture nationale reste inconnue. Les références recherchées pourraient figurer dans un autre mois, un autre canal de publication ou un enregistrement nécessitant un autre jeu de documents primaires.

## Limites scientifiques

Cet exercice établit un dénominateur documentaire plus vaste et vérifiable. Il ne mesure ni un déficit de compétences scientifiques, ni le temps nécessaire à une contribution utile, ni l'existence d'un besoin encore non satisfait. Il ne permet pas de conclure qu'une nouvelle institution serait souhaitable.

Les sept fichiers sont des versions datées dont les empreintes SHA-256 sont conservées. Les fournisseurs de données peuvent modifier les ressources officielles ultérieurement. Les archives conservées sur GitHub ont une durée de disponibilité limitée ; le bilan durable conserve les identifiants de ressources, les volumes, les empreintes, les dénominateurs et les conditions de preuve nécessaires à une future reproduction.

Le protocole et ses essais sont décrits dans `docs/EXTENSION_DECP_SEPT_MOIS_DEDOUBLONNAGE_V1.md` et réalisés dans `scripts/etendre_balayage_decp_sept_mois.py`. Les calculs d'identités et de variantes sont également testés avec `tests/test_bilan_decp_sept_mois_publie.py`.

## Étape suivante

Avant de mobiliser de nouveaux volumes de fichiers, reconstituer pour les sept références BOAMP les **chaînes d'avis liés**, les éventuels marchés publiés hors de ces sept mois, les pouvoirs des acheteurs et les actes contractuels accessibles. Les références génériques et les homonymies doivent rester exclues des correspondances confirmées. La priorité est la qualité des liens documentaires, non la seule croissance du nombre d'enregistrements examinés.
