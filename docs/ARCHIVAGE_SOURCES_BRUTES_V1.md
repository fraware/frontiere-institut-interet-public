# Conservation locale des sources brutes — outil expérimental

L'outil `scripts/archiver_source_brute.py` conserve les **octets exacts** d'un export public, y compris un fichier binaire volumineux. Chaque objet est rangé sous une adresse calculée par SHA-256 ; chaque capture possède une fiche distincte, liée cryptographiquement à l'objet, décrivant la source, sa date de capture **déclarée**, son éventuelle étiquette HTTP et sa licence déclarée.

## Utilisation isolée

Dans un répertoire privé, extérieur au dépôt public, avec Python 3.11 ou ultérieur :

```bash
python scripts/archiver_source_brute.py archiver \
  --archive /chemin/prive/archive \
  --fichier /chemin/prive/export-public.bin \
  --source-id dila_annuaire_local \
  --url https://example.org/source-publique \
  --licence "Licence Ouverte 2.0" \
  --observe-le 2026-10-08T12:00:00Z

python scripts/archiver_source_brute.py verifier \
  --archive /chemin/prive/archive --capture EMPREINTE_SHA256_DE_LA_CAPTURE

python scripts/archiver_source_brute.py restaurer \
  --archive /chemin/prive/archive --capture EMPREINTE_SHA256_DE_LA_CAPTURE \
  --destination /chemin/prive/copier-export-public.bin
```

`example.org` est un exemple fictif. Remplacer l'adresse, la date et la licence par les valeurs réellement documentées lors d'une capture. L'outil ne télécharge rien et n'obtient aucun en-tête HTTP lui-même.

Une fiche de capture comprend une empreinte des octets, leur nombre et un chemin canonique. Deux captures aux métadonnées différentes peuvent désigner les mêmes octets. La commande `verifier` examine à nouveau les octets et détecte leur altération. La restauration refuse de remplacer un fichier existant. La copie s'effectue par blocs, sans charger entièrement l'export en mémoire.

## Ce qui est établi et ce qui ne l'est pas

- **Établi par les contrôles techniques :** empreinte et longueur des octets archivés, cohérence de la fiche et récupération binaire des octets.
- **Déclaré, non certifié :** identité et URL du serveur source, date effective de capture, licence, éventuel ETag et date de dernière modification. Ces champs doivent provenir du journal d'ingestion conservé séparément.
- **Non établi :** absence de transformation avant archivage, antériorité indépendante, immuabilité face aux administrateurs locaux, conservation légale et capacité de restauration après perte du disque.

La publication atomique et le refus de remplacement préviennent des écrasements accidentels ; **il ne s'agit pas d'un stockage à rétention verrouillée**. Le caractère public d'un export et le droit de le conserver doivent être vérifiés en amont. Les secrets et les dossiers institutionnels sensibles sont exclus.

## Transition nécessaire avant de clôturer le ticket n° 49

1. Choisir et approvisionner un espace distant distinct, avec verrouillage effectif à durée définie, contrôle d'accès minimal et politique de conservation conforme aux droits de réutilisation.
2. Intégrer l'archivage dans les quatre collectes principales *immédiatement après réception des octets bruts et avant leur transformation*. Le scénario actuel ne branche pas encore automatiquement les importeurs sur cet outil.
3. Faire écrire l'identifiant de capture et l'empreinte brute dans le manifeste canonique versionné, puis contrôler la concordance entre transport brut et transformation.
4. Tester la restauration depuis le lieu de conservation indépendant, la détection de corruption, les rotations de droits, les échecs de dépôt et l'absence de suppression durant la durée de rétention.
5. Préserver les versions historiques non archivées comme **non attestées par cette nouvelle procédure**. Ne pas reconstruire rétroactivement de fausses captures.

Aucune source réelle n'est archivée dans cette livraison. Les essais utilisent exclusivement des octets inventés. Le ticket n° 49 reste ouvert.
