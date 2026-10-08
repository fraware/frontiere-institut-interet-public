"""Retrait traçable d'une datation ASNR non étayée et couverture courante."""
import copy
import json
from pathlib import Path

from scripts.construire_registre_verification_evenements import construire
from scripts.verifier_corpus_public import verifier as verifier_corpus
from scripts.verifier_passages_sources import verifier as verifier_passages

ROOT = Path(__file__).resolve().parents[1] / "donnees"


def lire(nom):
    return json.loads((ROOT / nom).read_text(encoding="utf-8"))


def test_retrait_asnr_uniquement_et_ancien_fait_conserve():
    v8 = lire("chronologies_v8.json")
    v9 = lire("chronologies_v9.json")
    avant = {x["id_signal"]: x for x in v8["chronologies"]}
    apres = {x["id_signal"]: x for x in v9["chronologies"]}
    assert avant.keys() == apres.keys()
    assert all(avant[id] == apres[id] for id in avant if id != "S042")
    anciens = {x["id_evenement"] for x in avant["S042"]["evenements"]}
    nouveaux = {x["id_evenement"] for x in apres["S042"]["evenements"]}
    assert anciens - nouveaux == {"S042-E04"}
    assert "S042-E02" in nouveaux
    assert "février 2024" in next(x for x in apres["S042"]["evenements"] if x["id_evenement"] == "S042-E02")["evenement"]
    assert v9["retraits_evenements_non_confirmes"][0]["identifiant_retire"] == "S042-E04"
    assert sum(len(c["evenements"]) for c in v8["chronologies"]) == 46
    assert sum(len(c["evenements"]) for c in v9["chronologies"]) == 45


def test_les_quarante_cinq_evenements_ont_une_premiere_lecture():
    signaux = lire("signaux_publics_v1.json")
    chronos = lire("chronologies_v9.json")
    assert verifier_corpus(signaux, chronos)["valide_structurellement"]
    registre = lire("registre_verification_evenements_v7.json")
    assert construire(signaux, chronos) == registre
    passages = lire("passages_sources_evenements_v6.json")
    resultat = verifier_passages(registre, passages)
    assert resultat["valide_structurellement"], resultat["erreurs"]
    assert resultat["total_evenements_registre"] == 45
    assert resultat["passages_documentaires_preliminaires"] == 45
    assert resultat["evenements_sans_passage_individuel"] == 0
    assert passages["evenements_restants_sans_passage"] == []
    assert resultat["relecture_independante_realisee"] is False


def test_retrait_non_trace_ou_fictif_est_rejete():
    signaux = lire("signaux_publics_v1.json")
    original = lire("chronologies_v9.json")
    tronque = copy.deepcopy(original)
    tronque["retraits_evenements_non_confirmes"] = []
    assert not verifier_corpus(signaux, tronque)["valide_structurellement"]
    invente = copy.deepcopy(original)
    invente["retraits_evenements_non_confirmes"][0]["assertion_source_conservee"] = "S042-E999"
    assert not verifier_corpus(signaux, invente)["valide_structurellement"]


def test_registres_anterieurs_reproductibles():
    signaux = lire("signaux_publics_v1.json")
    for version in range(3, 10):
        assert construire(signaux, lire(f"chronologies_v{version}.json")) == lire(
            f"registre_verification_evenements_v{version - 2}.json"
        )
    assert verifier_passages(
        lire("registre_verification_evenements_v6.json"),
        lire("passages_sources_evenements_v5.json"),
    )["valide_structurellement"]
