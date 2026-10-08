import json
from pathlib import Path

import pytest

from scripts.preparer_sessions_jeu_reserve import METHODES, preparer


def echantillon(tmp_path):
    questions = tmp_path / "questions.json"
    modele = tmp_path / "modele.json"
    questions.write_text(json.dumps({
        "version_schema": "jeu-reserve-v1",
        "date_creation": "2026-10-05",
        "cas": [
            {"code": "H01", "titre": "Premier", "question": "Que faire ?", "source_privee": "NE_PAS_DIFFUSER"},
            {"code": "H02", "titre": "Second", "question": "Qui mobiliser ?"},
        ],
    }), encoding="utf-8")
    modele.write_text(json.dumps({
        "version_schema": "reponses-jeu-reserve-v1",
        "methode": "a-remplacer",
        "version_methode": "1",
        "cas": [
            {"code": "H01", "voies": ["SOLUTION_A_NE_PAS_DIFFUSER"]},
            {"code": "H02", "ressources": ["RESSOURCE_SECRETE"]},
        ],
    }), encoding="utf-8")
    return questions, modele


def test_trois_dossiers_contiennent_uniquement_les_questions_publiques(tmp_path):
    questions, modele = echantillon(tmp_path)
    sortie = tmp_path / "experience"
    manifeste = preparer(questions, modele, sortie, "essai_001", 25)
    assert manifeste["nombre_cas"] == 2
    assert manifeste["reponses_collectees"] is False
    assert manifeste["reference_privee_consultee"] is False
    for nom in METHODES:
        fichier_questions = (sortie / nom / "questions.json").read_text(encoding="utf-8")
        fichier_reponses = (sortie / nom / "reponses_vierges.json").read_text(encoding="utf-8")
        assert "NE_PAS_DIFFUSER" not in fichier_questions
        assert "NE_PAS_DIFFUSER" not in fichier_reponses
        assert "RESSOURCE_SECRETE" not in fichier_reponses
        assert json.loads(fichier_reponses)["cas"][0]["voies"] == []
        assert json.loads(fichier_reponses)["cas"][1]["ressources"] == []
        journal = json.loads((sortie / nom / "journal_vierge.json").read_text(encoding="utf-8"))
        assert journal["cas"][0]["debut_iso"] is None
        assert journal["cas"][0]["reconnaissance_fortuite_origine"] is None
    contenus = [(sortie / nom / "questions.json").read_bytes() for nom in METHODES]
    assert len(set(contenus)) == 1


def test_refuse_ecrasement_de_dossier(tmp_path):
    questions, modele = echantillon(tmp_path)
    sortie = tmp_path / "experience"
    preparer(questions, modele, sortie, "essai_001", 25)
    with pytest.raises(FileExistsError):
        preparer(questions, modele, sortie, "essai_001", 25)


@pytest.mark.parametrize("identifiant,budget", [
    ("invalide avec espace", 20),
    ("ok", 20),
    ("session_valide", 0),
    ("session_valide", -1),
])
def test_refuse_configuration_invalide(tmp_path, identifiant, budget):
    questions, modele = echantillon(tmp_path)
    with pytest.raises(ValueError):
        preparer(questions, modele, tmp_path / "experience", identifiant, budget)


def test_refuse_ecart_de_codes(tmp_path):
    questions, modele = echantillon(tmp_path)
    donnees = json.loads(modele.read_text(encoding="utf-8"))
    donnees["cas"][1]["code"] = "H03"
    modele.write_text(json.dumps(donnees), encoding="utf-8")
    with pytest.raises(ValueError):
        preparer(questions, modele, tmp_path / "experience", "essai_001", 20)


def test_refuse_destination_dans_depot_public(tmp_path):
    questions, modele = echantillon(tmp_path)
    depot = Path(__file__).resolve().parents[1]
    with pytest.raises(ValueError, match="extérieure"):
        preparer(questions, modele, depot / "evaluation" / "sessions_a_ne_pas_creer", "essai_001", 25)
