"""Non-régression des rectifications : dates, interprétations et filiation des versions."""
import json
from pathlib import Path

from scripts.construire_registre_verification_evenements import construire
from scripts.verifier_corpus_public import verifier

ROOT = Path(__file__).resolve().parents[1]


def charger(nom):
    return json.loads((ROOT / "donnees" / nom).read_text(encoding="utf-8"))


def test_rectificatif_prealable_reste_immuable_et_evenements_conserves():
    v3 = charger("chronologies_v3.json")
    v4 = charger("chronologies_v4.json")
    assert v3["version"] == "3"
    assert v4["version"] == "4"
    c3 = {c["id_signal"]: c for c in v3["chronologies"]}
    c4 = {c["id_signal"]: c for c in v4["chronologies"]}
    assert c3.keys() == c4.keys()
    assert sum(len(c["evenements"]) for c in c4.values()) == 48
    assert all(len(c3[k]["evenements"]) == len(c4[k]["evenements"]) for k in c3)
    assert all(c3[k] == c4[k] for k in c3 if k not in {"S001", "S016"})
    assert c3["S016"]["evenements"][1]["date"] == "2024-07-05"
    assert c4["S016"]["evenements"][1]["date"] == "2024-03-15"
    assert "fin 2023" in c4["S016"]["evenements"][1]["evenement"]
    assert "ne constate pas un nouvel état" in c4["S001"]["evenements"][2]["evenement"]


def test_registre_v2_correspond_aux_sources_versionnees():
    signaux = charger("signaux_publics_v1.json")
    ancien = construire(signaux, charger("chronologies_v3.json"))
    nouveau = construire(signaux, charger("chronologies_v4.json"))
    assert ancien == charger("registre_verification_evenements_v1.json")
    assert nouveau == charger("registre_verification_evenements_v2.json")
    assert ancien["version_schema"] == "registre-verification-evenements-v1"
    assert nouveau["version_schema"] == "registre-verification-evenements-v2"
    assert all(x["preuve_directe_de_cet_evenement"] == "A_VERIFIER" for x in nouveau["evenements"])
    assert all(x["resultat_relecture"] is None for x in nouveau["evenements"])


def test_corpus_v4_reste_structure_et_source():
    rapport = verifier(charger("signaux_publics_v1.json"), charger("chronologies_v4.json"))
    assert rapport["valide_structurellement"], rapport["erreurs"]
    assert rapport["nombre_evenements"] == 48
