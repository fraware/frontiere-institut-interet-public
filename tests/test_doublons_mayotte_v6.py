"""Conserver les identifiants et détecter les doublons du cas Mayotte."""
import copy
import json
from pathlib import Path

from scripts.construire_registre_verification_evenements import construire
from scripts.verifier_corpus_public import verifier

ROOT = Path(__file__).resolve().parents[1] / "donnees"


def lire(nom):
    return json.loads((ROOT / nom).read_text(encoding="utf-8"))


def test_supprime_deux_doublons_sans_renumeroter():
    ancien = lire("chronologies_v5.json")
    courant = lire("chronologies_v6.json")
    x = next(c for c in ancien["chronologies"] if c["id_signal"] == "S038")
    y = next(c for c in courant["chronologies"] if c["id_signal"] == "S038")
    assert len(x["evenements"]) == 10
    assert len(y["evenements"]) == 8
    ids = [e["id_evenement"] for e in y["evenements"]]
    assert "S038-E07" not in ids and "S038-E08" not in ids
    assert ids[-2:] == ["S038-E09", "S038-E10"]
    assert {f["identifiant_supprime"]: f["identifiant_canonique"] for f in courant["fusions_doublons"]} == {
        "S038-E07": "S038-E09", "S038-E08": "S038-E10"
    }
    assert sum(len(c["evenements"]) for c in courant["chronologies"]) == 46


def test_registre_actuel_et_passages_conformes():
    signaux = lire("signaux_publics_v1.json")
    chronos = lire("chronologies_v6.json")
    registre = construire(signaux, chronos)
    assert registre == lire("registre_verification_evenements_v4.json")
    assert registre["nombre_evenements"] == 46
    rapport = verifier(signaux, chronos)
    assert rapport["valide_structurellement"], rapport["erreurs"]
    assert rapport["nombre_evenements"] == 46
    assert rapport["alertes_dates_exactes_identiques"] == []


def test_audit_ancien_repere_la_date_repetee():
    rapport = verifier(lire("signaux_publics_v1.json"), lire("chronologies_v5.json"))
    assert any(a["id_signal"] == "S038" and a["date"] == "2025-01-14"
               for a in rapport["alertes_dates_exactes_identiques"])


def test_interdit_identifiant_duplique_et_fusion_incoherente():
    data = lire("chronologies_v6.json")
    mauvais = copy.deepcopy(data)
    c = mauvais["chronologies"][0]
    c["evenements"][1]["id_evenement"] = c["evenements"][0]["id_evenement"]
    rapport = verifier(lire("signaux_publics_v1.json"), mauvais)
    assert not rapport["valide_structurellement"]
    assert any("répété" in e for e in rapport["erreurs"])
    mauvais = copy.deepcopy(data)
    mauvais["fusions_doublons"][0]["identifiant_canonique"] = "S038-E404"
    rapport = verifier(lire("signaux_publics_v1.json"), mauvais)
    assert not rapport["valide_structurellement"]
