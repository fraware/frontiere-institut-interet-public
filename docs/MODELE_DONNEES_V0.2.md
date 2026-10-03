# Modèle de données canonique v0.2

## Chaîne

`Épisode → Besoin → Exigence de capacité → Source → Ressource → Correspondance → Recherche → Décision → Frictions → Résultat → Connaissance → Réutilisation`

## Entités principales

### Organisation
Identité institutionnelle minimale. Les unités fines restent dans l'épisode au démarrage.

### Épisode
Identité stable du cas. Contient code, organisation, statut opératoire, D0–D4, sensibilité, caractère historique/actuel/récurrent, préexistence à Frontière et marqueur synthétique.

### Version du besoin
La formulation du besoin est versionnée. Une modification substantielle produit une nouvelle version et conserve l'ancienne.

### Capacité / exigence de capacité
La capacité est une classe réutilisable. L'exigence associe une capacité à un besoin avec profondeur, contexte, contraintes et méthode de vérification.

### Preuve
Document, donnée ou témoignage avec source, date, niveau A–E, sensibilité et environnement de données.

### Ressource
Personne, équipe, laboratoire, organisme, prestataire, communauté, outil, donnée, document, modèle, service, procédure ou autre.

### Recherche / découverte
Une exécution de recherche conserve méthode, type, dates, temps analyste et résultat. Une ressource découverte par plusieurs méthodes garde une seule identité et plusieurs découvertes.

### Voie évaluée
Une option de résolution conserve statut initial, statut courant, preuves favorables et défavorables, blocage et prochaine action.

### Décision
Conserve option choisie, options examinées, justification, éléments contradictoires, incertitudes, confiance, auteur et date.

### Friction
Événement temporel avec catégorie, sous-catégorie, début/fin, responsable, dépendance, caractère bloquant/évitable et raison.

### Résultat
Issue, intervention réelle, voie réelle, première contribution utile, coûts, temps et additionalité par dimensions.

### Connaissance / réutilisation
Une connaissance issue d'un épisode est enregistrée indépendamment de l'analyste qui l'a créée et reliée aux épisodes ultérieurs qui l'utilisent.

### Hypothèse de plateforme
Quinze hypothèses pré-enregistrées, avec critères de renforcement et d'affaiblissement et statut humainement revu.

## Invariants

1. Un épisode possède au plus une version active du besoin.
2. D0–D4 restent distincts de l'état opératoire de l'épisode.
3. Une recherche insuffisante produit P0.
4. Une capacité publique pertinente trouvée mais non mobilisable produit P2, pas P3.
5. R5 est spécifique à un besoin et une période.
6. Une connaissance synthétique n'alimente pas les métriques réelles.
7. Les éléments contradictoires font partie du dossier de décision.
8. Une disponibilité périmée doit être revalidée.
9. Les processus parallèles de friction ne sont pas additionnés comme délai total.
10. Une solution existante suffisante constitue un résultat valide.
