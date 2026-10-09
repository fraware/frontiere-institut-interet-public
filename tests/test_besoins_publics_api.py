"""Le site distingue les annonces et les références aux fichiers d'offres."""
import importlib

from fastapi.testclient import TestClient
from app.main import app

MODULE = importlib.import_module("app.main")


def test_api_besoins_publics_et_page(monkeypatch):
    annonce = {
        "id": "26-abc",
        "objet": "Étude scientifique",
        "acheteur": "Administration publique",
        "date_parution": "2026-10-09",
        "avis": "https://www.boamp.fr/",
        "catalogue_source": "https://boamp-datadila.opendatasoft.com/explore/dataset/boamp/",
    }
    def source(nom):
        if nom == "marches":
            return [annonce], {"controle_le": "2026-10-09", "recherche_partielle": True}
        return [{"id": "12345", "titre": "offres.csv", "url": None,
                 "modifie_le": "2026-10-05"}], {"controle_le": "2026-10-09"}

    monkeypatch.setattr(MODULE, "_lire_besoins_publics", source)
    with TestClient(app) as client:
        rep = client.get("/api/v1/besoins-publics")
        assert rep.status_code == 200
        assert rep.json()["total"] == 1
        assert rep.json()["collecte_partielle"] is True
        assert rep.json()["fichiers_integraux_recopies"] is False
        assert client.get("/api/v1/besoins-publics?page=0").status_code == 422
        assert client.get("/api/v1/besoins-publics?source=emplois").json()["total"] == 1
        html = client.get("/besoins-publics")
        assert html.status_code == 200
        assert "Étude scientifique" in html.text
        assert "Le relevé est partiel" in html.text
        assert client.get("/besoins-publics?source=emplois").status_code == 200
