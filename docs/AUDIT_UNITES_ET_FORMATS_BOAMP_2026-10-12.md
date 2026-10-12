# Audit des unités documentaires et des formats BOAMP — 12 octobre 2026

## Périmètre

Le corpus observé dans [l'exécution 38186561326](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38186561326) (archive 11719542712) comporte neuf avis choisis intentionnellement : six cas pilotes, un avis initial relié à un rectificatif, deux annonces antérieures vérifiées par références et acheteurs concordants. Il ne prétend pas représenter les marchés publics dans leur ensemble.

L'ancien inventaire indiquait neuf avis, six avis avec adresse dans un champ couvert, deux avis citant un dossier DCE précisément identifié et aucune pièce contractuelle obtenue. L'examen des octets officiels montre deux problèmes de mesure.

Le rectificatif Tisséo 26-83870 et l'avis initial 26-81640 citent le même dossier `www.marches-publics.info:IDM:1862843`. Deux citations documentaires représentent un seul dossier unique.

Huit avis utilisent le formulaire `eForms`, un avis SGDSN 26-77392 utilise `FNSimple`. Son champ `FNSimple/initial/communication/urlDocConsul` fournit une adresse de consultation sur PLACE. Le champ `docSecurite.oui` déclare des mesures de sécurité. L'absence de traitement de ce format aurait caché une référence existante. La déclaration de mesures de sécurité ne prouve pas la restriction effective, l'accès à la pièce ni sa réception.

Les effectifs corrigés restent à confirmer sur une nouvelle exécution réelle, distincte de ces observations sur l'archive précédente.

## Unités de mesure

**Avis officiel :** une publication identifiée dans la base BOAMP, indépendamment de l'existence d'avis initiaux, rectificatifs et attributions pour une même procédure.

**Référence documentaire :** une URI inscrite dans un champ de consultation du format effectivement pris en charge. Un lien vers un portail ne prouve ni l'existence d'un dossier identifiable ni la disponibilité de pièces.

**Dossier DCE précisément identifié :** une référence à un dossier de consultation sur une plateforme reconnue, avec numéro explicite. Pour le domaine `www.marches-publics.info`, la règle conservatrice utilise une URL HTTPS contenant `type=DCE` et un identifiant numérique `IDM`. Les avis distincts citant la même clé ne créent pas deux dossiers.

**Pièce obtenue :** possession réelle des octets de la pièce, empreinte et rattachement documentés. La disponibilité potentielle d'un lien ne satisfait pas ce critère.

**Exécution et contribution utile :** événements documentés de réalisation et d'utilisation effective ; ni publication ni attribution ne les établissent.

Le nouveau rapport déclare les formats `eforms`, `fnsimple`, `format_non_couvert` et `non_observe`. Un format non couvert n'est jamais interprété comme une preuve de l'absence de lien de consultation. Les chemins des champs sources et les références des avis demeurent enregistrés.

## Limites et critère suivant

Aucun règlement de consultation, cahier des charges ou procès-verbal de réception n'a été recueilli dans le corpus de neuf avis. L'adresse officielle d'un dossier Tisséo ne signifie pas que les pièces ont été téléchargées. Les documents confidentiels sont exclus de la collecte publique.

La prochaine expérience doit obtenir au moins une **pièce primaire publique vérifiable**, puis reconstruire, autant que les preuves le permettent, les étapes de disponibilité et d'utilisation. Le résultat scientifique prioritaire consiste à séparer achat ordinaire, recours à un prestataire qualifié, contraintes de spécification et difficultés attestées de mobilisation des compétences.
