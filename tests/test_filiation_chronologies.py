"""Les corrections historiques doivent être motivées sans altérer les versions précédentes."""
import copy
import json
from pathlib import Path

from scripts.auditer_filiation_chronologies import controle_filiation

ROOT = Path(__file__).resolve().parents[1] / "donnees"


def documents():
    return [
        json.loads((ROOT / f"chronologies_v{n}.json").read_text(encoding="utf-8"))
        for n in range(3, 10)
    ]


def test_versions_officielles_et_suppressions_documentees():
    bilan = controle_filiation(documents())
    assert bilan["valide_structurellement"], bilan["erreurs"]
    assert bilan["versions_examinees"] == 7
    assert len(bilan["transitions"]) == 6
    assert [x["nombre_evenements"] for x in bilan["transitions"]] == [48, 48, 46, 46, 46, 45]
    assert bilan["transitions"][2]["evenements_supprimes"] == ["S038-E07", "S038-E08"]
    assert bilan["transitions"][-1]["evenements_supprimes"] == ["S042-E04"]
    assert bilan["transitions"][-1]["cas_rectifies"] == ["S042"]


def test_modification_sans_rectificatif_est_signalee():
    docs = documents()
    falsifies = copy.deepcopy(docs)
    cas = next(x for x in falsifies[4]["chronologies"] if x["id_signal"] == "S018")
    cas["evenements"][0]["evenement"] = "Affirmation différente sans rectificatif."
    bilan = controle_filiation(falsifies)
    assert not bilan["valide_structurellement"]
    assert any("cas modifiés" in err for err in bilan["erreurs"])


def test_suppression_discrete_est_refusee():
    docs = documents()
    falsifies = copy.deepcopy(docs)
    cas = next(x for x in falsifies[-1]["chronologies"] if x["id_signal"] == "S038")
    cas["evenements"].pop()
    bilan = controle_filiation(falsifies)
    assert not bilan["valide_structurellement"]
    assert any("suppressions non conformes" in err for err in bilan["erreurs"])


def test_reecriture_du_journal_de_rectification_est_refusee():
    docs = documents()
    falsifies = copy.deepcopy(docs)
    falsifies[-1]["rectifications"][0]["nature"] = "Motif ancien réécrit."
    bilan = controle_filiation(falsifies)
    assert not bilan["valide_structurellement"]
    assert any("historique déclaré a été réécrit" in err for err in bilan["erreurs"])


def test_insertion_non_tracee_est_refusee():
    docs = documents()
    falsifies = copy.deepcopy(docs)
    cas = next(x for x in falsifies[-1]["chronologies"] if x["id_signal"] == "S042")
    ajout = copy.deepcopy(cas["evenements"][0])
    ajout["id_evenement"] = "S042-E98"
    cas["evenements"].append(ajout)
    bilan = controle_filiation(falsifies)
    assert not bilan["valide_structurellement"]
    assert any("nouveaux événements" in err for err in bilan["erreurs"])
