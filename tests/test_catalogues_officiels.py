"""Intégrité du registre de catalogues officiels à examiner et à collecter."""
import json
from pathlib import Path
from urllib.parse import urlparse

REGISTRE = Path(__file__).resolve().parents[1] / "institutionnel/decouverte/catalogues_officiels_v1.json"


def test_inventaire_des_catalogues_et_statuts_distincts():
    registre = json.loads(REGISTRE.read_text(encoding="utf-8"))
    entrees = registre["catalogues"]
    assert len(entrees) >= 20
    ids = [x["id"] for x in entrees]
    assert len(set(ids)) == len(ids)
    assert all(x.get("nom") and x.get("producteur") and x.get("objet") for x in entrees)
    for fiche in entrees:
        documentation = urlparse(fiche["documentation"])
        assert documentation.scheme == "https" and documentation.hostname
        assert fiche["statut"]
        if fiche.get("point_entree"):
            url = urlparse(fiche["point_entree"])
            assert url.scheme == "https" and url.hostname


def test_sans_licence_la_republication_n_est_pas_presumee():
    entrees = json.loads(REGISTRE.read_text(encoding="utf-8"))["catalogues"]
    par_id = {x["id"]: x for x in entrees}
    assert "licence_a_verifier" in par_id["dgafp_referentiel_metiers"]["statut"]
    assert "volume" in par_id["insee_sirene"]["statut"] or "volumes" in par_id["insee_sirene"]["statut"]
    assert par_id["ted"]["point_entree"].startswith("https://api.ted.europa.eu/")
