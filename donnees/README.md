# Corpus public de signaux

Ce dossier rassemble des situations documentées dans des sources publiques officielles afin d'identifier des cas susceptibles d'éclairer la mobilisation des capacités scientifiques et techniques dans l'action publique.

## Statuts documentaires

- **signal contextuel** : constat utile, mais insuffisant pour reconstruire un cas précis ;
- **cas partiel** : plusieurs éléments d'un cas sont connus, mais certaines étapes importantes manquent ;
- **cas solide** : le besoin, la capacité, la réponse ou l'obstacle et une partie de la chronologie sont suffisamment documentés pour une analyse détaillée.

Un signal n'est jamais transformé automatiquement en cas réel.

## Champs

Chaque entrée conserve :
- l'institution et la période ;
- le domaine ;
- la nature du signal ;
- le fait documenté ;
- la capacité concernée ;
- la réponse observée ;
- le niveau documentaire ;
- la présence ou non d'une solution connue ;
- la possibilité ou non de reconstruire une chronologie ;
- le caractère éventuel de contre-exemple ;
- la source officielle ;
- la priorité d'examen.

## Règles

1. Une même source peut soutenir plusieurs signaux distincts si les mécanismes observés diffèrent clairement.
2. Un chiffre ancien est conservé avec sa date et n'est jamais présenté comme une mesure actuelle.
3. Les constats généraux restent des signaux contextuels tant qu'un cas précis n'est pas identifié.
4. Les contre-exemples sont recherchés activement.
5. Une entrée doit être retirée ou corrigée si la source ne soutient pas directement le fait décrit.

Le fichier `signaux_publics_v1.json` constitue la première tranche. L'objectif suivant est d'atteindre environ cent signaux, puis de retenir les trente cas les plus documentés.

## Registre de vérification des événements

Le fichier `registre_verification_evenements_v1.json` recense les événements des dix chronologies de recherche les plus récentes (version 3), avec leur date conservée à la précision d'origine, le texte du fait allégué et **la source candidate du signal parent**.

Chaque événement porte la valeur `A_VERIFIER` : l'existence d'une source publique associée au signal **ne prouve pas** qu'elle documente précisément cet événement. Le fichier rend la tâche de vérification explicite, événement par événement, sans produire de citation nouvelle ni modifier les interprétations historiques. Les champs de relecture restent vides jusqu'à examen de la source par une personne compétente.

La commande `python scripts/construire_registre_verification_evenements.py --sortie /chemin/nouveau_registre.json` régénère un exemplaire de contrôle sans écraser un fichier existant. Les tests vérifient l'identité exacte du registre avec les fichiers sources du dépôt. Toute validation factuelle doit conserver la référence du passage justifiant le fait et la date de vérification.

## Version des chronologies et rectifications

La version de référence actuelle est `chronologies_v4.json` ; son registre de vérification est `registre_verification_evenements_v2.json`. La version 3 et le registre 1 restent disponibles sans modification. Les corrections portant sur le procès-verbal de l’IGN et le rapport sénatorial relatif à France Compétences figurent dans [le rectificatif documentaire](RECTIFICATIF_SOURCES_2026-10-08.md). Elles précisent la distinction entre date d'observation, date de séance et date de publication, sans créer de délais artificiels ni valider les autres événements.

### Complément sur Saint-Brieuc

La version la plus récente est désormais `chronologies_v5.json`, avec `registre_verification_evenements_v3.json`. Elle précise les dates du conseil scientifique de Saint-Brieuc à partir du rapport IGEDD, en distinguant notamment la date du rapport (juin 2025) de sa mise en ligne (mars 2026). Voir [la note de provenance](NOTE_SOURCES_SAINT_BRIEUC_2026-10-08.md). Les versions 3 et 4, ainsi que les registres antérieurs, restent conservés.

## Première lecture de passages primaires

Le fichier `passages_sources_evenements_v1.json` relie quatorze événements du registre courant à des passages précis de documents officiels. Il s'agit d'une **lecture documentaire préliminaire par l'assistant**, non d'une relecture humaine indépendante. Chaque entrée distingue l'assertion précisément soutenue, le document, son emplacement et les limites de l'inférence. Les autres événements restent sans passage individuel documenté dans ce fichier.

La commande `python scripts/verifier_passages_sources.py` vérifie la cohérence des identifiants, la structure des liens et l'absence de déclaration d'indépendance. Elle ne consulte pas les sources distantes et n'établit pas leur véracité. Une relecture documentaire contradictoire doit précéder toute qualification de preuve définitivement vérifiée.

### Correction des doublons et identifiants stables

La version active devient `chronologies_v6.json` ; elle conserve dix chronologies, comporte **46 événements distincts** après fusion de deux paires de doublons à Mayotte et attribue à chaque événement un identifiant historique stable. Le registre correspondant est `registre_verification_evenements_v4.json`, avec `passages_sources_evenements_v2.json` pour les quatorze premières lectures documentaires. Les identifiants supprimés et leurs successeurs sont consignés dans la version 6. Voir [la note Mayotte](NOTE_SOURCES_MAYOTTE_2026-10-08.md). Une date de nomination ou de prise d'effet juridique ne doit pas être assimilée à une date de première contribution utile.

### Provenance temporelle du cas DGA

La version active est `chronologies_v7.json` (toujours 46 événements pour dix chronologies), avec `registre_verification_evenements_v5.json` et `passages_sources_evenements_v3.json`. Quatre constats du cas DGA sont reliés au rapport parlementaire **enregistré le 17 janvier 2024**, tout en conservant 2023 comme période approximative des situations décrites. Le registre de passages couvre maintenant **18 événements**, dont la première lecture ne constitue pas une vérification indépendante. Voir [la note DGA](NOTE_SOURCES_DGA_2026-10-08.md).

### Chaîne documentaire PFAS et extension des sources

La référence active est `chronologies_v8.json`, son registre `registre_verification_evenements_v6.json`, et le dossier de passages `passages_sources_evenements_v4.json`. La version 8 distingue explicitement la remise de l'expertise PFAS le 15 avril 2026, la signature de la circulaire le 27 avril et leurs dates de publication. Elle préserve 46 événements sur dix cas. **29 événements** disposent maintenant d'un passage source localisé dans le registre, avec limites d'interprétation et absence de confirmation indépendante ; **17 restent à documenter individuellement**. Voir [la note PFAS](NOTE_SOURCES_PFAS_2026-10-08.md).

## Rapprochement des événements et des passages officiels — cinquième lecture

La collection `passages_sources_evenements_v5.json` est construite sur les mêmes 46 événements de `registre_verification_evenements_v6.json`. Elle comprend **44 premières lectures documentaires** avec sources et limites explicites, dont quinze nouvelles références à l'IGN, à Météo-France, à l'IGEDD, à l'ASNR et au Sénat. Deux événements restent sans passage individualisé suffisant : `S038-E06` et `S042-E04`. Les incertitudes et les documents nécessaires sont détaillés dans [l'état des preuves](ETAT_PREUVES_PAR_EVENEMENT_2026-10-08.md).

Les versions précédentes du registre de passages sont conservées et vérifiables. Le programme `python scripts/verifier_passages_sources.py` exige que les deux références manquantes correspondent exactement aux événements absents du fichier courant. **Le passage de 29 à 44 premières lectures ne constitue pas une relecture indépendante.**
