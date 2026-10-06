import json
from pathlib import Path


def test_execution_terrain_couvre_les_quatre_cas():
    contenu = json.loads(
        Path("donnees/execution_terrain_v1.json").read_text(encoding="utf-8")
    )
    demandes = contenu["demandes"]

    assert [demande["id_signal"] for demande in demandes] == [
        "S001",
        "S024",
        "S042",
        "S016",
    ]
    assert len({demande["id_signal"] for demande in demandes}) == 4

    for demande in demandes:
        assert demande["question"].strip()
        assert demande["minimum_suffisant"]
        assert demande["canal_principal"].strip()
        assert demande["statut"] == "prete_a_envoyer"


def test_execution_terrain_definit_une_seule_relance():
    contenu = json.loads(
        Path("donnees/execution_terrain_v1.json").read_text(encoding="utf-8")
    )
    relance = contenu["regle_relance"]

    assert relance["nombre_maximal"] == 1
    assert relance["delai_jours_ouvres_min"] == 4
    assert relance["delai_jours_ouvres_max"] == 6


def test_document_execution_contient_canaux_et_criteres_de_cloture():
    texte = Path("docs/EXECUTION_TERRAIN_V1.md").read_text(encoding="utf-8")

    for fragment in [
        "rh@francecompetences.fr",
        "ddtm-dml@cotes-darmor.gouv.fr",
        "info@asnr.fr",
        "recrutement-mobilite@ign.fr",
        "Critère de clôture",
        "Une absence de réponse ne constitue pas un résultat empirique",
    ]:
        assert fragment in texte
