"""Épreuve hors réseau de l'audit des types de données BOAMP."""
from scripts.auditer_types_champs_boamp import auditer, BOAMP


def test_diagnostic_distingue_listes_et_chaînes():
    rows = [
        {"idweb": "26-100", "dateparution": "2026-09-01",
         "type_marche": ["SERVICES"], "type_marche_facette": "SERVICES"},
        {"idweb": "26-101", "dateparution": "2026-09-02",
         "type_marche": "FOURNITURES", "type_marche_facette": "FOURNITURES"},
    ]

    def source(url, origine):
        assert url.startswith(BOAMP) and origine == BOAMP
        assert "type_marche_facette" in url
        return {"total_count": 2, "results": rows}

    r = auditer(source)
    assert r["enregistrements_examines"] == 2
    assert r["types_python_type_marche"] == {"list": 1, "str": 1}
    assert r["valeurs_apres_normalisation"] == {
        "None": 1, "FOURNITURES": 1,
    }
    assert r["copie_des_notices_integrales"] is False
