import json
from pathlib import Path

from scripts.evaluer_cas_retrospectifs import mesurer


def test_cas_retrospectifs_couvrent_douze_situations():
    questions = json.loads(
        Path("evaluation/cas_retrospectifs_developpement_v1_questions.json").read_text(encoding="utf-8")
    )
    references = json.loads(
        Path("evaluation/cas_retrospectifs_developpement_v1_references.json").read_text(encoding="utf-8")
    )
    modele = json.loads(
        Path("evaluation/cas_retrospectifs_developpement_v1_modele_reponses.json").read_text(encoding="utf-8")
    )

    codes_questions = [cas["code"] for cas in questions["cas"]]
    codes_references = [cas["code"] for cas in references["cas"]]
    codes_modele = [cas["code"] for cas in modele["cas"]]

    attendus = [f"D{i:02d}" for i in range(1, 13)]
    assert codes_questions == attendus
    assert codes_references == attendus
    assert codes_modele == attendus


def test_references_utilisent_uniquement_les_categories_admises():
    categories = json.loads(
        Path("evaluation/categories_comparaison_v1.json").read_text(encoding="utf-8")
    )
    references = json.loads(
        Path("evaluation/cas_retrospectifs_developpement_v1_references.json").read_text(encoding="utf-8")
    )

    voies = set(categories["voies_resolution"])
    formes = set(categories["formes_ressource"])

    for cas in references["cas"]:
        assert set(cas["voies_attendues"]) <= voies
        assert set(cas["formes_attendues"]) <= formes


def test_mesure_penalise_les_propositions_excessives():
    resultat = mesurer(
        ["investissement matériel"],
        ["investissement matériel", "recrutement contractuel", "réorganisation"],
    )
    assert resultat["rappel"] == 1.0
    assert round(resultat["precision"], 6) == round(1 / 3, 6)
    assert resultat["mesure_harmonique"] == 0.5
