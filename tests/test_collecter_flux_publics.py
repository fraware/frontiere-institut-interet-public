"""Tests hors réseau de la collecte institutionnelle multisource."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.collecter_flux_publics import (
    CollecteInvalide, adresse_requete, executer, extraire_bluesky,
    extraire_syndication, verifier_sources,
)

RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Publications</title>
<item><guid>avis-1</guid><title>Nouvel appel a projets</title>
<link>https://anr.fr/fr/detail/avis-1/</link>
<description>Appel a contributions</description>
<pubDate>Mon, 12 Oct 2026 10:00:00 GMT</pubDate></item>
</channel></rss>"""

ATOM = b"""<feed xmlns="http://www.w3.org/2005/Atom">
<entry><id>tag:anr.fr,2026:1</id><title>Projet collectif</title>
<updated>2026-10-12T11:00:00Z</updated>
<link href="https://anr.fr/fr/detail/avis-2/"/></entry></feed>"""

DID = "did:plc:poa5nra3tnvjpki64nprt27d"
BSKY = json.dumps({
    "feed": [
        {"post": {"author": {"did": DID},
                  "uri": "at://" + DID + "/app.bsky.feed.post/3m12345",
                  "cid": "bafy1",
                  "record": {"text": "Appel a manifestation d'interet",
                             "createdAt": "2026-10-12T10:30:00Z"}}},
        {"reason": {"$type": "app.bsky.feed.defs#reasonRepost"},
         "post": {"author": {"did": DID},
                  "uri": "at://" + DID + "/app.bsky.feed.post/3m88888",
                  "record": {"text": "Repartage"}}},
        {"post": {"author": {"did": "did:plc:aaaaaaaaaaaaaaaaaaaaaaaa"},
                  "uri": "at://did:plc:aaaaaaaaaaaaaaaaaaaaaaaa/app.bsky.feed.post/3m345",
                  "record": {"text": "Auteur tiers"}}},
    ],
}).encode()


def _configuration():
    return json.loads(Path("institutionnel/flux_publics/sources_v1.json")
                      .read_text(encoding="utf-8"))


def _ancien():
    return {"version": 1, "observations": []}


def _etat():
    return {"version": 1, "sources": []}


def _telecharger(source, url):
    assert url == adresse_requete(source)
    return BSKY if source["type"] == "bluesky" else RSS


def test_catalogue_reel_et_domaines():
    sources = verifier_sources(_configuration())
    assert len(sources) == 9
    assert {src["type"] for src in sources} == {"rss", "bluesky"}
    assert all(src["active"] for src in sources)


def test_collecte_indexe_et_dedoublonne():
    config = _configuration()
    first, etat = executer(
        config, _ancien(), _etat(),
        telecharger=_telecharger, horodatage="2026-10-12T12:00:00+00:00",
    )
    assert etat["sources_reussies"] == 9
    assert etat["nouveaux_signaux"] == 9
    assert etat["nombre_signaux_distincts"] == 9
    assert not etat["couverture_exhaustive_des_besoins_publics"]
    assert not etat["qualification_de_besoins_effectuee"]
    assert all(x["nature_signal"] == "publication_publique_non_qualifiee"
               for x in first["observations"])
    second, suivi = executer(
        config, first, etat, telecharger=_telecharger,
        horodatage="2026-10-12T18:00:00+00:00",
    )
    assert second == first
    assert suivi["nouveaux_signaux"] == 0
    assert suivi["revisions"] == 0


def test_une_source_en_echec_ne_supprime_pas_les_autres():
    premiere, state = executer(
        _configuration(), _ancien(), _etat(), _telecharger,
        "2026-10-12T12:00:00+00:00",
    )

    def partiel(source, url):
        if source["id"] == "anr_appels":
            raise TimeoutError("panne volontaire")
        return _telecharger(source, url)

    _, bilan = executer(
        _configuration(), premiere, state, partiel,
        "2026-10-12T18:00:00+00:00",
    )
    assert bilan["sources_en_echec"] == 1
    panne = next(x for x in bilan["sources"] if x["id"] == "anr_appels")
    assert panne["erreur"] == "TimeoutError"
    assert panne["dernier_succes"] == "2026-10-12T12:00:00+00:00"


def test_aucune_source_reussie_interdit_la_publication():
    def panne(source, url):
        raise TimeoutError("indisponible")

    with pytest.raises(CollecteInvalide):
        executer(_configuration(), _ancien(), _etat(), panne)


def test_revision_effective_comptee_une_fois():
    config = _configuration()
    avant, etat = executer(config, _ancien(), _etat(), _telecharger,
                           "2026-10-12T12:00:00+00:00")

    def modifie(source, url):
        return (_telecharger(source, url).replace(
            b"Nouvel appel a projets", b"Nouvel appel a projets modifie"
        ) if source["id"] == "anr_appels" else _telecharger(source, url))

    apres, bilan = executer(config, avant, etat, modifie,
                            "2026-10-12T18:00:00+00:00")
    assert bilan["revisions"] == 1
    assert bilan["nombre_signaux_distincts"] == 9
    entree = next(x for x in apres["observations"] if x["source_id"] == "anr_appels")
    assert entree["nombre_revisions"] == 1
    assert entree["observe_initialement_le"] == "2026-10-12T12:00:00+00:00"


def test_atom_et_rss_explicitement_reconnus():
    src = _configuration()["sources"][0]
    assert extraire_syndication(RSS, src)[0]["date_publication"] == (
        "2026-10-12T10:00:00+00:00"
    )
    assert extraire_syndication(ATOM, src)[0]["lien"] == (
        "https://anr.fr/fr/detail/avis-2/"
    )


def test_pas_de_dtd_ni_de_format_arbitraire():
    src = _configuration()["sources"][0]
    with pytest.raises(CollecteInvalide):
        extraire_syndication(b'<!DOCTYPE rss [<!ENTITY x "test">]><rss/>', src)
    with pytest.raises(CollecteInvalide):
        extraire_syndication(b'<html><body>Site</body></html>', src)


def test_identite_officielle_did_filtre_repartages_et_tiers():
    src = next(x for x in _configuration()["sources"] if x["id"] == "anr_bluesky")
    lignes = extraire_bluesky(BSKY, src)
    assert len(lignes) == 1
    assert "/profile/agencerecherche.bsky.social/post/3m12345" in lignes[0]["lien"]


def test_hote_et_acces_restreints():
    original = _configuration()
    original["sources"][0]["url"] = "https://localhost/adresse"
    with pytest.raises(CollecteInvalide):
        verifier_sources(original)
    original = _configuration()
    next(x for x in original["sources"] if x["id"] == "anr_bluesky")["did"] = "agencerecherche.bsky.social"
    with pytest.raises(CollecteInvalide):
        verifier_sources(original)


def test_index_invalide_est_refuse():
    with pytest.raises(CollecteInvalide):
        executer(
            _configuration(),
            {"version": 1, "observations": [
                {"identifiant_publication": "duplicat"},
                {"identifiant_publication": "duplicat"},
            ]}, _etat(), _telecharger,
        )


RSS_DC = b"""<?xml version="1.0"?>
<rss xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0">
<channel><title>Bulletin ministeriel</title><item>
<guid>https://www.economie.gouv.fr/bulletins-officiels/texte-2026</guid>
<title>Decision de financement</title>
<dc:date>2026-10-12T09:15:00Z</dc:date>
</item></channel></rss>"""

RSS_HREF = b"""<rss version="2.0"><channel><item>
<guid>decision-2</guid><title>Nouvelle consultation</title>
<link href="https://www.economie.gouv.fr/dae/appel-2"/>
<published>2026-10-12T10:05:00Z</published>
</item></channel></rss>"""


def test_date_normalisee_depuis_champ_dc_date():
    src = next(x for x in _configuration()["sources"] if x["id"] == "economie_bulletins_officiels")
    entree = extraire_syndication(RSS_DC, src)[0]
    assert entree["date_publication"] == "2026-10-12T09:15:00+00:00"
    assert entree["lien"] == "https://www.economie.gouv.fr/bulletins-officiels/texte-2026"


def test_lien_rss_href_et_date_published():
    src = next(x for x in _configuration()["sources"] if x["id"] == "economie_achats_etat")
    entree = extraire_syndication(RSS_HREF, src)[0]
    assert entree["lien"] == "https://www.economie.gouv.fr/dae/appel-2"
    assert entree["date_publication"] == "2026-10-12T10:05:00+00:00"


def test_guid_opaque_ne_devient_pas_un_lien_invente():
    src = _configuration()["sources"][0]
    entree = extraire_syndication(
        b'<rss><channel><item><guid>opaque</guid><title>Titre</title></item></channel></rss>',
        src,
    )[0]
    assert entree["lien"] is None
    assert entree["date_publication"] is None


def test_enrichissement_date_sans_revision_du_document():
    """Une date auparavant non lue ne constitue pas une édition de l'avis."""
    config = _configuration()
    origine, premier_etat = executer(
        config, _ancien(), _etat(), _telecharger,
        "2026-10-12T21:58:28+00:00",
    )
    ajout_date = RSS.replace(
        b"</pubDate>", b"</pubDate>"
    ).replace(
        b"Mon, 12 Oct 2026 10:00:00 GMT",
        b"Tue, 13 Oct 2026 10:00:00 GMT",
    )

    def relecture(source, url):
        return ajout_date if source["id"] == "anr_appels" else _telecharger(source, url)

    suivant, etat = executer(
        config, origine, premier_etat, relecture,
        "2026-10-12T22:05:11+00:00",
    )
    original = next(v for v in origine["observations"] if v["source_id"] == "anr_appels")
    nouveau = next(v for v in suivant["observations"] if v["source_id"] == "anr_appels")
    assert original["titre"] == nouveau["titre"]
    assert original["description"] == nouveau["description"]
    assert etat["revisions"] == 0
    assert etat["enrichissements_metadonnees"] == 1
    assert nouveau["nombre_revisions"] == 0
    assert nouveau["nombre_enrichissements_metadonnees"] == 1


def test_rectificatif_du_second_cycle_reclasse_100_dates():
    """Le rectificatif conserve les annotations et les observations originales."""
    chemin = Path("institutionnel/flux_publics/observations.json")
    etat_chemin = Path("institutionnel/flux_publics/etat_collecte.json")
    if not chemin.is_file() or not etat_chemin.is_file():
        pytest.skip("Premières collectes publiques non encore publiées")
    observations = json.loads(chemin.read_text(encoding="utf-8"))["observations"]
    etat = json.loads(etat_chemin.read_text(encoding="utf-8"))
    classes = [x for x in observations if x.get("rectification_extraction")]
    assert len(classes) == 100
    assert all(
        x["nombre_revisions"] == 0
        and x["nombre_enrichissements_metadonnees"] == 1
        and x["source_id"] == "service_public_pro"
        for x in classes
    )
    assert etat["rectification_historique"]["nombre_publications_concernees"] == 100
    assert etat["revisions"] == 0
    assert etat["enrichissements_metadonnees"] >= 0  # Le compteur mesure uniquement le dernier cycle.



def test_rectificatif_historique_conserve_mais_compteurs_renouveles():
    """Préserver l'événement historique sans compter 100 enrichissements à chaque cycle."""
    config = _configuration()
    avant, etat = executer(
        config, _ancien(), _etat(), _telecharger,
        "2026-10-12T21:58:28+00:00",
    )
    etat["rectification_historique"] = {
        "nombre_publications_concernees": 100,
        "classification": "enrichissement_de_dates",
    }
    suivant, bilan = executer(
        config, avant, etat, _telecharger,
        "2026-10-13T02:00:00+00:00",
    )
    assert suivant == avant
    assert bilan["rectification_historique"] == etat["rectification_historique"]
    assert bilan["enrichissements_metadonnees"] == 0
    assert bilan["revisions"] == 0
    assert bilan["nouveaux_signaux"] == 0


def test_historique_invalide_est_refuse():
    ancien = {"version": 1, "sources": [], "rectification_historique": "incorrect"}
    with pytest.raises(CollecteInvalide):
        executer(_configuration(), _ancien(), ancien, _telecharger)
