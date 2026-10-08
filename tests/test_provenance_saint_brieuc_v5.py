"""Précision documentaire et stabilité des versions de Saint-Brieuc."""
import json
from pathlib import Path

from scripts.construire_registre_verification_evenements import construire
from scripts.verifier_corpus_public import verifier

ROOT = Path(__file__).resolve().parents[1] / "donnees"


def lire(nom):
    return json.loads((ROOT / nom).read_text(encoding="utf-8"))


def test_version_cinq_ne_change_que_saint_brieuc():
    avant = lire("chronologies_v4.json")
    apres = lire("chronologies_v5.json")
    anciennes = {x["id_signal"]: x for x in avant["chronologies"]}
    nouvelles = {x["id_signal"]: x for x in apres["chronologies"]}
    assert anciennes.keys() == nouvelles.keys()
    for code in anciennes:
        if code != "S024":
            assert anciennes[code] == nouvelles[code]
    assert len(nouvelles["S024"]["evenements"]) == 5
    assert [e["date"] for e in nouvelles["S024"]["evenements"]] == [
        "2017-04-18", "2021", "2023-11-22", "2024-05-28", "2025-06"
    ]
    assert "ne sollicite pas de renouvellement" in nouvelles["S024"]["evenements"][1]["evenement"]
    assert "16 mars 2026" in nouvelles["S024"]["evenements"][4]["evenement"]


def test_registres_historiques_conserves_et_registre_actualise():
    signaux = lire("signaux_publics_v1.json")
    for version, registre in (
        ("3", "registre_verification_evenements_v1.json"),
        ("4", "registre_verification_evenements_v2.json"),
        ("5", "registre_verification_evenements_v3.json"),
    ):
        document = construire(signaux, lire(f"chronologies_v{version}.json"))
        assert document == lire(registre)
        assert document["nombre_evenements"] == 48
        assert all(l["preuve_directe_de_cet_evenement"] == "A_VERIFIER" for l in document["evenements"])
    rapport = verifier(signaux, lire("chronologies_v5.json"))
    assert rapport["valide_structurellement"], rapport["erreurs"]
