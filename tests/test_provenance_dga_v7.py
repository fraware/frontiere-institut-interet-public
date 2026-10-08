"""Rattachement chronologique et documentaire des constats de recrutement DGA."""
import json
from pathlib import Path
from scripts.construire_registre_verification_evenements import construire
from scripts.verifier_corpus_public import verifier as verifier_corpus
from scripts.verifier_passages_sources import verifier as verifier_passages

ROOT = Path(__file__).resolve().parents[1] / "donnees"


def lire(nom):
    return json.loads((ROOT / nom).read_text(encoding="utf-8"))


def test_seul_le_cas_dga_change_et_ses_dates_restant_approximatives():
    avant = lire("chronologies_v6.json")
    apres = lire("chronologies_v7.json")
    a = {c["id_signal"]: c for c in avant["chronologies"]}
    b = {c["id_signal"]: c for c in apres["chronologies"]}
    assert a.keys() == b.keys()
    assert all(a[k] == b[k] for k in a if k != "S011")
    assert len(a["S011"]["evenements"]) == len(b["S011"]["evenements"]) == 4
    for old, new in zip(a["S011"]["evenements"], b["S011"]["evenements"]):
        assert old["id_evenement"] == new["id_evenement"]
        assert old["date"] == new["date"] == "2023"
        assert new["date_document_source"] == "2024-01-17"
        assert new["nature_date"] == "periode_de_reference_approximative"
    assert verifier_corpus(lire("signaux_publics_v1.json"), apres)["valide_structurellement"]


def test_registres_reproductibles_et_passages_documentaires_augmente():
    signaux = lire("signaux_publics_v1.json")
    for version, registre in ((3, 1), (4, 2), (5, 3), (6, 4), (7, 5)):
        assert construire(signaux, lire(f"chronologies_v{version}.json")) == lire(
            f"registre_verification_evenements_v{registre}.json"
        )
    passages = lire("passages_sources_evenements_v3.json")
    registre = lire("registre_verification_evenements_v5.json")
    resultat = verifier_passages(registre, passages)
    assert resultat["valide_structurellement"], resultat["erreurs"]
    assert resultat["total_evenements_registre"] == 46
    assert resultat["passages_documentaires_preliminaires"] == 18
    assert resultat["evenements_sans_passage_individuel"] == 28
    assert resultat["relecture_independante_realisee"] is False
    assert all(
        any(e["identifiant_evenement"] == f"S011-E{i:02d}" for e in passages["entrees"])
        for i in range(1, 5)
    )
