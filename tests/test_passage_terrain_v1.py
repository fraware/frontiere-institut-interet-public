import json
from pathlib import Path


def test_demandes_execution_couvrent_les_quatre_cas():
    contenu = json.loads(
        Path("donnees/demandes_execution_ciblees_v1.json").read_text(encoding="utf-8")
    )
    demandes = contenu["demandes"]
    ids = [demande["id_signal"] for demande in demandes]

    assert ids == ["S001", "S016", "S024", "S042"]
    assert len(ids) == len(set(ids))

    for demande in demandes:
        assert demande["question_unique"].strip()
        assert demande["champs_minimaux"]
        assert demande["precision_minimale"].strip()
        assert demande["canal_public"].strip()
        assert demande["statut"] in {"prete_a_envoyer", "prete_a_router"}


def test_plafond_preuve_v2_conserve_les_quatre_cas():
    contenu = json.loads(
        Path("donnees/plafond_preuve_publique_v2.json").read_text(encoding="utf-8")
    )
    ids = [cas["id_signal"] for cas in contenu["cas"]]

    assert ids == ["S001", "S016", "S024", "S042"]
    assert contenu["cas"][-1]["statut"] == "preuve_publique_partielle_supplementaire"


def test_analyse_delais_v4_reste_prudente_sur_asnr():
    contenu = json.loads(
        Path("donnees/analyse_delais_v4.json").read_text(encoding="utf-8")
    )

    assert contenu["synthese"]["delais_de_parcours_mesurables"] == 6
    assert contenu["mise_a_jour_s042"]["delai_parcours_mesurable"] is False
    assert "différents" in contenu["mise_a_jour_s042"]["precaution"]


def test_document_passage_terrain_contient_les_quatre_institutions():
    texte = Path("docs/PASSAGE_DONNEES_EXECUTION_V1.md").read_text(encoding="utf-8")
    for nom in ["France Compétences", "IGN", "Saint-Brieuc", "ASNR"]:
        assert nom in texte
