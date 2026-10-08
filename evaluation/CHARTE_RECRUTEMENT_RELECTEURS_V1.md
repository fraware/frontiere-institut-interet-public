# Charte de recrutement et de lancement — relecture des chronologies historiques

**Version 1 — 8 octobre 2026.** Ce texte transforme le protocole de relecture documentaire en conditions explicites de recrutement, de confidentialité et de lancement. Il ne désigne aucun relecteur, ne prouve aucune indépendance et ne préjuge d'aucun jugement.

## 1. Périmètre précis de la mission

La mission porte sur les **45 événements documentaires** du corpus courant, répartis entre dix chronologies historiques. Pour chacun, le responsable remet une assertion, sa date et sa précision déclarées, ainsi qu'une ou plusieurs pièces officielles candidates et une localisation de lecture.

Chaque relecteur examine séparément quatre questions : le document proposé est-il retrouvé ? Étaye-t-il le fait ? Étaye-t-il la date ? La précision temporelle de la chronologie est-elle justifiée ? Les valeurs sont **OUI, NON, INDETERMINE**, avec justification libre et passage effectivement consulté si la pièce est accessible.

Le travail vise la **validité documentaire et chronologique**. Il n'évalue ni la représentativité nationale du corpus, ni l'utilité opérationnelle de FRONTIÈRE, ni les dix cas réservés H01–H10. Le budget et le calendrier de la mission ne sont pas encore arrêtés.

## 2. Recrutement, rôles et indépendance

Le responsable de l'étude recrute **deux lecteurs distincts** possédant une expérience vérifiable en recherche documentaire, examen critique de rapports administratifs, méthodes des sciences sociales, documentation de données ou évaluation des politiques publiques. Lorsque possible, ils appartiennent à **deux organisations différentes**, afin de réduire le risque de dépendance des jugements.

Avant confirmation de chaque participation, recueillir dans un dossier privé :

- fonction, institution, domaine de compétence, expérience concrète pertinente, disponibilité et conditions éventuelles de rémunération ;
- liens antérieurs avec FRONTIÈRE ou Horizon France, ses contributeurs, ses promoteurs ou son financement ;
- participation à la constitution des dix chronologies, à la rédaction ou la consultation des notes de provenance et aux modifications du dépôt ;
- implication professionnelle récente ou intérêt significatif dans les organismes concernés par les dix dossiers historiques ;
- éventuelle connaissance préalable des 45 événements, de leurs sources ou des interprétations proposées ;
- engagement à produire ses jugements seul, avant toute communication avec l'autre lecteur ou consultation de ses réponses.

Une appartenance institutionnelle différente est un **indice de séparation organisationnelle**, non une garantie d'indépendance intellectuelle. Le responsable documente les risques résiduels, retire ou remplace les candidats exposés aux références ou ayant contribué au corpus, et évite les conflits d'intérêts sur les dossiers concernés.

Les noms, adresses, déclarations de conflits et conditions financières des candidats ne sont pas inscrits dans le dépôt public sans consentement explicite.

## 3. Sélection progressive

**Premier message.** Décrire un contrôle documentaire indépendant de 45 assertions tirées de dix chronologies publiques, les critères à examiner, l'absence d'obligation d'approuver le corpus, les modalités de travail séparées et l'existence éventuelle d'une rémunération *à définir*. Demander une orientation vers une personne compétente et disponible. Ne pas présenter la mission comme une simple validation de travail déjà jugé correct.

**Préqualification.** Évaluer la compétence en critique des sources administratives, dater les événements, reconnaître des informations insuffisantes et expliciter les limites. Vérifier la connaissance antérieure du corpus. Le candidat reçoit une présentation exacte du commanditaire et des règles d'indépendance ; si cela révèle une exposition antérieure, consigner cette exposition au lieu de présenter l'examen comme aveugle.

**Accord de mission.** Fixer avant toute séance l'effort attendu, les moyens de consultation, la politique d'indemnisation le cas échéant, les échéances, les possibilités de retrait et la propriété des livrables. Ne pas supposer une participation bénévole ni annoncer une enveloppe non financée.

**Contrôle préalable de l'outil.** Tester les fichiers et consignes sur un corpus artificiel ou de développement, hors des 45 événements définitifs ; corriger les problèmes de compréhension *avant* l'enregistrement du manifeste final. Aucun temps estimé obtenu après consultation des 45 faits ne doit être présenté comme un étalonnage antérieur.

## 4. Intégrité et ordre des opérations

1. Vérifier l'état de la branche principale, la version des chronologies et les scripts de contrôle ; conserver l'identifiant du commit.
2. Arrêter par écrit les règles d'examen, les critères de conflit, la procédure d'arbitrage et le plan de diffusion avant le premier avis.
3. Exécuter `scripts/preparer_relecture_evenements.py` **hors du dépôt public** avec `registre_verification_evenements_v7.json` et `passages_sources_evenements_v6.json`. Vérifier les deux paquets identiques, les 45 avis vierges par personne et les empreintes.
4. Faire déposer le manifeste et son empreinte auprès d'un tiers ou d'un dispositif d'horodatage indépendant, puis distribuer les paquets séparément. L'empreinte locale ne constitue pas une attestation d'antériorité.
5. Recevoir les deux fichiers individuels, les conserver intègres et faire attester leurs empreintes **avant** toute discussion conjointe.
6. Exécuter `scripts/consolider_relecture_evenements.py` hors du dépôt public ; conserver l'intégralité des jugements et des divergences. La consolidation ne produit pas de consensus.
7. Si un arbitrage est nécessaire, faire rédiger une décision distincte, datée et motivée, en conservant les deux versions initiales.

Ces fichiers contiennent les sources candidates et leur emplacement, mais **pas** les appréciations de l'assistant. Il s'agit donc d'une indépendance des *jugements*, pas d'une découverte indépendante des sources. Toute connaissance préalable doit être consignée. Une investigation séparée sur la capacité à retrouver les pièces à partir du seul fait constituerait une expérience différente, à préenregistrer distinctement.

## 5. Conditions minimales de preuve

Le responsable ne déclarera l'étude achevée que si les deux personnes ont effectivement rendu leurs avis, avec identités et indépendance évaluées, réponses complètes, justifications, horodatages externes du gel, comparaisons calculées sur les mêmes événements et divergences préservées.

Il publiera les effectifs exacts de pièces retrouvées, de faits étayés, non étayés et indéterminés ; la part des dates et précisions justifiées ; les accords par dimension, les désaccords individuels et les réserves de méthode. Les avis non vérifiés ne sont pas comptés comme des preuves établies.

Une couverture de 45 événements par des sources candidates, des réponses concordantes ou une réussite des tests de programmation **ne prouve pas** la valeur ajoutée de FRONTIÈRE pour les administrations.

## 6. Séparation des autres campagnes

La comparaison H01–H10 possède son propre dispositif d'étude, trois opérateurs de méthode et un détenteur des références privées. Les lecteurs historiques ne doivent pas accéder à ces références. Si une même personne se voit proposer plusieurs rôles, le responsable évalue et consigne le risque de contamination avant de l'autoriser.

Les quatre demandes d'exécution concernant France Compétences, la DDTM des Côtes-d'Armor, l'ASNR et l'IGN relèvent du protocole de collecte institutionnelle. Leur envoi et leur réception sont consignés séparément, sans modifier les chronologies historiques de manière silencieuse.

**Documents de référence :** `evaluation/PROTOCOLE_RELECTURE_SOURCES_HISTORIQUES_V1.md`, `evaluation/PROTOCOLE_SESSIONS_INDEPENDANTES_V1.md`, `docs/EXECUTION_TERRAIN_V1.md`, tâches n° 84 et n° 63.
