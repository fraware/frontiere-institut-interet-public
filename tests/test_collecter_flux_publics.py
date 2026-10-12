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
    assert len(sources) == 3
    assert {src["type"] for src in sources} == {"rss", "bluesky"}
    assert all(src["active"] for src in sources)


def test_collecte_indexe_et_dedoublonne():
    config = _configuration()
    first, etat = executer(
        config, _ancien(), _etat(),
        telecharger=_telecharger, horodatage="2026-10-12T12:00:00+00:00",
    )
    assert etat["sources_reussies"] == 3
    assert etat["nouveaux_signaux"] == 3
    assert etat["nombre_signaux_distincts"] == 3
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
    assert bilan["nombre_signaux_distincts"] == 3
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
    src = _configuration()["sources"][-1]
    lignes = extraire_bluesky(BSKY, src)
    assert len(lignes) == 1
    assert "/profile/agencerecherche.bsky.social/post/3m12345" in lignes[0]["lien"]


def test_hote_et_acces_restreints():
    original = _configuration()
    original["sources"][0]["url"] = "https://localhost/adresse"
    with pytest.raises(CollecteInvalide):
        verifier_sources(original)
    original = _configuration()
    original["sources"][-1]["did"] = "agencerecherche.bsky.social"
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
