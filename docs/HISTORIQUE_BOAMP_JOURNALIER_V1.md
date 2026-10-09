# Historique officiel des avis BOAMP par journées closes

## Objet

Le programme `scripts/collecter_historique_boamp.py` vise à constituer, par progression temporelle, un archive des **métadonnées publiques des avis** du Bulletin officiel des annonces des marchés publics (BOAMP). Il complète la collecte glissante de sept jours. La collecte se limite aux champs explicitement sélectionnés et n'aspire ni le texte intégral des avis ni les coordonnées de contact.

**Producteur à citer :** Direction de l'information légale et administrative (DILA), BOAMP. Conserver l'adresse officielle du jeu, la date de collecte et les références des avis. La documentation de réutilisation et les avertissements de la DILA figurent sur [la page officielle](https://www.boamp.fr/pages/donnees-ouvertes-et-api/).

## Méthode

Une demande interroge uniquement les enregistrements dont `dateparution` appartient à une journée civile précise, du début inclus au lendemain exclu. Les résultats sont triés par identifiant. Toutes les pages jusqu'au total officiellement annoncé sont exigées ; une page manquante, un total instable, un identifiant répété, une annonce mal datée ou un plafond de pagination insuffisant interrompt **la journée entière**.

Chaque journée réussie produit :

- `historique_boamp/AAAA/MM/AAAA-MM-JJ.jsonl.gz` : notices normalisées, triées par identifiant et comprimées de manière reproductible ;
- `historique_boamp/AAAA/MM/AAAA-MM-JJ.json` : nombre d'avis, date du relevé, origine, attribution, empreinte SHA-256 du contenu décompressé et empreinte du fichier comprimé ;
- `etat_historique_boamp.json` : curseur de reprise, jours achevés pendant la dernière exécution, décompte et erreurs.

Le manifeste d'une journée est écrit **après** l'archive. Le curseur ne recule que pour les journées intégralement collectées. Les journées déjà archivées sont vérifiées par empreinte avant réutilisation. Les archives défectueuses provoquent un arrêt explicite. Aucun fichier de données antérieur n'est supprimé par le programme.

Le plafond initial est de cinquante pages de cent avis par journée ; ce plafond constitue une contrainte technique. Si une journée en comporte davantage, une autre méthode de partition ou d'export sera nécessaire avant de pouvoir la déclarer complète.

## Première exécution et progression

Depuis la racine du dépôt :

```bash
python -m pytest -q tests/test_collecte_historique_boamp.py tests/test_publication_besoins_publics.py
python scripts/collecter_historique_boamp.py --jours 24
```

En absence de curseur, le programme commence huit jours avant la date d'exécution, pour limiter le chevauchement avec la collecte courante. Les premiers relevés effectifs ont commencé le 9 octobre 2026 et ont confirmé huit journées complètes, du 24 septembre au 1er octobre 2026, pour 2 817 avis normalisés. Le programme est ensuite réglé pour traiter au plus vingt-quatre journées par exécution, en remontant vers le 1er janvier 2018. La collecte programmée publie ses modifications dans des propositions soumises aux trois contrôles du dépôt. La portée historique complète et la stabilité transactionnelle de la source restent non établies.

Les journées entièrement traitées comptent des **avis BOAMP** et non des marchés distincts, des difficultés de recrutement, des besoins scientifiques avérés ou des interventions FRONTIÈRE. Une déclaration de complétude ne concerne que la journée et l'instant du relevé. Les corrections ultérieures à la source, les avis antérieurs au plancher, les archives historiques officielles en dehors de cette interface et les erreurs de classification restent hors du périmètre démontré.

## Sécurité et intégrité

Le programme utilise exclusivement l'adresse de l'interface publique et n'accepte aucune adresse externe depuis une fiche de données. Les réponses ont une taille bornée par le collecteur existant, les appels sont ralentis et un échec de récupération conserve le curseur. Aucune sortie privée ou pièce sensible ne doit être jointe au dépôt public. Une empreinte conservée dans le même dépôt vérifie la cohérence des fichiers, mais **ne constitue pas une attestation externe immuable**.

## Contrôle continu et limites après activation

Vérifier par une exécution réelle la validité des filtres de dates et de l'ordre de tri de l'interface actuelle. Contrôler ensuite, sur plusieurs journées incluant une journée sans avis, la cohérence entre `total_count` et les enregistrements réellement archivés, puis identifier les dates dont le volume dépasse le plafond. Les tests fictifs constituent des contrôles de fonctionnement, jamais une preuve de complétude des archives institutionnelles.
