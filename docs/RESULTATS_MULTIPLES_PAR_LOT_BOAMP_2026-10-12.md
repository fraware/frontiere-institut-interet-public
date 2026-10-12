# Plusieurs décisions eForms pour le même lot

L'ensemble ciblé de 24 avis a été collecté dans [l'exécution officielle n° 38200661719](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38200661719). Les 24 réponses sont archivées avec leurs empreintes SHA-256. Le relevé initial contient 17 avis sans résultat d'attribution dans la notice lue, 3 attributions eForms interprétées, 3 attributions textuelles FNSimple et un formulaire eForms non interprété.

Les trois avis eForms interprétés décrivent **quatre lots attribués** et **deux lots non attribués pour un autre motif**. Aucun lot ne porte le motif `no-rece` (aucune offre reçue).

L'avis `26-60672` (GHT Aude-Pyrénées, transports de patients) possède trois nœuds `efac:LotResult`, tous rattachés à `LOT-0001`, avec le code `selec-w`. Ils indiquent trois références contractuelles distinctes `CON-0001`, `CON-0003` et `CON-0002`. Le code `tenders` déclare la valeur 3 dans chacune de ces décisions.

**Règle de regroupement :** ces nœuds représentent un lot avec trois décisions d'attribution, non trois lots. Leur nombre d'offres n'est pas 3 + 3 + 3. La procédure retient une mesure par code compatible et conserve tous les chemins de provenance, les trois contrats et les trois enregistrements d'origine.

Les discordances de statut, de motif, de mesure ou de références contractuelles entraînent un refus du regroupement ; aucune donnée contradictoire ne se transforme en étiquette certaine.

Les effectifs corrigés demeurent **en attente d'une exécution réelle** après le changement de code. Les causes des consultations infructueuses et les diagnostics de capacité ne sont pas établis à partir de ce corpus de titres volontairement enrichi.

L'échantillon de 36 avis conserve son empreinte et son protocole distinct. Aucun effet sur la disponibilité de compétences ou la première contribution utile n'est démontré.
