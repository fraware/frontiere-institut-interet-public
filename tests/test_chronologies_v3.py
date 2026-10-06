import json
from pathlib import Path


def test_chronologies_v3_couvrent_les_dix_cas():
    contenu = json.loads(Path("donnees/chronologies_v3.json").read_text(encoding="utf-8"))
    ids = [cas["id_signal"] for cas in contenu["chronologies"]]
    assert len(ids) == 10
    assert len(ids) == len(set(ids))


def test_analyse_delais_v3_compte_six_delais_de_parcours():
    contenu = json.loads(Path("donnees/analyse_delais_v3.json").read_text(encoding="utf-8"))
    assert contenu["synthese"]["nombre_chronologies"] == 10
    assert contenu["synthese"]["delais_de_parcours_mesurables"] == 6
    assert sum(1 for cas in contenu["cas"] if cas["delai_parcours_mesurable"]) == 6
    assert contenu["synthese"]["cas_restants_sans_delai_de_parcours"] == ["S001", "S016", "S024", "S042"]


def test_sources_prioritaires_documentees():
    texte = Path("donnees/PREUVES_CHRONOLOGIES_V3.md").read_text(encoding="utf-8")
    for identifiant in ["S001", "S016", "S024", "S038", "S042"]:
        assert identifiant in texte
