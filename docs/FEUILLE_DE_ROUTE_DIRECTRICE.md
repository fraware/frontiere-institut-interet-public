# FRONTIÈRE — Feuille de route directrice et registre d'exécution

**Version :** 1.0 · **Création :** 16 octobre 2026 (UTC) · **Point de départ vérifié :** `bc44675b4b30298d9337dda92699c0a4c47bcba2` · **Périmètre :** projet national FRONTIÈRE.

> Ce document constitue le registre durable des travaux prévus, et non la preuve qu'ils sont terminés. Il complète le [plan d'enquête de douze semaines](PLAN_12_SEMAINES.md) et le [protocole](PROTOCOLE_V1.1.md), qu'il ne remplace pas. Les échéances sont des cibles révisables. Une collecte, un rapprochement documentaire ou un test unitaire ne prouve pas, à lui seul, un déficit institutionnel ni une efficacité réelle.

## Finalité

Construire une infrastructure française permettant d'identifier les institutions publiques et leurs activités, de relier les publications et les événements à des projets et capacités, de qualifier les besoins publics explicitement établis, d'anticiper certains besoins sous contrôle expérimental, puis d'orienter vers des ressources effectivement mobilisables. Les décisions publiques et les choix engageant des personnes restent sous responsabilité des autorités compétentes.

## Règles de gestion

- **Identifiant permanent :** chaque travail possède un numéro `F-001` à `F-091`. Ne pas le réaffecter même en cas d'abandon. Pour de nouveaux travaux, attribuer `F-092` et suivants sans renuméroter les anciens.
- **États autorisés :** `À faire`, `En cours`, `Bloqué`, `Terminé`, `Abandonné`. `Terminé` exige une preuve (révision Git, procédure réussie et, si nécessaire, vérification sur données réelles ou institutionnelle). Une réalisation partielle ne suffit pas.
- **Traçabilité :** inscrire dans le [journal des revues](SUIVI_FEUILLE_ROUTE.md) la date UTC, la révision observée, les changements, les références GitHub et les inconnues. Documenter toute modification de priorité, d'échéance ou de critère.
- **Cadence :** revue **hebdomadaire le lundi**, après chaque contribution substantielle et lors de tout incident critique. Une revue sans changement significatif peut conclure « aucun changement ». Les mises à jour passent par une demande de fusion validée ; aucune réécriture automatique silencieuse.
- **Conditions de sécurité :** recherche prioritaire des capacités publiques existantes, conservation des résultats négatifs, données sensibles hors du dépôt public, aucune nouvelle dépense récurrente sans autorisation explicite.
- **Frontière de preuve :** distinguer document observé, activité institutionnelle, capacité explicitement recherchée, déficit de capacité confirmé et hypothèse d'anticipation ; ne pas convertir implicitement une catégorie dans une autre.
- **Travaux déjà préparés :** plusieurs mécanismes existent dans le dépôt. « En cours » signifie que le résultat complet formulé ici n'a pas encore été démontré ; il ne signifie pas que rien n'a été développé.

## Jalons de vérification

| Jalon | Cible indicative | Résultat conditionnant la suite |
| --- | --- | --- |
| J1 | Fin octobre 2026 | Archives, index, exécutions et publication vérifiés sur une révision explicite |
| J2 | Fin novembre 2026 | Premier lot de dossiers institutionnels multisources relus et datés |
| J3 | Décembre 2026 | Registre de besoins documentés, distinct des déficits confirmés |
| J4 | Janvier 2027 | Évaluation historique anti-fuite et premières hypothèses prospectives préenregistrées |
| J5 | Premier semestre 2027 | Recherche de capacités et infrastructure durables, sous réserve des mesures |

## Suivi exhaustif des 91 travaux

### Phase 0 — Stabiliser la chaîne existante

**Horizon indicatif :** 16–23 octobre 2026. **Résultat de phase :** Reconstruction des données, état Git et déploiement connu, aucune dépense supplémentaire.

| ID | État au lancement | Action | Preuve minimale d'achèvement |
| --- | --- | --- | --- |
| F-001 | En cours | Établir l'état de référence contrôlé des archives et services | SHA Git, empreintes, versions et horodatages réunis dans un bilan reproductible |
| F-002 | À faire | Réconcilier les huit demandes de fusion ouvertes | Chaque demande fusionnée, révisée ou fermée avec justification et contrôle de concurrence |
| F-003 | En cours | Vérifier les archives BOAMP, CSP et DECP | Unités, périodes, dénominateurs et empreintes explicitement mesurés |
| F-004 | En cours | Reconstruire les deux index locaux SQLite intégraux | Effectifs, requêtes de référence et empreintes concordants sur corpus réel |
| F-005 | À faire | Tester l'échec de construction et les données invalides | Les corruptions et collisions sont refusées sans destruction de l'index précédent |
| F-006 | En cours | Auditer les collectes programmées et leurs permissions | Exécutions, retards, échecs, droits et automations documentés |
| F-007 | En cours | Mesurer puis résorber l'écart GitHub–Render | Commit et inventaire exacts du site publiés puis rapprochés d'une révision validée |
| F-008 | En cours | Produire un bilan unique de santé documentaire | Rapport par source indiquant succès, retards, lacunes et disponibilité de consultation |
| F-009 | À faire | Auditer la sécurité, les licences et les données publiques | Exceptions recensées, exposition des données sensibles vérifiée, actions à privilège contrôlées |
| F-010 | À faire | Publier une attestation de reproductibilité du premier cycle | Commandes, sorties, journaux, limites et points non reproduits accessibles |

### Phase 1 — Couverture et collecte

**Horizon indicatif :** 19 octobre–8 novembre 2026. **Résultat de phase :** Catalogue de sources mesuré et collecte suivie par producteur.

| ID | État au lancement | Action | Preuve minimale d'achèvement |
| --- | --- | --- | --- |
| F-011 | À faire | Unifier les registres de sources existants | Identifiants et statuts dédoublonnés, origine de chaque entrée retrouvable |
| F-012 | À faire | Construire des dénominateurs de couverture par source | Définition des objets observables, période, reçus, admis et manquants |
| F-013 | En cours | Vérifier le balayage du catalogue national data.gouv.fr | Pages et omissions documentées, comparaison avec export complet quand admissible |
| F-014 | À faire | Définir une cadence différenciée de collecte par producteur | Fréquence, délai attendu, coût et limites source consignés |
| F-015 | En cours | Renforcer les relevés et archives BOAMP | États et avis liés distingués, collecte historique et récente contrôlée |
| F-016 | En cours | Conserver les variantes et états des recrutements publics | Version, référence, date et état de publication correctement différenciés |
| F-017 | En cours | Consolider les formats et producteurs DECP | JSON, XML, variantes, acheteurs et identités harmonisés avec attestations |
| F-018 | En cours | Actualiser le référentiel institutionnel et territorial | Créations, fermetures, identifiants et changements de compétences suivis |
| F-019 | En cours | Qualifier et relier les sources scientifiques admissibles | ANR, MESR, RNSR, HAL, CORDIS examinés selon licences et pertinence |
| F-020 | En cours | Structurer les budgets, programmes et autorisations publiques | Prévision, autorisation, engagement et dépense séparés |
| F-021 | À faire | Étendre les sources locales et délibérations | Sources SCDL partielles déclarées, actes datés et versions conservées |
| F-022 | En cours | Mettre en place la détection des changements par source | Ajouts, retraits de relevés, corrections, annulations et schémas séparés |
| F-023 | En cours | Prévoir une supervision indépendante de l'exécution des collectes | Arrêt du système de surveillance lui-même détectable |

### Phase 2 — Reconstruction institutionnelle

**Horizon indicatif :** 26 octobre–22 novembre 2026. **Résultat de phase :** Dossiers intersources cohérents et relations datées vérifiables.

| ID | État au lancement | Action | Preuve minimale d'achèvement |
| --- | --- | --- | --- |
| F-024 | En cours | Mesurer la couverture des quatorze familles d'organismes | Taux et lacunes définis pour chaque famille et sa population |
| F-025 | En cours | Stabiliser les identités et rôles administratifs | Identifiants officiels, acheteurs, employeurs, autorités et opérateurs distingués |
| F-026 | À faire | Modéliser créations, fusions, scissions et changements de tutelle | Identités historiques et liens de succession conservés |
| F-027 | À faire | Représenter les projets publics indépendamment de leurs avis | Projet distinct de publication, achat ou recrutement |
| F-028 | À faire | Définir les événements publics typés | Annonce, financement, offre, attribution, livraison et résultat distingués |
| F-029 | En cours | Enregistrer les dates d'événement, publication, observation et validité | Reconstitution d'une connaissance telle qu'accessible à une date donnée |
| F-030 | À faire | Représenter les relations institutionnelles avec preuves | Lien, source, dates, méthode et incertitude conservés |
| F-031 | En cours | Séparer rapprochements exacts, candidats et non établis | Cas ambigus conservés sans fusion automatique |
| F-032 | En cours | Étendre les dossiers d'acheteurs attestés | Requêtes par SIRET et avis corroborés sans supposer un contrat commun |
| F-033 | En cours | Assembler les chronologies institutionnelles multisources | Séquences reproductibles avec documents et types d'événements |
| F-034 | En cours | Livrer les premières fiches institutionnelles consolidées | Objectif expérimental : 20 fiches relues avec provenance et manques |
| F-035 | À faire | Évaluer les faux rapprochements et les omissions | Cas positifs, négatifs, ambigus et erreurs par catégorie |

### Phase 3 — Registre des besoins publics

**Horizon indicatif :** 9 novembre–6 décembre 2026. **Résultat de phase :** Premiers besoins datés, différenciés des déficits institutionnels démontrés.

| ID | État au lancement | Action | Preuve minimale d'achèvement |
| --- | --- | --- | --- |
| F-036 | À faire | Définir l'identité persistante d'un besoin | Organisme, période, objectif, capacité et versions reliés |
| F-037 | À faire | Séparer la demande publiée du déficit de capacité | Absence de déduction automatique d'une pénurie depuis un avis |
| F-038 | À faire | Modéliser les niveaux de preuve de chaque besoin | Déclaré, corroboré, candidat et non établi avec règles documentées |
| F-039 | À faire | Distinguer les états opérationnels des niveaux de preuve | Programmé, en cours, satisfait, abandonné et inconnu |
| F-040 | En cours | Définir les catégories de capacités recherchées | Personnes, équipes, outils, données, équipements, méthodes et procédures |
| F-041 | En cours | Construire l'extraction contrôlée des demandes déclarées | Passages exacts, organisme, capacité, échéance et source identifiés |
| F-042 | À faire | Conserver champs incomplets, contradictoires et tronqués | Inconnus, refus d'extraction et désaccords consultables |
| F-043 | En cours | Qualifier les 24 pièces de recrutement préselectionnées | Relectures, preuves et absence de conclusion non justifiée |
| F-044 | En cours | Poursuivre les huit enquêtes documentaires initiales | Différences de versions et issue réelle inconnue correctement consignées |
| F-045 | En cours | Relire les six cas pilotes BOAMP en recherchant les explications concurrentes | Qualification distinguant achat, prestation, ressource et déficit éventuel |
| F-046 | En cours | Rapprocher les besoins de leurs événements préparatoires | Relations établies par preuves sans déduire une causalité |
| F-047 | À faire | Permettre la consultation des besoins structurés | Recherche par organisme, domaine, dates, état et preuves |

### Phase 4 — Détection et anticipation

**Horizon indicatif :** Décembre 2026–janvier 2027. **Résultat de phase :** Première évaluation chronologique avec résultats positifs et négatifs.

| ID | État au lancement | Action | Preuve minimale d'achèvement |
| --- | --- | --- | --- |
| F-048 | À faire | Définir les classes d'événements futurs observables | Cible, unité d'événement, horizon et critères de confirmation fixés |
| F-049 | À faire | Construire des trajectoires historiques avec dates de connaissance | Événements préparatoires distingués des informations futures |
| F-050 | À faire | Définir des hypothèses prospectives datées | Organisme, capacité, période, preuves et condition de réfutation |
| F-051 | À faire | Établir des méthodes simples de référence | Surveillance directe et règles élémentaires évaluées |
| F-052 | À faire | Tester méthodes relationnelles et statistiques si pertinentes | Gain comparatif documenté sur les mêmes événements |
| F-053 | À faire | Créer des instantanés historiques sans fuite temporelle | Aucune information postérieure accessible pendant la prédiction |
| F-054 | À faire | Préenregistrer les jeux et la méthode d'évaluation | Périodes, fenêtres, unités et exclusions verrouillées |
| F-055 | À faire | Mesurer erreurs, omissions et avance temporelle | Précision, rappel, faux positifs et cas censurés séparés |
| F-056 | À faire | Évaluer par type d'institution et de besoin | Résultats ventilés et effectifs rapportés |
| F-057 | À faire | Conserver un registre prospectif non réécrit | Prédictions archivées avant l'issue et horodatages vérifiables |
| F-058 | À faire | Créer des alertes justifiées et révisables | Chaque signal renvoie à des preuves et une incertitude |
| F-059 | À faire | Publier le premier rapport reproductible d'anticipation | Comparaison avec référence simple et limites d'extrapolation |

### Phase 5 — Cartographie des ressources

**Horizon indicatif :** Janvier–mars 2027. **Résultat de phase :** Ressources candidates distinguées de ressources mobilisables.

| ID | État au lancement | Action | Preuve minimale d'achèvement |
| --- | --- | --- | --- |
| F-060 | À faire | Définir les catégories d'offre de capacité | Personne, équipe, établissement, laboratoire, infrastructure, service |
| F-061 | À faire | Consolider les capacités publiques explicitement publiées | Origine et limites des affirmations conservées |
| F-062 | À faire | Relier les organismes scientifiques à leurs réalisations | Projets, instruments et publications uniquement lorsqu'ils sont sourcés |
| F-063 | À faire | Étendre les ressources industrielles pertinentes | Entreprises et capacités décrites sans inventer leur disponibilité |
| F-064 | À faire | Établir des catégories techniques interopérables | Relations entre capacités et formulations de besoins documentées |
| F-065 | À faire | Créer la recherche de ressources par besoin | Résultats avec justification, sources et incertitudes |
| F-066 | À faire | Séparer pertinence, disponibilité et habilitation | Aucune mobilisabilité supposée depuis une proximité textuelle |
| F-067 | À faire | Comparer voies publiques, extérieures et mixtes | Alternatives conservées et recherche publique prioritaire |
| F-068 | À faire | Évaluer les correspondances sur cas réels relus | Pertinence et disponibilité vérifiées séparément |

### Phase 6 — Infrastructure durable

**Horizon indicatif :** Premier semestre 2027. **Résultat de phase :** Consultation durable, coûts mesurés et restauration reproductible.

| ID | État au lancement | Action | Preuve minimale d'achèvement |
| --- | --- | --- | --- |
| F-069 | À faire | Unifier les interfaces de consultation et de requête | Objets et filtres communs, index spécialisés préservés |
| F-070 | En cours | Séparer sources, projections analytiques et publications | Reconstruction possible sans modifier les archives originales |
| F-071 | À faire | Évaluer les coûts et limites de stockage hors Git | Volumes, croissance, durées et rétention mesurés |
| F-072 | En cours | Mettre en place les mises à jour différentielles | Index partiels reconstruits sans altération globale |
| F-073 | En cours | Tester des architectures de recherche publique adaptées au volume | Temps de réponse, coûts et transfert mesurés avant choix |
| F-074 | En cours | Concevoir des vues orientées utilisateurs institutionnels | Fiches, chronologies, besoins et limites de preuve consultables |
| F-075 | À faire | Publier une interface de programmation stable | Schémas, versions, pagination et provenance documentés |
| F-076 | En cours | Définir reprise sur incident et plans de continuité | Sauvegardes, restauration et surveillance testées |
| F-077 | En cours | Vérifier la publication des données et le contrôle d'accès | Licences, confidentialité, traitement des données et exclusions audités |

### Phase 7 — Validation en situation réelle

**Horizon indicatif :** À engager en parallèle dès les autorisations, jusqu'en 2027. **Résultat de phase :** Cas prospectifs, comparaison équitable et utilité effective.

| ID | État au lancement | Action | Preuve minimale d'achèvement |
| --- | --- | --- | --- |
| F-078 | À faire | Mettre à jour les registres d'entretiens déjà conduits | Constats, contre-exemples et demandes de preuves attribués |
| F-079 | À faire | Instruire la piste INRAE avec pièces et accords nécessaires | Épisodes de mobilité vérifiés sans supposer une pénurie |
| F-080 | À faire | Examiner les pistes et le rapport évoqués dans l'échange avec Jérémy | Sources et contacts contrôlés avant réutilisation comme preuves |
| F-081 | À faire | Comparer les dispositifs existants DINUM, DITP et partenaires | Contre-exemples et voies publiques recensés |
| F-082 | À faire | Ouvrir des cas prospectifs préenregistrés | État initial et méthode ordinaire fixés avant intervention |
| F-083 | À faire | Comparer les méthodes avec les mêmes données disponibles | Résultats, temps humain et contamination mesurés |
| F-084 | À faire | Mesurer première contribution et transfert durable de capacité | Effet opérationnel distinct de la découverte documentaire |

### Phase 8 — Choix institutionnel et financement

**Horizon indicatif :** Conditionnel, après premières preuves solides. **Résultat de phase :** Forme institutionnelle minimale justifiée, indépendance et financement validés.

| ID | État au lancement | Action | Preuve minimale d'achèvement |
| --- | --- | --- | --- |
| F-085 | À faire | Déterminer le périmètre de valeur réellement démontré | Périmètre de fonctionnement justifié par mesures |
| F-086 | À faire | Définir les accords et responsabilités des administrations | Décision et supervision humaines préservées |
| F-087 | À faire | Évaluer les formes juridiques envisageables | Choix soumis à expertise, aucun véhicule présumé |
| F-088 | À faire | Réviser les hypothèses du budget pluriannuel | Dépenses et ressources engagées distinguées des scénarios |
| F-089 | À faire | Formaliser indépendance et contrôle des conflits d'intérêts | Refus de financements orientant les choix garantis |
| F-090 | À faire | Sélectionner les premiers partenaires selon des preuves d'utilité | Cas, autorisations, responsabilités et limites définis |
| F-091 | À faire | Statuer sur construire, cibler, réorienter, prolonger ou arrêter | Décision datée, contradictoire et liée aux preuves |

## Ordre des premières contributions

1. **Contribution 1 — État de référence transversal** : réviser le [premier relevé documenté](ETAT_INITIAL_CHAINE_DOCUMENTAIRE_2026-10-16.md), reproduire les deux bases et les requêtes exactes, et fixer les divergences observables.
2. **Contribution 2 — File des propositions ouvertes** : analyser les huit demandes déjà ouvertes avant de produire des ajouts concurrents sur les mêmes corpus.
3. **Contribution 3 — Archives → index → consultation** : comparer les manifestes, les documents effectivement indexés, les plafonds du site et le déploiement Render.
4. **Contribution 4 — Dossiers institutionnels** : définir la relation sourcée organisme–événement–projet–capacité et construire un petit lot de chronologies avec évaluation indépendante.
5. **Contribution 5 — Registre des besoins** : qualifier des pièces primaires, conserver les contre-exemples et séparer systématiquement demandes, ressources et déficits démontrés.

## Indicateurs de progrès

Déclarer séparément : couverture par source et période, retard de collecte, intégrité des archives, précision des identités, qualité des chronologies, proportion de besoins qualifiés sur pièces primaires, erreurs d'anticipation, mobilisation effective, délai jusqu'à première contribution, effort humain et connaissances réellement réutilisées. Tous les dénominateurs et périodes doivent être publiés avec la mesure.

## Documents associés

- [Journal des revues et changements d'état](SUIVI_FEUILLE_ROUTE.md)
- [Premier relevé transversal du 16 octobre](ETAT_INITIAL_CHAINE_DOCUMENTAIRE_2026-10-16.md)
- [Protocole d'exécution scientifique](PROTOCOLE_V1.1.md)
- [Évaluation technique](EVALUATION_TECHNIQUE_V0.5.md)
- [Architecture](ARCHITECTURE.md)
- [État empirique](ETAT_DU_PROJET.md)
- [Contrôle transversal de veille](CONTROLE_VEILLE_ET_INTEGRATION_V1.md)

_Le document reflète l'état des éléments contrôlés au lancement, non une validation globale de chacun des 91 jalons._
