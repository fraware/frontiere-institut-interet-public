# Rapprochement des avis BOAMP et des attributions BeauAMP

## Objet

Le programme `scripts/rapprocher_avis_attributions.py` relie les documents BOAMP présents dans un index vérifié aux fichiers quotidiens BeauAMP archivés. BeauAMP est une source **enrichie et indicative**, produite par Adrien Deschamps (Avignon Université) sous licence CC-BY-SA. Les avis officiels demeurent nécessaires pour confirmer une attribution.

## Méthode de rapprochement

Deux champs de référence BeauAMP sont examinés séparément : `id_boamp_contrat` et `id_boamp_attribution`. Un rapprochement n'est enregistré que si une valeur canonique du champ correspond **exactement** à un identifiant de notice dans l'index BOAMP. Aucun rapprochement approximatif de noms, de titulaires ou d'objets de marché n'est effectué.

Toutes les archives BeauAMP déclarées dans le manifeste sont lues, après vérification de leur taille et de leur SHA-256. Les identifiants BOAMP ambigus dans l'index sont écartés du rapprochement. Une archive secondaire altérée interrompt le calcul sans remplacer le rapport précédent.

La sortie distingue les lignes du fichier secondaire (qui peuvent décrire différents lots d'un même marché), les liaisons exactes par type de référence et les identifiants BOAMP distincts concernés. Les exemples conservent le fichier source et l'archive BOAMP. Ils ne constituent pas un échantillon représentatif.

## Dates et limites

Pour les références contractuelles reliées, la méthode calcule uniquement l'intervalle entre **la date de parution du document BOAMP indexé** et **la date de l'avis d'attribution déclarée dans BeauAMP**. Les dates incohérentes ou antérieures sont signalées séparément ; les dates manquantes sont exclues de cet indicateur.

Cet intervalle ne mesure ni la durée totale de la procédure de marché, ni le délai depuis la formulation d'un besoin, ni le temps de mobilisation d'une compétence. Une absence de rapprochement ne démontre aucune absence d'attribution, en particulier hors des dates des petits fichiers quotidiens archivés.

## Exécution

```bash
python scripts/rapprocher_avis_attributions.py \
  --index /chemin/index-avis-boamp.sqlite3 \
  --preuve-index /chemin/preuve-index.json \
  --beauamp institutionnel/marches_attribues \
  --sortie /chemin/rapprochements-attributions.json
```

La procédure d'indexation BOAMP produit le rapport avec les autres analyses et contrôles. La collecte BeauAMP demande explicitement une reconstruction documentaire après fusion d'un nouveau lot.
