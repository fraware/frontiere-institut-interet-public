"""Chronologie PFAS et registre des passages primaires version 4."""
import json
from pathlib import Path

from scripts.construire_registre_verification_evenements import construire
from scripts.verifier_corpus_public import verifier as verifier_corpus
from scripts.verifier_passages_sources import verifier as verifier_passages

ROOT = Path(__file__).resolve().parents[1] / "donnees"


def lire(nom):
    return json.loads((ROOT / nom).read_text(encoding="utf-8"))


def test_pfas_remise_circulaire_et_publications_separees():
    ancien = lire("chronologies_v7.json")
    actuel = lire("chronologies_v8.json")
    avant = {x["id_signal"]: x for x in ancien["chronologies"]}
    apres = {x["id_signal"]: x for x in actuel["chronologies"]}
    assert avant.keys() == apres.keys()
    assert all(avant[k] == apres[k] for k in avant if k != "S027")
    a = apres["S027"]["evenements"]
    assert [x["date"] for x in a] == ["2025-09", "2026-04-15", "2026-04-27", "2026-04-28"]
    assert [x["id_evenement"] for x in a] == [
        "S027-E01", "S027-E02", "S027-E03", "S027-E04",
    ]
    assert "29 avril 2026" in a[2]["evenement"]
    assert "remise de son rapport le 15 avril" in a[2]["evenement"]
    assert sum(len(c["evenements"]) for c in actuel["chronologies"]) == 46


def test_registre_and_passages_reconstructibles():
    signaux = lire("signaux_publics_v1.json")
    actuel = lire("chronologies_v8.json")
    assert construire(signaux, actuel) == lire("registre_verification_evenements_v6.json")
    assert verifier_corpus(signaux, actuel)["valide_structurellement"]
    registre = lire("registre_verification_evenements_v6.json")
    passages = lire("passages_sources_evenements_v4.json")
    bilan = verifier_passages(registre, passages)
    assert bilan["valide_structurellement"], bilan["erreurs"]
    assert bilan["total_evenements_registre"] == 46
    assert bilan["passages_documentaires_preliminaires"] == 29
    assert bilan["evenements_sans_passage_individuel"] == 17
    assert bilan["relecture_independante_realisee"] is False


def test_documents_historiques_reproductibles():
    signaux = lire("signaux_publics_v1.json")
    for version in range(3, 9):
        assert construire(signaux, lire(f"chronologies_v{version}.json")) == lire(
            f"registre_verification_evenements_v{version - 2}.json"
        )
    for reg, passages in [(3, 1), (4, 2), (5, 3), (6, 4)]:
        assert verifier_passages(
            lire(f"registre_verification_evenements_v{reg}.json"),
            lire(f"passages_sources_evenements_v{passages}.json"),
        )["valide_structurellement"]
