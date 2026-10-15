# Correspondances d'acheteurs BOAMP–DECP dans une enquête indépendante

## Population et provenance

Le premier lot repose exclusivement sur les 36 avis BOAMP tirés
indépendamment et conservés avec leurs réponses officielles. Parmi eux,
l'étude antérieure a identifié 17 observations d'un identifiant de
quatorze chiffres associé au rôle d'acheteur, réparties sur 16 chaînes
distinctes. Dans ces avis, **le schéma SIRET n'était pas déclaré**.

L'étude a également enregistré 16 recherches de ces numéros dans une
interface administrative publique, avec conservation des réponses brutes,
de leurs empreintes et de leurs dates de consultation.

Le programme `scripts/constituer_correspondances_siret_boamp_decp.py`
rejoue les preuves des trois ensembles existants : réponses d'avis,
recherches administratives et relevés de marchés attribués AIFE/DGFiP.
Il vérifie les réponses primaires et les empreintes déjà figées en
réutilisant le programme de reconstitution des 17 chaînes documentaires.

## Règle de rapprochement

Un avis n'est considéré comme relié sur le plan documentaire à un
acheteur DECP que si les deux conditions suivantes sont réunies :

1. Le numéro à quatorze chiffres déclaré dans le rôle d'acheteur BOAMP
   figure **exactement comme SIRET d'établissement** dans la réponse
   administrative archivée, au sein de l'unité légale correspondante.
2. Ce même numéro figure dans la clé d'acheteur d'au moins une identité
   de marché DECP, reconstruite et dédoublonnée sur la paire
   (SIRET d'acheteur, identifiant de marché).

Le nombre de marchés du même SIRET est un décompte d'identités
**documentaires**, et non un décompte d'achats juridiquement distincts.
La procédure ne prétend ni confirmer le rôle juridique du pouvoir
adjudicateur, ni relier une annonce à un contrat particulier, ni
identifier un besoin encore ouvert.

Un numéro BOAMP non attesté comme établissement exact dans la réponse
administrative **n'est jamais utilisé comme lien DECP**. Une absence
de correspondance signifie « non établie dans ces sources », et ne
démontre pas l'inexistence de l'organisme.

## Déroulement et publication

La procédure `.github/workflows/correspondances-siret-boamp-decp.yml`
récupère les deux ensembles historiques encore disponibles dans les
archives des actions GitHub, vérifie les empreintes connues et exécute
le calcul sans effectuer d'appel aux producteurs publics.

Son résultat est conservé dans une **pièce jointe temporaire de
procédure pendant 30 jours**. Lors d'un déclenchement par modification
de `main`, une seconde tâche disposant de droits de publication distincts
contrôle la version du fichier et ouvre, sous réserve de permissions GitHub,
une **demande de fusion en brouillon**, limitée au fichier
`institutionnel/besoins_publics/correspondances_siret_boamp_decp_17.json`.
Elle refuse de publier si `main` a changé depuis la révision de l'étude.
Les écritures directes sur la branche principale restent interdites.

Les nombres empiriques de correspondances ne sont considérés acquis
qu'à la suite d'une exécution réussie sur les archives originales.
La publication demeure soumise à examen et à la réussite des contrôles.

Les sources archivées et les résultats de recherche associés ont
également une durée de conservation limitée. Leur indisponibilité future
devra être déclarée comme une impossibilité de rejouer la preuve ;
elle n'autorise ni une reconstruction approximative ni une conclusion
nouvelle.

## Critères de validation

- 17 avis vérifiés, 16 identifiants distincts, sans substitution de source ;
- un contrôle administratif positif exact comme condition préalable ;
- dédoublonnage DECP par SIRET et identifiant de marché ;
- aucun appariement BOAMP–DECP par nom, référence de procédure ou
  ressemblance textuelle ;
- aucun lien contractuel ou besoin institutionnel inféré ;
- échec intégral si une empreinte, une source, une identité ou un
  dénominateur attendu est incompatible.

Pour vérifier les règles sans réseau :

```sh
python -m pytest -q tests/test_constituer_correspondances_siret_boamp_decp.py
```

Les mesures produites concerneront **uniquement les 17 avis étudiés**.
Elles ne pourront pas être extrapolées à l'ensemble du BOAMP.
