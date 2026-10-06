import json
from pathlib import Path


def test_chronologies_v2_couvrent_les_dix_cas():
    contenu = json.loads(Path("donnees/chronologies_v2.json").read_text(encoding="utf-8"))
    ids = [cas["id_signal"] for cas in contenu["chronologies"]]
    assert len(ids) == 10
    assert len(ids) == len(set(ids))


def test_analyse_delais_v2_est_coherente():
    contenu = json.loads(Path("donnees/analyse_delais_v2.json").read_text(encoding="utf-8"))
    assert contenu["synthese"]["nombre_chronologies"] == 10
    assert contenu["synthese"]["delais_de_parcours_mesurables"] == 5
    assert contenu["synthese"]["durees_structurelles_mesurables"] == 10
    assert sum(1 for cas in contenu["cas"] if cas["delai_parcours_mesurable"]) == 5


def test_preuves_chronologies_v2_documentees():
    texte = Path("donnees/PREUVES_CHRONOLOGIES_V2.md").read_text(encoding="utf-8")
    for identifiant in ["S016", "S018", "S024", "S038", "S042", "S027"]:
        assert identifiant in texte
