# Découverte contrôlée des flux de sites institutionnels

Cette extension complète l'inventaire des éditeurs de données et des canaux déjà abonnés. Elle examine **cinq pages institutionnelles publiquement documentées**, appartenant à l'ANR, aux ministères économiques, à la transition écologique, au centre de communication scientifique du CNRS et à *CNRS Le Journal*.

Sources de référence : [ANR](https://anr.fr/fr/flux-rss-et-reseaux-sociaux/), [ministères économiques](https://www.economie.gouv.fr/tous-les-fils-d-infos), [transition écologique](https://www.ecologie.gouv.fr/flux-rss), [centre de communication scientifique](https://www.ccsd.cnrs.fr/rester-informe/) et [CNRS Le Journal](https://lejournal.cnrs.fr/ecrans).

## Acquisition

Le fichier `institutionnel/canaux_publics/sites_verifies_v1.json` définit cinq **hôtes autorisés** et la page à examiner. Aucune origine ajoutée par une publication ou un lien de page ne peut provoquer une requête. Les redirections restent limitées au même hôte et au protocole sécurisé.

Le programme `scripts/decouvrir_liens_syndication.py` lit au plus 800 000 octets HTML par page et repère :

- les déclarations HTML `rel="alternate"` avec type RSS ou Atom ;
- les liens du même hôte portant explicitement RSS, Atom ou `/feed/` dans leur adresse, ou dont le texte annonce clairement un flux.

Les liens sont normalisés, dédupliqués et conservés avec leur page de provenance dans `institutionnel/canaux_publics/decouvertes_sites.json`. **Aucun nouveau flux n'est téléchargé, validé ou activé automatiquement.** Les URL externes, privées ou vers un hôte différent sont ignorées. Un lien candidat peut conduire à un document HTML ou à une erreur ; seul un contrôle de contenu ultérieur permettra d'établir son format.

Une page inaccessible n'est pas traduite en absence de canal. Les dernières observations réussies sont conservées. Si toutes les pages échouent, aucun nouvel état n'est publié. Les pages HTML dynamiques, les liens construits par scripts et les sous-domaines non autorisés ne sont pas couverts.

## Vérification et programmation

```bash
python -m pytest -q tests/test_decouvrir_liens_syndication.py
python scripts/decouvrir_liens_syndication.py
```

La procédure déjà présente `.github/workflows/inventaire-canaux.yml` effectue la découverte en plus de l'inventaire local, quatre fois par jour. Les deux sorties restent distinctes. Les seuls fichiers de données autorisés en publication automatique sont l'inventaire des éditeurs et le relevé des liens de sites.

## Extension future

La liste de cinq pages constitue une expérimentation technique limitée. Pour étendre la découverte au territoire national, il faudra relier les entités administratives aux domaines officiels par des références établies, puis faire évoluer le registre des hôtes et les cadences. Un nombre important d'éditeurs de données ouvertes ne signifie pas qu'ils disposent d'un domaine web distinct.

Aucune publication issue d'un flux candidat n'est, en l'état, qualifiée comme besoin opérationnel.
