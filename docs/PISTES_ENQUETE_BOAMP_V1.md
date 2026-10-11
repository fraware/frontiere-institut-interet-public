# Pistes documentaires pour enquêtes institutionnelles — BOAMP

## Objet

Le programme `scripts/constituer_pistes_boamp.py` transforme les repérages lexicaux du bilan BOAMP en une liste **bornée, reproductible et vérifiable de notices à examiner**. Chaque notice sélectionnée comporte sa date, son identifiant, son objet, l'acheteur déclaré, le lien officiel vers l'avis, le chemin de l'archive contrôlée, l'instant du relevé et les règles lexicales effectivement déclenchées.

Les trois fichiers d'entrée sont indissociables : `index-avis-boamp.sqlite3`, `preuve-index.json` et `bilan-documentaire.json`. La procédure refuse une discordance entre les empreintes SHA-256, les versions ou les règles lexicales du bilan. Elle n'interroge aucun site extérieur. Le fichier de sortie `pistes-a-examiner.json` accompagne les autres fichiers dans chaque artefact de recherche BOAMP.

## Politique de sélection explicite

Pour chacun des sept domaines techniques déclarés dans le bilan, le programme parcourt les annonces dans l'ordre de la date de parution décroissante, puis de l'identifiant croissant. Il retient au maximum **douze avis par domaine** et **deux avis par acheteur normalisé et par domaine**. Les accents et la casse sont normalisés pour appliquer cette limite, sans effectuer une résolution d'identité institutionnelle. Un avis peut appartenir à plusieurs domaines si son objet correspond à plusieurs règles.

La liste finale est volontairement **non représentative**. Elle facilite un premier examen diversifié et privilégie les avis récents. Elle ne remplace ni un tirage probabiliste ni une revue complète du corpus, et son plafond ne mesure aucune fréquence dans la population. Les nombres de correspondances totales sont conservés séparément dans le bilan documentaire.

## Instruction d'un dossier de cas

Pour chaque avis retenu, la phase de vérification doit documenter progressivement l'objet exact de la commande, les dates pertinentes, l'identité et la mission de l'acheteur, les compétences déjà disponibles en interne, les solutions contractuelles et partenariales accessibles, les moyens juridiques de mobilisation et les éventuels délais observés. Les informations manquantes doivent rester explicitement inconnues. Une enquête humaine ou une source institutionnelle complémentaire est nécessaire pour établir ces éléments.

La présence d'un avis BOAMP et une correspondance lexicale ne démontrent jamais une pénurie scientifique. Le fichier `pistes-a-examiner.json` contient des états explicites `besoin_scientifique_valide=false`, `disponibilite_competences_etablie=false` et `decision_institutionnelle_etablie=false`. Ces états indiquent l'absence de validation dans ce protocole documentaire, et non une conclusion selon laquelle le besoin, les compétences ou la décision n'existent pas.

## Reproduction locale

Après avoir récupéré les trois fichiers issus de la même construction d'index :

```bash
python scripts/constituer_pistes_boamp.py \
  --index /chemin/index-avis-boamp.sqlite3 \
  --preuve-index /chemin/preuve-index.json \
  --bilan /chemin/bilan-documentaire.json \
  --sortie /chemin/pistes-a-examiner.json
```

La procédure automatique de construction de l'index publie les quatre fichiers ensemble et exécute les tests de la sélection. Les règles pourront évoluer lors d'une révision explicitement documentée du protocole, en conservant les bilans antérieurs comme références historiques.
