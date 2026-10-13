# Première ingestion expérimentale des enregistrements de marchés DECP — JSON

## Fondement documentaire

Les textes français applicables depuis le 1er janvier 2024 définissent notamment l'identifiant du marché, l'identifiant de l'acheteur, l'objet, le code commun des marchés, la date de notification et la publication des données essentielles. Les structures sont décrites dans le [schéma national de données 2.0](https://schema.data.gouv.fr/139bercy/format-commande-publique/2.0.0/) et dans l'[annexe de l'arrêté du 22 décembre 2022](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000048876441).

Le [dépôt officiel du format](https://github.com/139bercy/format-commande-publique) contient des exemples avec `{"marches":{"marche":[...]}}`, tandis que le schéma JSON décrit `{"marches":[...]}`. **La première ressource AIFE réellement téléchargée le 13 octobre 2026 présente deux collections à l’intérieur de `marches` : `marche` et `contrat-concession`.** L’importateur prend désormais en charge cet ensemble, quel que soit l’ordre des deux collections, ainsi que les tableaux racines. Il compte les concessions séparément sans les qualifier comme marchés. Les formes inconnues sont refusées.

**L'origine des champs normalisés est réglementaire ; le traitement fourni ne constitue pas une vérification complète de conformité à ce schéma.** Une vérification normative ultérieure devra appliquer la version du schéma correspondant à chaque fichier et isoler les concessions.

## Livrables techniques

- `scripts/ingerer_fichier_decp_json.py` : lecture incrémentale d'un tableau de notices JSON, sans charger la liste entière en mémoire ; contrôle de la taille du fichier (16 Mo), de chaque notice (deux millions de caractères), du nombre maximal de notices (50 000) et des extraits conservés (200 au plus).
- Contrôle du couple **SIRET de l'acheteur + identifiant du marché**, de l'objet, du code CPV, des dates calendaires et des valeurs numériques. Les rejets sont comptés par motif. Les doublons exacts et les conflits de versions dans un même fichier sont comptés **séparément** ; les différences ne sont pas masquées par la conservation de la première occurrence.
- Conservation de l'empreinte SHA-256 du fichier brut, de l'identifiant de ressource et du catalogue, des comptes de lignes et des 50 ou 200 premiers enregistrements normalisés.
- `scripts/sonder_ressource_decp_aife.py` : sélection d'un seul fichier JSON récent déjà recensé dans l'inventaire AIFE, vérification de son identifiant dans la fiche officielle, de sa taille déclarée et de l'origine de son URL. Téléchargement plafonné à 1,5 Mo sur des domaines publics explicitement autorisés. Les autres fichiers ne sont pas sollicités.
- `institutionnel/decp/sonde_aife_json.json` : **sortie de collecte**, publiée seulement si une requête réelle et les vérifications réussissent.

## Exécution

Pour analyser un fichier JSON déjà obtenu de façon licite et vérifier son origine :

```bash
python scripts/ingerer_fichier_decp_json.py \
  --entree /chemin/vers/un-fichier-decp.json \
  --source aife_api_decp \
  --ressource-id db50f1f1-9fe5-4f9e-93dd-d273617d4a26 \
  --sortie /tmp/bilan-decp.json --extraits 50

python -m pytest -q \
  tests/test_ingerer_fichier_decp_json.py \
  tests/test_sonder_ressource_decp_aife.py
```

La sonde distante, exécutée uniquement sur une machine autorisée à accéder aux ressources :

```bash
python scripts/sonder_ressource_decp_aife.py
```

Elle échoue sans produire de nouvelle sortie si les ressources officielles ne sont pas consultables, si le domaine de stockage n'est pas autorisé, si la taille diverge ou si le fichier ne respecte pas les enveloppes reconnues. Un diagnostic de forme limité aux noms et types de champs accompagne les refus, sans journaliser de texte contractuel. Il n'existe pas de contournement automatique d'un refus d'accès.


## Surveillance récurrente du prélèvement

La première ingestion réelle du fichier AIFE a réussi avec **127 marchés normalisés**, **une concession** comptée distinctement et **zéro rejet** sur les champs du profil réduit.

La procédure `.github/workflows/sonde-decp-json.yml` est désormais prévue quatre fois par jour à **03:23, 09:23, 15:23 et 21:23 UTC**, sous réserve des décalages d'ordonnancement GitHub Actions. À chaque cycle, elle interroge uniquement le catalogue AIFE et télécharge au plus un petit fichier JSON déjà référencé, de taille strictement limitée.

Le programme compare l'ensemble des résultats normalisés à la version enregistrée, sans tenir compte de la seule heure du nouveau contrôle. **Un cycle identique ne crée pas de proposition de modification supplémentaire.** Toute modification du contenu, de l'empreinte ou des compteurs devra passer les contrôles et une nouvelle publication.

Cette cadence concerne uniquement **la sonde d'un fichier récent**, et ne représente ni une ingestion exhaustive des publications AIFE ni la détection en temps réel de toutes les opérations d'achat. La mise en place d'un curseur parcourant chaque nouvelle ressource depuis le dernier passage est nécessaire pour évoluer vers une couverture temporelle vérifiable.

## Limites empiriques

Une donnée de marché attribué ne signifie pas que le besoin est encore ouvert. L'attribution n'atteste pas la livraison ni la première contribution du prestataire. Le rattachement d'une annonce BOAMP à une attribution DECP demeure **non établi** à ce stade : les identifiants de marchés, d'acheteurs et de procédures doivent être rapprochés sur des critères vérifiables.

Cette première ingestion ne couvre **ni l'ensemble des fichiers JSON, ni les 5 000 fichiers XML DGFiP, ni le fichier consolidé de plusieurs gigaoctets**. Ces volumes demanderont le traitement XML en flux, une mémoire persistante externe et une politique explicite de mise à jour des versions.

Les exemples et les tests vérifient des propriétés logicielles ; seul un relevé réellement exécuté dans GitHub sur une ressource officielle pourra établir le nombre de notices présentes et prises en charge. La réussite de cette première sonde sera analysée séparément de la réussite du programme sur des données d'essai.
