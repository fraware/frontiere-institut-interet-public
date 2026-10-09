"""Consultation des postes publiés, sans accès au fichier d'origine."""
import importlib
import json
from fastapi.testclient import TestClient

from app.main import app

MODULE = importlib.import_module("app.main")


def test_recherche_et_pages_sur_lignes_importees(monkeypatch, tmp_path):
    repertoire = tmp_path / "institutionnel" / "besoins_publics"
    partitions = repertoire / "offres_postes"
    partitions.mkdir(parents=True)
    (repertoire / "manifest_offres_postes.json").write_text(json.dumps({
        "source_id": "source-publique-fictive",
        "extraire_le": "2026-10-09",
        "offres_distinctes": 2,
        "couverture_integrale_du_csv": True,
    }), encoding="utf-8")
    offres = [
        {"reference": "2026-A", "intitule": "Mathématicien appliqué",
         "employeur": "Organisme public", "metier": "Recherche",
         "specialisation": "Statistiques", "localisation": "Paris"},
        {"reference": "2026-B", "intitule": "Technicien de laboratoire",
         "employeur": "Université publique", "metier": "Analyse",
         "specialisation": "Chimie", "localisation": "Lyon"},
    ]
    for i, offre in enumerate(offres):
        (partitions / f"lot_{i:02x}.jsonl").write_text(
            json.dumps(offre, ensure_ascii=False) + "\n", encoding="utf-8",
        )
    racine = tmp_path / "app"
    racine.mkdir()
    monkeypatch.setattr(MODULE, "BASE_DIR", racine)
    with TestClient(app) as client:
        res = client.get("/api/v1/offres-emplois")
        assert res.status_code == 200
        assert res.json()["total"] == 2
        assert res.json()["fichier_brut_reproduit"] is False
        filtrage = client.get("/api/v1/offres-emplois?terme=statistiques")
        assert filtrage.json()["total"] == 1
        assert filtrage.json()["offres"][0]["intitule"] == "Mathématicien appliqué"
        assert client.get("/api/v1/offres-emplois?limite=101").status_code == 422
        page = client.get("/offres-emplois?terme=chimie")
        assert page.status_code == 200
        assert "Technicien de laboratoire" in page.text
