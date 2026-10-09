"""Les sources publiques sont consultables sans changer les épisodes du projet."""
import importlib

from fastapi.testclient import TestClient

from app.main import app

MODULE = importlib.import_module("app.main")


def test_consultation_catalogue_metadonnees_publiques(monkeypatch):
    candidat = {
        "id": "abc123",
        "titre": "Laboratoires publics",
        "producteur": "Organisme public",
        "page": "https://www.data.gouv.fr/datasets/abc123/",
        "licence_declaree": "lov2",
        "donnees_actualisees_le": "2026-10-09",
    }
    monkeypatch.setattr(
        MODULE,
        "_charger_sources_publiques",
        lambda: ([candidat], {"controle_le": "2026-10-09T10:00:00+00:00", "pages_echouees": 1}),
    )
    with TestClient(app) as client:
        data = client.get("/api/v1/sources-publiques")
        assert data.status_code == 200
        resultat = data.json()
        assert resultat["total"] == 1
        assert resultat["notices"][0]["id"] == "abc123"
        assert resultat["pages_echouees_derniere_collecte"] == 1
        assert resultat["couverture_exhaustive_du_web"] is False
        assert resultat["contenus_originaux_recopies"] is False
        assert client.get("/api/v1/sources-publiques?terme=inexistant").json()["total"] == 0
        assert client.get("/api/v1/sources-publiques?limite=101").status_code == 422
        assert client.get("/sources-publiques").status_code == 200
        assert "Laboratoires publics" in client.get("/sources-publiques").text
