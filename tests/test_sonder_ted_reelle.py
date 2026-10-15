"""Essais déterministes du diagnostic réel TED, sans appel HTTP pendant pytest."""
from datetime import date
import pytest

from scripts.sonder_ted_reelle import sonder, TEDInvalide

JOUR = date(2026, 10, 13)


def publication(num="3001-2026"):
    return {
        "publication-number": num,
        "publication-date": "2026-10-13",
        "notice-title": {"fra": ["Marché de recherche"]},
        "buyer-name": {"fra": ["Établissement public"]},
        "buyer-country": "FRA",
    }


def test_requete_sur_le_jour_et_resultat_borne():
    appels = []
    def serveur(corps):
        appels.append(corps)
        return {"notices": [publication()], "totalNoticeCount": 123}
    bilan = sonder(JOUR, demander=serveur)
    assert bilan["controle_structurel"] == "reussi"
    assert bilan["resultats_declares"] == 123
    assert bilan["premier_numero"] == "3001-2026"
    assert bilan["portee"] == "premiere_page_uniquement"
    assert appels[0]["paginationMode"] == "PAGE_NUMBER"
    assert appels[0]["page"] == 1
    assert appels[0]["limit"] == 25
    assert "buyer-country = FRA" in appels[0]["query"]


def test_jour_sans_publication_possible():
    bilan = sonder(JOUR, demander=lambda _: {
        "notices": [], "totalNoticeCount": 0,
    })
    assert bilan["resultats_declares"] == 0
    assert bilan["controle_structurel"] == "reussi"


@pytest.mark.parametrize("reponse", [
    {"notices": [], "totalNoticeCount": 2},
    {"notices": [publication()], "totalNoticeCount": 1, "timedOut": True},
    {"notices": [publication()], "totalNoticeCount": "1"},
    {"notices": [publication(), publication()], "totalNoticeCount": 2},
])
def test_incompatibilites_refusees(reponse):
    with pytest.raises(TEDInvalide):
        sonder(JOUR, demander=lambda _: reponse)
