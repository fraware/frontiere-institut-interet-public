"""Essais de cohérence des passages historiques documentés."""
import copy
import json
from pathlib import Path

from scripts.verifier_passages_sources import verifier

ROOT = Path(__file__).resolve().parents[1] / "donnees"


def lire(nom):
    return json.loads((ROOT / nom).read_text(encoding="utf-8"))


def test_passages_reels_restent_structurels_et_non_independants():
    registre = lire("registre_verification_evenements_v3.json")
    passages = lire("passages_sources_evenements_v1.json")
    bilan = verifier(registre, passages)
    assert bilan["valide_structurellement"], bilan["erreurs"]
    assert bilan["total_evenements_registre"] == 48
    assert bilan["passages_documentaires_preliminaires"] == 14
    assert bilan["evenements_sans_passage_individuel"] == 34
    assert bilan["relecture_independante_realisee"] is False


def test_signale_un_identifiant_ou_lien_invalide():
    registre = lire("registre_verification_evenements_v3.json")
    passages = lire("passages_sources_evenements_v1.json")
    copie = copy.deepcopy(passages)
    copie["entrees"][0]["identifiant_evenement"] = "S999-E01"
    copie["entrees"][1]["source_principale"]["url"] = "http://exemple.fr"
    bilan = verifier(registre, copie)
    assert not bilan["valide_structurellement"]
    assert any("événement inconnu" in e for e in bilan["erreurs"])
    assert any("URL invalide" in e for e in bilan["erreurs"])


def test_refuse_de_pretendre_a_une_relecture_independante():
    registre = lire("registre_verification_evenements_v3.json")
    passages = lire("passages_sources_evenements_v1.json")
    passages["entrees"][0]["verification_independante"] = True
    assert not verifier(registre, passages)["valide_structurellement"]
