"""Essais hors réseau pour l'interface publique TED et son historique local."""
from datetime import date
import copy
import pytest

from app.collecteur_ted_continu import (
    TEDInvalide, StockageTED, collecter_jour, cycle,
)

JOUR = date(2026, 10, 12)


def avis(no, titre="Recherche scientifique"):
    return {
        "publication-number": no,
        "publication-date": "2026-10-12",
        "notice-title": {"fra": [titre]},
        "buyer-name": {"fra": ["Université publique"]},
        "buyer-country": "FRA",
        "notice-type": "cn-standard",
        "classification-cpv": ["73100000"],
        "deadline": "2026-11-14",
    }


def reponse(lignes, total, token=None):
    return {
        "notices": lignes, "totalNoticeCount": total,
        "iterationNextToken": token, "timedOut": False,
    }


def test_parcours_integral_et_importation(tmp_path, monkeypatch):
    monkeypatch.setattr("app.collecteur_ted_continu.NOMBRE_PAR_PAGE", 1)
    demandes = []
    def obtenir(corps):
        demandes.append(corps)
        if corps["page"] == 1:
            return reponse([avis("1234-2026")], 2)
        assert corps["page"] == 2
        return reponse([avis("1235-2026", "Cybersécurité")], 2)
    captures, pages = collecter_jour(JOUR, obtenir=obtenir, attendre=lambda _: None)
    assert pages == 2
    assert len(captures) == 2
    assert demandes[0]["paginationMode"] == "PAGE_NUMBER"
    assert demandes[0]["scope"] == "ALL"
    assert "buyer-country = FRA" in demandes[0]["query"]
    assert demandes[1]["page"] == 2
    db = StockageTED(tmp_path / "ted.sqlite3")
    first = db.importer(JOUR, captures, pages)
    assert first["etat"] == "actualisé"
    assert db.etat() == {
        "avis": 2, "versions": 2, "jours": 1, "dernier_jour": "2026-10-12"
    }
    assert db.rechercher("cybersécurité")[0]["numero"] == "1235-2026"
    assert db.importer(JOUR, captures, pages)["etat"] == "inchangé"
    assert db.etat()["versions"] == 2


def test_une_republication_change_la_version_sans_perdre_l_ancienne(tmp_path):
    storage = StockageTED(tmp_path / "ted.sqlite3")
    original, _ = collecter_jour(
        JOUR, obtenir=lambda _: reponse([avis("1234-2026")], 1),
    )
    storage.importer(JOUR, original, 1)
    change, _ = collecter_jour(
        JOUR, obtenir=lambda _: reponse([avis("1234-2026", "Physique")], 1),
    )
    storage.importer(JOUR, change, 1)
    assert storage.etat()["avis"] == 1
    assert storage.etat()["versions"] == 2
    assert storage.rechercher("Physique")[0]["numero"] == "1234-2026"


@pytest.mark.parametrize("reponse_fausse,raison", [
    ({"notices": [], "totalNoticeCount": 1}, "incomplète"),
    ({"notices": [avis("1234-2026")], "totalNoticeCount": 1,
      "timedOut": True}, "expirée"),
    ({"notices": [], "totalNoticeCount": "0"}, "Décompte"),
])
def test_refus_des_pages_incompletes(reponse_fausse, raison):
    with pytest.raises(TEDInvalide, match=raison):
        collecter_jour(
            JOUR, obtenir=lambda _: reponse_fausse, attendre=lambda _: None,
        )


def test_decompte_changeant_et_identifiants_incoherents(monkeypatch):
    monkeypatch.setattr("app.collecteur_ted_continu.NOMBRE_PAR_PAGE", 1)
    compteur = 0
    def obtenir(_):
        nonlocal compteur
        compteur += 1
        if compteur == 1:
            return reponse([avis("1234-2026")], 2, "suite")
        return reponse([avis("1235-2026")], 3)
    with pytest.raises(TEDInvalide, match="modifié"):
        collecter_jour(JOUR, obtenir=obtenir, attendre=lambda _: None)
    faux = avis("1234-2026")
    faux["publication-date"] = "2026-10-13"
    with pytest.raises(TEDInvalide, match="dehors"):
        collecter_jour(JOUR, obtenir=lambda _: reponse([faux], 1))


def test_echec_de_collecte_ne_modifie_pas_la_base(tmp_path):
    db = StockageTED(tmp_path / "ted.sqlite3")
    notices, pages = collecter_jour(
        JOUR, obtenir=lambda _: reponse([avis("1234-2026")], 1),
    )
    db.importer(JOUR, notices, pages)
    def invalide(_):
        return {"notices": [avis("1234-2026", "modification")],
                "totalNoticeCount": 2}
    with pytest.raises(TEDInvalide):
        collecter_jour(JOUR, obtenir=invalide)
    assert db.etat() == {
        "avis": 1, "versions": 1, "jours": 1, "dernier_jour": "2026-10-12"
    }


def test_recherche_litterale_ne_traite_pas_pourcent_comme_joker(tmp_path):
    db = StockageTED(tmp_path / "ted.sqlite3")
    raw, _ = collecter_jour(
        JOUR, obtenir=lambda _: reponse([avis("1234-2026", "Valeur 40%")], 1),
    )
    db.importer(JOUR, raw, 1)
    assert db.rechercher("40%")
    assert db.rechercher("40_") == []
    with pytest.raises(ValueError):
        db.rechercher("test", 0)


def test_collecte_sur_plusieurs_jours():
    calls = []
    def obtenir(corps):
        calls.append(corps["query"])
        return reponse([], 0)
    from tempfile import TemporaryDirectory
    from pathlib import Path
    with TemporaryDirectory() as dossier:
        base = StockageTED(Path(dossier) / "test.db")
        resultats = cycle(base, jours=2, premier=JOUR, obtenir=obtenir,
                          attendre=lambda _: None)
        assert resultats["jours"] == 2
        assert len(calls) == 2
        assert "20261012" in calls[0]
        assert "20261013" in calls[1]
