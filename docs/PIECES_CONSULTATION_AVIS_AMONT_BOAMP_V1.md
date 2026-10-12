# Pièces de consultation et avis amont BOAMP — méthode v1

**Périmètre :** les six notices pilotes, l'avis initial Tisséo et deux annonces antérieures candidates. Aucun contact, aucune authentification et aucune pièce confidentielle ne sont inclus.

## Avis antérieurs candidats

| Avis | Date BOAMP | Avis de comparaison | Référence interne commune attendue |
| --- | --- | --- | --- |
| 24-119544 | 18 octobre 2024 | Météo-France 26-74896 (attribution 2026) | METEOFRANCE2432F0342 |
| 26-55633 | 7 juin 2026 | Tisséo 26-81640 (appel d'offres initial) | M3202604147M |

Les pistes sont enregistrées avant l'exécution dans `evaluation/avis_amont_cibles_boamp_v1.json`.

Source officielle Météo-France : https://www.boamp.fr/telechargements/FILES/PDF/2024/10/24-119544.pdf

Source du portail officiel Tisséo : https://tisseo.marches-publics.info/avis/index.cfm?IDS=4210&fuseaction=pub.affPublication&refPub=MPI-pub-20261581295&serveur=MPI

Le collecteur doit vérifier chaque réponse intégrale de la DILA, l'identifiant, la date, la concordance de l'acheteur et la référence interne du marché dans les deux formulaires officiels. Une référence interne commune atteste une concordance documentaire : elle ne démontre pas à elle seule l'identité des numéros de procédure européens, la continuité juridique, l'exécution ou la cause des délais.

L'avis périodique indicatif Tisséo prévoit un lancement le 8 juillet 2026 ; la consultation initiale conservée paraît le 20 août 2026. L'écart oppose **une date prévisionnelle à une publication observée**. Il ne démontre aucune pénurie ou difficulté de mobilisation.

## Inventaire reproductible des références de pièces

Le programme `scripts/inventorier_pieces_consultation_boamp.py `analyse les formulaires officiels intégralement archivés et relève exclusivement les champs `cac:CallForTendersDocumentReference`, avec leur chemin JSON, identifiant déclaré, adresse littérale et adresse dont les entités HTML sont décodées.

Une page générique d'acheteur ne devient jamais une référence de dossier de consultation. Une adresse de dossier est enregistrée comme **lien cité dans l'avis**, et jamais comme **pièce téléchargée ou vérifiée**. Le programme ne suit aucun lien, ne contourne aucune connexion et ne collecte aucune annexe confidentielle.

Le formulaire source Tisséo mentionne un dossier portant l'identifiant 1862843, sur www.marches-publics.info.

Source de consultation : https://www.marches-publics.info/mpiaws/index.cfm?fuseaction=dematEnt.login&type=DCE&IDM=1862843

Le portail du dossier requiert une étape de retrait ou d'identification et indique une vérification. Son avis public rappelle qu'une annexe confidentielle est communiquée sous accord de confidentialité. Cette annexe demeure exclue. Les quatre prestations annoncées portent sur l'architecture, la configuration, l'organisation et la sécurité physique, et les tests d'intrusion. Les exigences PASSI et les références industrielles décrivent la qualification des prestataires, sans démontrer leur disponibilité réelle.

Portail public Tisséo : https://tisseo.marches-publics.info/avis/index.cfm?IDS=4210&fuseaction=pub.affPublication&refPub=MPI-pub-2026232874&serveur=MPI

Une page publique PLACE de Météo-France confirme la référence METEO-FRANCE2432F0342, une limite de remise au 28 novembre 2024 et un projet de renouvellement de capacité de calcul intensif.

Source : https://www.marches-publics.gouv.fr/index.php?id=2636711&orgAcronyme=d4t&page=Entreprise.EntrepriseDemandeTelechargementDce

## Exécution, contrôle et limites

Le collecteur utilise les archives déjà vérifiées des six cas pilotes et de leur avis explicitement lié. Chaque réponse amont est conservée avec empreinte SHA-256, adresse exacte et horodatage. Une réponse absente produit un inconnu. Si la date officielle diffère du registre, les octets et la date observée sont archivés sous le statut **date_officielle_divergente**, sans qualifier la correspondance de marché ; l'avis est exclu de l'inventaire des références documentaires validées. Les autres contradictions d'identité, de structure, d'acheteur ou de référence interne bloquent la capture entière. La divergence doit être vérifiée sur sa source primaire avant toute correction versionnée du registre.

Le programme d'inventaire conserve des indicateurs distincts : contenu des pièces obtenu, procès-verbal de réception obtenu et première utilisation scientifique documentée. Ces valeurs sont **fausses** jusqu'à examen d'une preuve primaire correspondante.

Le prochain seuil scientifique est la récupération et la vérification de pièces publiques authentiques, puis de sources démontrant livraison, réception ou utilisation effective. Les annonces et les dates de marché sont insuffisantes pour mesurer le délai entre le besoin et la première contribution utile.


## Révision datée du registre — version 2

Le relevé du 11 octobre 2026, exécution [38186268810](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38186268810), archive [11720150455](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38186268810/artifacts/11720150455), confirme une divergence pour **Météo-France 24-119544** : document PDF daté du 18 octobre 2024 ; champ de parution du jeu DILA daté du **20 octobre 2024**. La réponse conservée possède l'empreinte SHA-256 `b0f582826fe0acf87b1f1b0a2eff7b8ee06e7133e960887c7db761d38cbf82c4`. L'avis Tisséo 26-55633 du 7 juin 2026 concorde avec le formulaire de l'appel d'offres initial par référence interne et acheteur.

Le registre initial `evaluation/avis_amont_cibles_boamp_v1.json` est conservé sans modification. Le nouveau registre `evaluation/avis_amont_cibles_boamp_v2.json` contient la date de parution DILA pour Météo-France, conserve la date du PDF, documente la raison et référence la preuve archivée. La procédure active utilise v2. Les deux versions et les archives restent séparées.

Le premier inventaire comporte neuf avis, dont **cinq avec une adresse inscrite dans un champ officiel de référence documentaire** ; certains liens pointent seulement vers des portails génériques. Le schéma distingue maintenant `lien_portail_generique` et `lien_dossier_consultation_identifie`. La deuxième catégorie est reconnue de façon conservatrice uniquement quand l'adresse sur `www.marches-publics.info` fournit un paramètre DCE avec identifiant numérique IDM. La règle n'établit aucune disponibilité des fichiers sous-jacents.

La référence d'un dossier DCE, son contenu réellement téléchargé, une réception contractuelle et une première utilisation scientifique constituent quatre niveaux de preuve distincts. Aucun des trois derniers n'est attesté par ce cycle.
