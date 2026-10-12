# Relevé des issues publiées — échantillon indépendant de 36 avis

## Protocole et séparation des résultats

Le tirage de 36 avis BOAMP a été exécuté dans la procédure GitHub Actions [38196247041](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38196247041) depuis un index vérifié (277 171 annonces dans 776 journées archivées). La semence, les six mois et les quotas ont été fixés avant de consulter les résultats de marché. Le SHA-256 de la liste ordonnée des identifiants est `40f791c35adcdc67d69bb933e873b0efaa7b24dd0c74958474dc6272b94242c8`.

Le fichier `echantillon-independant-technique.json` est une liste **de questions à examiner**, pas une référence scientifique ou une liste de cas classés. Le programme `scripts/relever_issues_echantillon_independant.py` consulte ensuite les 36 avis à l'identifiant exact, conserve les corps des réponses officielles, leur empreinte et une première **préqualification automatique**, avec le résultat par lot s'il s'agit d'un avis d'attribution doté d'un formulaire reconnu.

L'intégration à `.github/workflows/index-boamp-historique.yml` sépare chronologiquement le tirage sans information de résultat, puis le relevé des avis correspondants. La sortie est `releve-issues-36/rapport.json` accompagnée des réponses JSON originales.

## Préqualification et conclusions autorisées

- `attribution_officielle_avec_resultats` : un avis de nature ATTRIBUTION contient des résultats eForms lisibles par lot, y compris des motifs de non-attribution. Le classement demeure automatique et non confirmé par relecture indépendante.
- `avis_observe_sans_resultat_attribution` : l'avis examiné n'est pas un résultat d'attribution. **Il ne s'agit pas d'un cas sans offre.** Le devenir de la consultation reste indéterminé.
- `resultat_officiel_structure_non_interpretee` : la source est un avis d'attribution dont la structure n'a pas été entièrement interprétée. Aucune étiquette ne doit être produite par approximation.
- `non_retrouve_lors_du_releve` et `date_officielle_divergente` : l'absence à une consultation ponctuelle ou la divergence de date sont des résultats de contrôle documentaire, sans qualification d'issue.

Pour un lot couvert, la règle distingue `attribue_dans_cet_avis`, `absence_offre_explicite`, `non_attribue_autre_motif` et `non_classe`. Elle garde la statistique officielle et sa portée (`tenders` et `t-esubm` ne se confondent pas).

## Vérifications et protocole indépendant à réaliser

Le prélèvement par mots-clés techniques est intentionnel et non représentatif de l'ensemble de la commande publique. Il ne garantit pas la présence d'une quantité suffisante de cas « sans offre ». Il serait scientifiquement incorrect de modifier les 36 identifiants une fois les issues connues afin de favoriser une classe. Une extension enrichie en cas rares, si nécessaire, formera un second ensemble explicitement distinct et préenregistré.

Avant toute mesure d'exactitude des classements, deux relectures documentaires indépendantes doivent établir des références officielles **par lot**. Les désaccords sont à consigner, les cas irrésolus restent indéterminés et les publications multiples d'une même procédure ne constituent pas des observations indépendantes. Il faudra séparer la concordance des résultats de marché de l'hypothèse **causale** d'une pénurie de compétences scientifiques ou techniques.

Les comparaisons ultérieures comporteront une matrice de confusion, les faux diagnostics de pénurie, les abstentions justifiées, la couverture des cas, les temps de vérification et la provenance de chaque conclusion. **Aucun score de performance ni aucune évaluation indépendante n'est acquis par la seule exécution du relevé.**

Cette étape n'introduit aucune démarche relative à la conservation durable des archives.
