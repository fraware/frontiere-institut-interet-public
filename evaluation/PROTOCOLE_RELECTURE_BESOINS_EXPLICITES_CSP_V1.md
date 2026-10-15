# FRONTIÈRE — Première relecture des besoins explicitement publiés

## Question de recherche

À partir d'une sélection documentaire de recrutements publics, quelles
affirmations sur une **demande de compétences à une date donnée** sont
directement étayées par les champs du producteur ? Quels éléments manquent
pour conclure qu'une capacité est actuellement absente, ou qu'un besoin
reste non satisfait ?

Ce protocole interdit de transformer un poste publié en diagnostic de
pénurie de talents. Il interdit également de déduire un poste encore
ouvert d'une date de publication antérieure.

## Population et données

Source : fichier DGAFP diffusé sur Choisir le service public et extrait le
12 octobre 2026 dans les archives du dépôt. La source brute n'est pas
conservée dans Git ; les 16 partitions JSONL contiennent des champs
sélectionnés. Le manifeste précise la ressource, les dates de modification
connues, les empreintes cryptographiques et le nombre de variantes.

L'unité de lecture des partitions est une **variante de référence d'offre**.
Plusieurs variantes documentaires peuvent partager une référence ; la
procédure retient au maximum une variante par référence dans ses
échantillons, selon une règle déterministe. Une variante ne représente
pas nécessairement un poste distinct, un recrutement effectif ou une
capacité manquante.

## Préparation reproductible

Le programme `scripts/preparer_relecture_besoins_explicites.py` vérifie,
octet pour octet, les empreintes des seize partitions et leurs effectifs
contre le manifeste. Il rejette l'ensemble si une partition, un
enregistrement ou le décompte global est incompatible.

Pour chaque ligne admissible, il conserve uniquement :

- la référence, l'empreinte d'enregistrement, l'intitulé intégral et
  l'entité déclarée, relevée dans « organisme » ou, en son absence, dans
  « employeur », avec le nom du champ effectivement utilisé ;
- la date de publication avec le nom du champ exact d'origine ;
- les compétences attendues seulement si ce champ est renseigné,
  suffisamment court et non tronqué ;
- l'identifiant de la partition, le numéro de ligne, l'empreinte SHA-256
  de cette ligne et la liste des champs utilisés ;
- un statut explicite de **candidat non relu** et un état actuel
  **indéterminé**.

Un titre ou des compétences tronqués ne servent pas à qualifier une
demande spécifique. Les textes comprenant des adresses électroniques ou
adresses web ne sont pas reproduits. Les extraits publiés dans les archives
restent les champs du producteur, sans rédaction ou interprétation
nouvelle.

Deux strates de douze références chacune sont constituées en ordre
déterministe d'empreinte : un tirage parmi les variantes admissibles,
puis un complément scientifique et technique fondé sur un lexique
préenregistré appliqué uniquement au titre, métier et spécialisation.
Aucune référence n'apparaît dans les deux strates. Le choix repose sur
l'instantané disponible et sur des règles d'admissibilité : il ne
constitue **ni une estimation statistique représentative, ni une mesure
de couverture nationale**, et la sélection lexicale ne vaut pas
classification professionnelle validée.

La procédure GitHub
`.github/workflows/relecture-besoins-explicites-csp.yml`
archive les vingt-quatre fiches et leur empreinte pendant trente jours.
Elle n'ajoute **aucune observation automatiquement acceptée** au registre
public ; aucun nouveau contenu n'est intégré à `main` sans vérification
humaine des preuves.

## Consignes de relecture

Pour chaque référence, le relecteur doit répondre indépendamment :

1. Le texte exact de l'intitulé documente-t-il une compétence
   recherchée ? Quelle expression précise l'étaye ?
2. Le champ « compétences attendues » renseigne-t-il une capacité
   attendue de manière suffisamment précise pour être citée telle
   quelle ? Le champ est-il absent, tronqué ou trop général ?
3. Peut-on identifier l'organisme responsable au niveau où le besoin
   est exprimé, ou seulement un rattachement administratif déclaratif ?
4. Les dates documentent-elles une publication passée, une échéance de
   candidature, une date de vacance, ou un état actuel de l'offre ?
   Elles doivent rester des catégories distinctes.
5. Un complément primaire est-il indispensable pour établir le
   caractère encore ouvert du besoin, l'absence de capacité interne
   ou l'éventuelle satisfaction du recrutement ?

Le relecteur choisit l'une de quatre décisions :

| Décision | Sens |
|---|---|
| `recherche_competence_precise_documentee` | Une expression de compétence identifiable figure littéralement dans l'annonce |
| `recherche_generique_documentee` | Recrutement identifiable, compétence spécifique insuffisamment déterminée |
| `preuve_incomplete` | Un champ essentiel ou une source fait défaut |
| `hors_population_utilisable` | La référence ne peut être utilisée sans qualification supplémentaire |

Pour chaque décision, conserver le chemin du champ cité,
la citation littérale, la qualification et une justification. Les
citations ne doivent pas être reconstituées à partir de souvenirs
ou de reformulations ; l'empreinte de la ligne permet de retrouver
exactement l'enregistrement consulté.

La première passe doit être réalisée par deux relecteurs de manière
indépendante, sans accès à leurs décisions respectives. Les désaccords
sont enregistrés et arbitrés dans une deuxième passe distincte. Il
faut conserver aussi les refus et les dossiers insuffisants, afin de
mesurer les erreurs d'extraction et non seulement les réussites.

## Évaluation

Une fois les deux passes disponibles, compter, en séparant la strate
générale et la strate lexicale :

- la proportion de dossiers jugés interprétables, avec dénominateur
  explicite et intervalle de confiance si pertinent ;
- l'accord interrelecteurs et ses désaccords par catégorie ;
- les erreurs de champ, de citation et de datation ;
- les cas exigeant un accès à une pièce primaire plus complète ;
- les situations pour lesquelles l'état actuel reste indéterminé.

Aucune de ces mesures ne suffit à estimer la prévalence nationale des
besoins publics. La validité de la recherche de talents, la preuve de
pénurie et la datation de la satisfaction du besoin demanderont des
investigations distinctes.

## Exécution et limites

```sh
python -m pytest -q tests/test_preparer_relecture_besoins_explicites.py
python -m scripts.preparer_relecture_besoins_explicites --sortie /tmp/candidats-csp.json
```

Les contrôles GitHub exécutent aussi la procédure sur les 16 véritables
partitions. La proposition ne collecte aucun contenu extérieur et n'engage
aucun abonnement. Les champs libres sont filtrés contre les courriels, liens
web et numéros de téléphone reconnaissables. Ce filtrage ne constitue
pas une garantie d'absence de données personnelles : la relecture humaine
doit précéder toute publication durable des fiches.
