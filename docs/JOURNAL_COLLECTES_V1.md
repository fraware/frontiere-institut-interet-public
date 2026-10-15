# FRONTIÈRE — Journal d'exécution des collecteurs

L'hébergement géré intègre un journal SQLite autonome sous
\`/var/lib/frontiere/exploitation/passages.sqlite3\`. Il décrit **l'activité
réelle des commandes de collecte**, indépendante des dates de publication
et des versions documentaires observées.

Pour chaque amorçage et chaque cycle des cinq collecteurs, le registre
conserve la source, l'heure de démarrage, l'heure de fin, l'état
(\`en_cours\`, \`reussite\`, \`echec\`, \`interrompu\`), le code de sortie
et le type éventuel d'erreur. Il ne conserve pas les messages des
exceptions, qui pourraient inclure des détails sensibles.

La consultation privée \`GET /collectes\` expose les derniers passages,
la dernière réussite de chaque source et le nombre d'échecs consignés.
Sur Render, elle utilise le même jeton obligatoire que les autres routes
de consultation.

    curl -H "Authorization: Bearer VOTRE_JETON" \
      "https://VOTRE_SERVICE.onrender.com/collectes"

Une base absente produit \`non_configure\` et n'est jamais créée par une
lecture. Une panne de l'outil de journalisation est signalée sur la sortie
du service sans empêcher la collecte elle-même.

## Interprétation

Un état \`reussite\` signifie que le programme du collecteur a rendu un
code de sortie nul. **Ce n'est pas une preuve de couverture nationale ni
de disponibilité de toutes les ressources**. Certains collecteurs
renvoient un succès de processus avec des erreurs partielles de source,
signalées dans leurs bilans détaillés sur la sortie standard.

Une exécution interrompue sans procédure de terminaison laisse son
enregistrement \`en_cours\` dans la base. Cet état est historique et ne
doit pas être présenté automatiquement comme un traitement encore actif.
La prochaine évolution rapprochera les journaux de passage des rapports
de collecte pour compter séparément les sources effectivement interrogées
et les ressources importées.

Les fichiers d'acquisition et les données d'origine continuent à être
conservés dans leurs bases respectives ; cette table constitue uniquement
le journal d'exploitation.
