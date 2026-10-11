# Banc de rappel textuel des correspondances institutionnelles

## Question

Le remplacement de la recherche par mots isolés par une recherche d'expressions complètes améliore-t-il la **couverture des correspondances textuelles présentes dans le même référentiel** ?

La comparaison n'utilise aucun jugement humain et ne mesure aucune pertinence opérationnelle. Sa référence est un recensement technique obtenu en parcourant toutes les lignes correspondantes des quatre champs de l'index institutionnel, puis en vérifiant la présence de l'expression entière dans les textes officiels publiés ou les noms d'organismes.

## Méthodes comparées

Les expressions évaluées proviennent des pistes BOAMP produites à partir de l'index vérifié. Le programme `scripts/evaluer_rappel_textuel.py` les déduplique et exécute, pour chacune, trois procédures : recensement de référence sans plafond de résultats ; ancien moteur fondé sur des mots isolés avec 25 restitutions par classe ; nouveau moteur fondé sur une expression entière, avec 500 candidats au plus par champ.

Les éléments retournés sont à nouveau comparés à leurs passages documentaires. Les résultats hors de la référence provoquent une erreur ; une omission du moteur exact sans saturation déclarée provoque également une erreur.

Le rapport mesure, par expression, le nombre de concordances textuelles de référence, les correspondances retrouvées par les deux méthodes, les omissions et les troncatures. Chaque recensement de référence possède une empreinte SHA-256 calculée sur les identifiants triés. Les sommes globales sont **non dédoublonnées entre expressions**, car un organisme peut figurer dans plusieurs recherches.

## Interprétation et limites

Le rappel textuel est le rapport entre identifiants retrouvés et identifiants portant réellement une expression exacte dans les champs indexés. Il ne mesure ni les synonymes, ni les connaissances implicites, ni l'aptitude scientifique, ni la disponibilité, ni le succès d'une mobilisation.

Le nombre d'expressions est limité aux requêtes issues des pistes exploratoires de ce cycle, lesquelles ne représentent pas la demande nationale. Les résultats doivent être comparés sur la **même révision du référentiel et le même jeu de requêtes**. La procédure d'indexation BOAMP conserve désormais le rapport `banc-rappel-textuel.json` aux côtés des preuves et de l'audit de concentration.
