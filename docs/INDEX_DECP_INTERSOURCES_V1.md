# Index documentaire commun des marchés AIFE et DGFiP

## Objet et unité d'observation

Cet index rapproche les **marchés attribués publiés dans les fichiers DECP**, issus de deux circuits distincts : le fichier JSON observé de l'AIFE et les ressources XML du PES Marché DGFiP déjà archivées. La clé de déduplication est **(SIRET de l'acheteur, identifiant du marché)**. Elle constitue une identité documentaire opérationnelle, et non une preuve d'identité juridique parfaite dans toutes les situations.

Une même clé peut figurer plusieurs fois : soit avec un contenu normalisé identique, soit sous des **variantes documentaires** différentes. Ces variantes sont conservées distinctement, avec leur ressource d'origine. Un changement d'objet ou de montant n'est pas qualifié automatiquement d'avenant, de correction officielle ou d'une seconde commande.

## Exécution

```bash
python scripts/consolider_attributions_decp.py \
  --aife institutionnel/decp/sonde_aife_json.json \
  --dgfip institutionnel/decp/lot_dgfip_xml.json \
  --base /tmp/frontiere-decp.sqlite3 \
  --rapport /tmp/frontiere-decp-bilan.json

python scripts/indexer_attributions_decp_sqlite.py rechercher \
  --base /tmp/frontiere-decp.sqlite3 --expression "scientifique"

python -m pytest -q \
  tests/test_indexer_attributions_decp_sqlite.py \
  tests/test_consolider_attributions_decp.py
```

Le programme reconstruit localement l'ensemble du fichier SQLite en appliquant la même structure de tables d'identités, versions, fichiers et attestations déjà employée pour les relevés AIFE. Une recherche plein texte FTS5 est disponible dans la base créée. Aucun compte ni service distant n'est nécessaire.

## Conditions de publication et limites

La reconstruction échoue si une source ne respecte pas le profil d'extraction connu, si une ressource XML est tronquée, si une identité ou une date indispensable est invalide, ou si la correspondance entre nombre de marchés normalisés et notices conservées est incohérente. La base antérieure reste alors inchangée. Les contrôles d'intégrité SQLite et des clés étrangères sont exécutés avant le remplacement du fichier.

Le bilan distingue explicitement les nombres d'enregistrements par fichier, d'identités distinctes, de variantes normalisées, de répétitions de variantes identiques, de fichiers sources et d'attestations. Il conserve aussi les empreintes SHA-256 des deux **relevés publiés** utilisés pour reconstruire la base, en plus des empreintes de fichiers bruts déjà relevées par les collecteurs.

**Attention aux différences de preuve.** Les fichiers bruts officiels ne sont pas téléchargés à nouveau par cet indexeur. L'intégrité des relevés archivés est calculable ; l'empreinte déclarée d'un fichier source n'est pas recoupée à nouveau avec le site émetteur pendant cette opération. La conformité réglementaire complète et la couverture nationale ne sont pas établies.

La base traite uniquement les fichiers présents dans le registre, sans prétendre connaître tous les marchés du pays. Aucun appariement BOAMP n'est encore attesté et aucune attribution n'est assimilée à un besoin encore ouvert. Le rapprochement des avis de publicité et des marchés attribués constitue une opération ultérieure, avec preuves de correspondance et traitement des ambiguïtés.

L'index SQLite est **reconstruit localement** et ne figure pas parmi les fichiers institutionnels versionnés. Le code et les relevés sources suffisent à le reproduire tant que les versions de Python et SQLite utilisées sont documentées.
