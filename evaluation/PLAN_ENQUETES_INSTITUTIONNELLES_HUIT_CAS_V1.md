# FRONTIÈRE — Huit enquêtes institutionnelles sur des recrutements documentés

**État au 15 octobre 2026.** Les huit références proviennent de l'échantillon de vingt-quatre offres préparé par la procédure GitHub 38817002674. Aucune ne démontre aujourd'hui un manque de compétences institutionnelles ou une possibilité réelle de détachement.

Le registre evaluation/enquetes_institutionnelles_8_cibles_v1.json contient les références, fichiers, numéros et empreintes SHA-256 de lignes ainsi que les questions individuelles. Le programme scripts/constituer_enquetes_institutionnelles.py vérifie les seize partitions d'offres et reconstruit chaque fiche à partir des lignes archivées. Les observations de pages officielles sont des annotations de recherche, dont les fichiers HTML complets ne sont pas archivés.

## Huit enquêtes et informations manquantes

| Référence | Publication historique / observation officielle | Prochaine preuve nécessaire |
|---|---|---|
| DEF_04-00070536 | Armée de terre ; annonce accessible sur Choisir le service public | Le recrutement a-t-il abouti ? Les habilitations et accès ont-ils retardé la prise de poste ? |
| 2026-2344611 | PRECOBOVE, école vétérinaire de Toulouse ; date limite du 9 août 2026 dépassée | Le projet a-t-il recruté dans les délais ? Quelle conséquence scientifique d'un éventuel retard ? |
| 2026-2309597 | Analyse chimique, Université de Haute-Alsace ; adresse officielle redirigée vers la dépublication | Quelles compétences instrumentales, quel résultat du recrutement et quelles solutions internes ? |
| UMR5214-MOBINT-Q56002 | Instrumentation CNRS ; fiche primaire longue non vérifiée indépendamment dans ce travail | Instruments, accès, financement, formation et issue du recrutement |
| 2026-2181943 | Statisticien, Aix-Marseille Université ; métadonnées d'archive | Programme de recherche, méthodes, compétences internes et recrutement réalisé |
| O032260213001234 | Projet informatique du Gers ; Emploi territorial indique que la candidature est expirée | Poste pourvu ? État du projet, mutualisation, solutions de référence |
| 2026-2290038 | Recherche clinique du centre hospitalier de Saint-Nazaire ; reprise par un site tiers seulement | Protocoles, gestion des données, contraintes réglementaires et recrutement |
| UMR5283-EMMSAN-003 | Traitement de transcriptions CNRS ; métadonnées d'archive | Objets traités, restrictions de données, logiciel et issue du recrutement |

Le site officiel présentant toujours une annonce ne prouve pas que le poste est actuellement vacant. La dépublication ne démontre pas que le recrutement a abouti. Un champ historique « vacant » n'a aucune force probatoire sur la situation présente.

## Étendue des preuves et données personnelles

La pièce de recrutement comporte référence, intitulé, entité déclarée, dates de publication ou diffusion, chemin et empreinte de la ligne. La réponse de site externe apporte un état d'accessibilité observé et une adresse officielle, distincts des faits de recrutement. Les affirmations sur l'issue et les difficultés restent « inconnue » ou « non établie » tant que l'institution ne les a pas confirmées.

Le programme classe la qualité du champ compétences attendues en quatre états : absent, tronqué, présent mais trop long ou filtré, et court repris. Il ne publie ni le texte long ni une liste de coordonnées de contact. Il ne transforme pas la présence de compétences déclarées en constat de pénurie.

Les huit dossiers doivent faire l'objet d'une revue de confidentialité et, si des conclusions sont envisagées, de validations indépendantes. Conserver aussi les refus et les réponses administratives négatives.

## Questionnaire institutionnel commun

1. Quel résultat opérationnel ou scientifique précis motivait la recherche, avec quelle échéance ?
2. À quelles dates les candidatures, auditions et décisions ont-elles été réalisées ? Quelle a été l'issue effective ?
3. Quelles équipes ou compétences internes ont-elles été envisagées ou mobilisées ?
4. Des organismes publics partenaires, services mutualisés ou dispositifs de mobilité ont-ils été sollicités ?
5. Quels obstacles exacts ont été rencontrés : compétences, accès, statut, financement, organisation, sécurité ou rémunération ?
6. Quelles conséquences temporelles ou financières observables ont découlé de ces difficultés ? Existe-t-il une pièce pour les corroborer ?
7. Quel mécanisme aurait été utile de façon supplémentaire aux solutions réellement utilisées, et avec quel responsable institutionnel ?

Ne demander aucune donnée personnelle de candidat. Distinguer entretiens, archives, déductions et preuves de résultat.

## Épisodes et capacités publiques

Le niveau P0 signifie information insuffisante ; P1 signifie compétence publique trouvée et mobilisable ; P2, compétence trouvée mais difficulté de mobilisation étayée ; P3, aucune compétence identifiée au terme d'une recherche suffisamment documentée. **Les huit dossiers commencent en P0.**

La qualification « épisode de déficit de capacité » exige un problème daté, une compétence précise, une difficulté de mobilisation effectivement attestée, des démarches publiques déjà tentées et une conséquence institutionnelle vérifiable. Les intitulés de poste ne remplissent pas ce standard.

Le recrutement réussi au LISC/INRAE, évoqué au cours des entretiens du projet, constitue une piste de contre-exemple à instruire séparément, sans l'introduire artificiellement dans la population de huit offres.

## Feuille d'exécution

**Jours 1 à 3 :** reconstituer les huit fiches, diagnostiquer les champs de compétences, contrôler les dates et les pages primaires disponibles.

**Jours 4 à 7 :** préparer les questions de chaque institution, rechercher les programmes de recherche et les mécanismes de mobilité, puis contacter les services appropriés si un canal institutionnel valide est identifié.

**Jours 8 à 21 :** obtenir les réponses, reconstruire les chronologies, documenter les situations sans réponse et les recrutements réussis autant que les difficultés.

**Jours 22 à 28 :** double relecture indépendante, arbitrage des désaccords, comparaison aux dispositifs existants et décision motivée d'étude approfondie ou de clôture.

La cible est de comprendre huit situations, **pas de déclarer huit déficits**. Les résultats produits par le programme restent des pièces d'instruction et ne sont pas automatiquement publiés dans la branche principale.

Pour reproduire : exécuter le test Python tests/test_constituer_enquetes_institutionnelles.py, puis le module scripts.constituer_enquetes_institutionnelles avec l'option --sortie pointant vers un chemin temporaire non existant.
