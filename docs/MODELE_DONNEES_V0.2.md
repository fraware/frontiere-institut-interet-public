# Modèle de données — version 0.2

## Vue d'ensemble

L'application relie les objets suivants :

`Cas → Besoin → Capacité nécessaire → Source → Ressource → Recherche → Voie de résolution → Décision → Délais et obstacles → Résultat → Connaissance → Réutilisation`

## Cas

Le cas représente une situation réelle et délimitée dans le temps. Il conserve l'organisation concernée, le besoin, son état d'avancement, sa sensibilité et son caractère réel ou de démonstration.

## Version du besoin

Le besoin peut évoluer à mesure que de nouvelles informations apparaissent. Chaque changement important crée une nouvelle version ; l'ancienne reste consultable.

## Capacité nécessaire

La capacité décrit ce qu'il faut savoir faire pour résoudre le problème. Elle comprend le domaine, la fonction attendue, le niveau de profondeur, le contexte et les contraintes.

## Preuve

Une preuve est un document, une donnée ou un témoignage. Elle conserve sa source, sa date, sa qualité, son niveau de sensibilité et l'environnement dans lequel elle peut être utilisée.

## Ressource

Une ressource peut être une personne, une équipe, un laboratoire, un organisme, un prestataire, un réseau, un outil, une donnée, un document, un modèle, un service, une procédure ou une infrastructure.

## Recherche

Une recherche conserve la méthode utilisée, les dates, le temps consacré et les ressources trouvées. Une même ressource trouvée par plusieurs méthodes reste une seule ressource, reliée à plusieurs recherches.

## Voie de résolution

Une voie décrit une manière concrète de résoudre le besoin : utiliser une capacité publique existante, organiser une expertise ponctuelle, créer une coopération scientifique, recruter, acheter une prestation, former une équipe ou utiliser un autre mécanisme adapté.

Chaque voie conserve les éléments favorables, les éléments défavorables, les inconnues, les conditions bloquantes et la prochaine action.

## Décision

La décision conserve l'option retenue, les autres options examinées, la justification, les éléments contradictoires, les incertitudes, l'auteur et la date.

## Délais et obstacles

Chaque délai important est enregistré séparément avec son début, sa fin, son responsable, ses dépendances et son caractère bloquant ou non.

## Résultat

Le résultat décrit ce qui s'est réellement passé : solution utilisée, première contribution utile, coût, temps consacré et valeur ajoutée observée.

## Connaissance réutilisable

Une connaissance peut être une source utile, une capacité, une ressource, une voie, un délai typique, une règle ou un précédent. Elle est reliée aux cas futurs qui l'utilisent réellement.

## Règles essentielles

1. Un cas ne possède qu'une seule version active du besoin.
2. Une recherche incomplète ne permet pas de conclure qu'aucune capacité publique n'existe.
3. Une capacité publique trouvée mais difficile à mobiliser n'est pas assimilée à une absence de capacité.
4. Une ressource n'est considérée mobilisable que pour un besoin précis et une période précise.
5. Une disponibilité ancienne doit être confirmée avant usage.
6. Les cas de démonstration ne sont jamais comptés comme observations réelles.
7. Les preuves contradictoires restent dans le dossier.
8. Les délais parallèles ne sont pas additionnés comme s'ils étaient successifs.
9. Une solution existante suffisante constitue un résultat valable.
