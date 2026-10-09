# Suivi des modifications rétroactives des avis BOAMP

## Question documentaire

Un premier relevé d'une journée du Bulletin officiel des annonces des marchés publics (BOAMP) représente les notices accessibles à un instant donné. Une correction, un retrait, une publication tardive ou une modification de l'interface pourrait modifier ultérieurement ce relevé. FRONTIÈRE doit distinguer l'état observé lors de la première collecte et les états observés lors des nouveaux contrôles.

Le programme `scripts/surveiller_revisions_boamp.py` réinterroge des journées déjà archivées sur l'interface officielle de la Direction de l'information légale et administrative (DILA). **Les fichiers initiaux ne sont jamais modifiés** par ce programme. Chaque variation entre deux relevés complets déclenche un nouveau fichier compressé adressé par empreinte et un constat décrivant les changements d'identifiants.

## Politique de surveillance

À chaque passage, le programme examine les deux journées archivées les plus récentes et quatre journées parcourues par rotation parmi l'ensemble des archives historiques. Le curseur repose sur une date et non sur la position courante dans une liste, afin de continuer à fonctionner lors de l'ajout de nouvelles journées plus anciennes. Les journées déjà inspectées reviennent progressivement dans le cycle, sous réserve de disponibilité de l'interface.

Une date est comparée seulement si les deux états satisfont les contrôles de provenance, de pagination, de décompte et d'empreintes. Le programme refuse de déclarer « aucun changement » en cas d'indisponibilité ou de lecture partielle. Toute erreur est consignée. La rotation ne progresse pas si une erreur survient. La publication peut continuer pour les autres sources sans attribuer à cette date un résultat favorable.

Lorsqu'une différence est observée, le dépôt reçoit sous `institutionnel/besoins_publics/revisions_boamp/AAAA/MM/AAAA-MM-JJ/` un nouvel état compressé et son constat `<empreinte>.json`. Le constat précise les deux empreintes, les dates du relevé initial et du nouveau contrôle, les volumes et trois groupes d'identifiants : apparus, absents du nouveau relevé et modifiés. L'absence au relevé ne prouve pas la suppression juridique d'un avis ; les raisons d'une variation restent à établir. Une révision identique déjà conservée est reconnue sans créer une copie supplémentaire.

Le fichier `etat_revisions_boamp.json` présente le lot vérifié, les erreurs, les journées avec variation et le curseur. Il établit uniquement ce qui a été contrôlé pendant le passage considéré. **Un résultat sans variation ne démontre jamais l'absence de toute modification historique.**

## Exécution et contrôles

Depuis la racine du projet :

```bash
python -m pytest -q tests/test_surveiller_revisions_boamp.py
python scripts/surveiller_revisions_boamp.py
```

La collecte programmée des besoins publics lance cette surveillance après la collecte historique. Les fichiers passent par la procédure de proposition et les trois contrôles du dépôt avant publication. Une panne de la source historique laisse fonctionner le relevé des autres besoins publics.

Le programme n'établit ni l'origine des corrections, ni une exhaustivité des marchés, ni un besoin d'expertise scientifique. Les fichiers contiennent uniquement les champs publics déjà sélectionnés par la collecte BOAMP, à l'exclusion des coordonnées de contact. La validité des droits de réutilisation reste déterminée par les conditions de l'interface officielle.

## Croissance et entretien

Chaque version distincte d'une journée modifiée crée un fichier supplémentaire. La compression est reproductible et chaque cliché porte deux empreintes, sur les octets comprimés et décompressés. Les fichiers anciens restent disponibles pour audit. Le volume doit être suivi séparément avant de déplacer des archives vers un stockage externe à conservation durable ; une migration future nécessitera une correspondance vérifiable entre les manifestes Git et les objets conservés hors du dépôt.

Le système ne garantit pas une consultation transactionnelle de l'interface distante pendant une pagination. Un changement du contenu sans variation du décompte pourrait être observé comme une modification réelle ; chaque constat décrit les différences entre relevés, sans conclure sur la cause institutionnelle.
