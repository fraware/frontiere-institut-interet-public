import json
from pathlib import Path


def test_analyse_des_delais_couvre_les_dix_chronologies():
    chronologies = json.loads(Path("donnees/chronologies_v1.json").read_text(encoding="utf-8"))
    analyse = json.loads(Path("donnees/analyse_delais_v1.json").read_text(encoding="utf-8"))

    ids_chronologies = {c["id_signal"] for c in chronologies["chronologies"]}
    ids_analyse = {c["id_signal"] for c in analyse["cas"]}

    assert len(ids_chronologies) == 10
    assert ids_analyse == ids_chronologies
    assert analyse["synthese"]["nombre_chronologies"] == 10
    assert analyse["synthese"]["segments_directement_mesurables"] == 3
    assert analyse["synthese"]["segments_non_directement_mesurables"] == 7


def test_chaque_analyse_de_delai_explicite_les_manques():
    analyse = json.loads(Path("donnees/analyse_delais_v1.json").read_text(encoding="utf-8"))
    for cas in analyse["cas"]:
        assert cas["segment_principal"].strip()
        assert isinstance(cas["mesurable"], bool)
        assert cas["observation"].strip()
        assert cas["borne"].strip()
        assert cas["manque"]
