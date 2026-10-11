# Contrôle automatique des six cas pilotes BOAMP

L'instrument `scripts/preparer_dossiers_pilotes_boamp.py` transforme le registre `evaluation/cas_pilotes_boamp_v1.json` en fiches documentaires vérifiées. Les six identifiants et dates du registre sont ceux des dossiers rédigés dans `docs/SIX_CAS_PILOTES_BOAMP_2026-10.md`. Ils servent à tester des hypothèses concurrentes ; ils ne constituent pas des six besoins validés.

## Vérifications sur les données réelles

Le programme contrôle l'empreinte de l'index BOAMP et ses dénominateurs, puis retrouve chaque avis par identifiant strict. Un avis absent, un identifiant dupliqué ou une différence avec la date préenregistrée interrompt le traitement. Les sorties exposent l'objet de la notice, l'acheteur déclaré, la source quotidienne, le lien officiel, la date de relevé et l'état documentaire réellement publié.

Pour le cas Tisséo, le relevé BOAMP actuel classe l'avis 26-83870 comme **RECTIFICATIF**. Ce document ne constitue donc pas la preuve de la date de la première consultation. Ce point doit demeurer explicite même si une source secondaire suggère un marché attribué.

Le programme vérifie également les fichiers quotidiens BeauAMP grâce à leurs tailles et empreintes SHA-256. Il recherche uniquement des égalités explicites entre les identifiants pilotes et `id_boamp_attribution` ou `id_boamp_contrat`. Il conserve les deux types de lien séparément, recense les lots et indique les fichiers sources. Les observations secondaires sont limitées à vingt exemples par cas, avec le nombre total de lignes concernées et un indicateur de troncature.

BeauAMP est une source enrichie indicative et sa période de disponibilité est partielle. Plusieurs lignes sur un même identifiant peuvent correspondre à des lots ou répétitions ; le nombre de lignes n'est jamais un nombre de marchés distincts. Une absence de correspondance dans les fichiers examinés ne prouve aucune absence d'attribution.

## Résultats et étapes documentaires

Les fiches produites distinguent les hypothèses préenregistrées de ce qui est effectivement prouvé. Elles signalent expressément l'absence d'analyse du cahier des charges, de reconstitution de l'origine du besoin, de validation de l'attribution officielle, de capacité disponible et de délai jusqu'à première contribution utile.

Le traitement n'engage aucun interlocuteur extérieur, n'effectue aucune inférence causale et ne prétend pas compléter les documents de consultation manquants. Il prépare un ensemble de données testables à confronter à des sources primaires lors de futures étapes techniques.

```bash
python scripts/preparer_dossiers_pilotes_boamp.py \
  --index /chemin/index-avis-boamp.sqlite3 \
  --preuve-index /chemin/preuve-index.json \
  --beauamp institutionnel/marches_attribues \
  --registre evaluation/cas_pilotes_boamp_v1.json \
  --sortie /chemin/dossiers-pilotes-documentaires.json
```

Le fichier est produit automatiquement dans la chaîne de construction de l'index BOAMP. Tout échec de vérification des fichiers secondaires ou d'une date préenregistrée empêche la publication du nouveau dossier.
