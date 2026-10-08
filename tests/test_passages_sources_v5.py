"""Exigences de provenance de la cinquième collection documentaire."""
import copy
import json
from pathlib import Path

from scripts.verifier_passages_sources import verifier

ROOT = Path(__file__).resolve().parents[1] / "donnees"


def lire(nom):
    return json.loads((ROOT / nom).read_text(encoding="utf-8"))


def test_quarante_cinq_passages_identifies_et_une_lacune_explicite():
    registre = lire("registre_verification_evenements_v6.json")
    passages = lire("passages_sources_evenements_v5.json")
    rapport = verifier(registre, passages)
    assert rapport["valide_structurellement"], rapport["erreurs"]
    assert rapport["total_evenements_registre"] == 46
    assert rapport["passages_documentaires_preliminaires"] == 45
    assert rapport["evenements_sans_passage_individuel"] == 1
    assert passages["evenements_restants_sans_passage"] == ["S042-E04"]
    assert rapport["relecture_independante_realisee"] is False
    assert all(
        e["verification_independante"] is False
        and e["etat_verification"] == "LECTURE_DOCUMENTAIRE_PRELIMINAIRE"
        and e["limites"].strip()
        for e in passages["entrees"]
    )


def test_liste_incomplete_ou_erronee_est_rejetee():
    registre = lire("registre_verification_evenements_v6.json")
    passages = lire("passages_sources_evenements_v5.json")
    incorrect = copy.deepcopy(passages)
    incorrect["evenements_restants_sans_passage"] = []
    assert not verifier(registre, incorrect)["valide_structurellement"]
    incorrect = copy.deepcopy(passages)
    incorrect["entrees"].pop()
    incorrect["nombre_entrees"] -= 1
    assert not verifier(registre, incorrect)["valide_structurellement"]


def test_versions_documentaires_precedentes_restent_valides():
    registre = lire("registre_verification_evenements_v6.json")
    passages = lire("passages_sources_evenements_v4.json")
    ancien = verifier(registre, passages)
    assert ancien["valide_structurellement"], ancien["erreurs"]
    assert ancien["passages_documentaires_preliminaires"] == 29
    assert ancien["evenements_sans_passage_individuel"] == 17
