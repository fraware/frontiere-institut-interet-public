# Bilan documentaire du BOAMP historique

## Objet et garanties de provenance

Le programme `scripts/analyser_historique_boamp.py` extrait des statistiques descriptives d'un **index historique BOAMP intégralement vérifié**. Il exige l'index SQLite ainsi que la fiche `preuve-index.json` produite lors de la même construction. Il contrôle la version du schéma, l'intégrité de SQLite, l'empreinte SHA-256 de l'index, la révision exacte du dépôt et les décomptes de journées et d'avis indiqués dans la fiche de provenance. Une discordance interrompt la production, sans remplacer le bilan existant.

Les résultats comprennent la première et la dernière journée indexées, le nombre de journées calendaires de l'intervalle, les journées dépourvues d'archives dans cet intervalle, les volumes quotidiens et mensuels, les catégories publiées par la source et les vingt noms d'acheteurs les plus présents dans ces annonces. Le nom de l'acheteur est repris tel qu'il apparaît dans la source ; ses variations orthographiques ne sont pas fusionnées.

## Repérages lexicaux déclarés à l'avance

Les expressions régulières contrôlées par le programme recherchent des termes explicites dans le seul champ `objet` : intelligence artificielle, cybersécurité, robotique, calcul scientifique, imagerie géographique, sciences biologiques et instrumentation scientifique. Les règles, conservées dans `MOTIFS`, figurent intégralement dans chaque bilan. Les correspondances peuvent se recouvrir : un avis portant sur deux domaines entre dans deux décomptes. Trois exemples récents par domaine facilitent la consultation de la source, sans constituer un échantillon représentatif.

Le programme analyse **toutes les lignes présentes dans l'index**, y compris les avis ne correspondant à aucun domaine prédéfini. La répartition des domaines ne représente ni la structure réelle de la dépense publique ni un recensement des besoins de chercheurs. Le statut d'un avis, sa répétition, l'absence de publication et les éventuelles variations des mots employés par les acheteurs influencent directement ces observations. Un avis ne correspond pas nécessairement à un marché unique. Aucun délai de mobilisation, aucune compétence indisponible et aucune défaillance institutionnelle ne sont déduits de ces comptages.

## Exécution locale et publication automatique

Depuis la racine du dépôt, après construction de l'index :

```bash
python scripts/analyser_historique_boamp.py \
  --index /chemin/index-avis-boamp.sqlite3 \
  --preuve-index /chemin/preuve-index.json \
  --sortie /chemin/bilan-documentaire.json
```

La procédure `.github/workflows/index-boamp-historique.yml` reconstruit l'index, publie sa preuve et produit le bilan descriptif associé dans le même artefact temporaire. Elle exécute également les tests ciblés du calcul statistique. Le fichier JSON porte la révision source, l'empreinte de l'index, les dénominateurs, toutes les règles lexicales et des avertissements explicites.

Le protocole favorise les comparaisons reproductibles entre deux états de l'archive. Pour comparer des périodes, ramener les nombres d'annonces au nombre de jours effectivement archivés ; les périodes incomplètes et les changements dans la source doivent être signalés. Aucun résultat lexical n'est qualifié d'épisode institutionnel vérifié.
