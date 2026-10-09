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



def test_etat_balayage_national_ne_pretend_pas_une_exhaustivite(monkeypatch, tmp_path):
    module = MODULE
    (tmp_path / "institutionnel" / "decouverte" / "balayage_pages").mkdir(parents=True)
    racine = tmp_path / "app"
    racine.mkdir()
    (tmp_path / "institutionnel" / "decouverte" / "balayage_etat.json").write_text(
        '{"controle_le":"2026-10-09","page_suivante":31,"cycles_acheves":0,'
        '"nombre_total_jeux_declare_par_catalogue":75000,"erreurs":[]}',
        encoding="utf-8",
    )
    (tmp_path / "institutionnel" / "decouverte" / "balayage_pages" / "page_00001.jsonl").write_text(
        '{"id":"un-test"}\n', encoding="utf-8",
    )
    monkeypatch.setattr(module, "BASE_DIR", racine)
    with TestClient(app) as client:
        res = client.get("/api/v1/balayage-national")
        assert res.status_code == 200
        data = res.json()
        assert data["page_suivante"] == 31
        assert data["nombre_pages_presentes"] == 1
        assert data["catalogue_exhaustif_atteste"] is False
        assert data["donnees_brutes_copiees"] is False


def test_navigation_pages_generales_sans_lire_toute_la_collection(monkeypatch, tmp_path):
    import json
    repertoire = tmp_path / "institutionnel" / "decouverte"
    pages = repertoire / "balayage_pages"
    pages.mkdir(parents=True)
    (repertoire / "balayage_etat.json").write_text(
        '{"controle_le":"2026-10-09T16:00:00+00:00",'
        '"page_suivante":2,"cycles_acheves":0,"erreurs":[]}',
        encoding="utf-8",
    )
    notices = [{
        "id": "jeu-00001",
        "titre": "Atlas des capacités scientifiques",
        "producteur": "Producteur public",
        "page": "https://www.data.gouv.fr/datasets/jeu-00001/",
        "licence": "lov2",
        "actualise_le": "2026-10-09T00:00:00+00:00",
    }]
    (pages / "page_00001.jsonl").write_text(
        json.dumps(notices[0], ensure_ascii=False) + "\n", encoding="utf-8",
    )
    racine = tmp_path / "app"
    racine.mkdir()
    monkeypatch.setattr(MODULE, "BASE_DIR", racine)
    with TestClient(app) as client:
        rep = client.get("/api/v1/catalogue-national?page=1")
        assert rep.status_code == 200
        assert rep.json()["page_presente"] is True
        assert rep.json()["notices"][0]["titre"] == "Atlas des capacités scientifiques"
        assert rep.json()["couverture_complete_attestee"] is False
        absent = client.get("/api/v1/catalogue-national?page=2")
        assert absent.status_code == 200 and absent.json()["page_presente"] is False
        assert client.get("/api/v1/catalogue-national?page=2001").status_code == 422
        page = client.get("/catalogue-national")
        assert page.status_code == 200
        assert "Atlas des capacités scientifiques" in page.text
        assert "Page suivante" in page.text



def test_catalogue_scientifique_sur_site(monkeypatch, tmp_path):
    import json
    dossier = tmp_path / "institutionnel" / "decouverte"
    dossier.mkdir(parents=True)
    (dossier / "catalogue_mesr.json").write_text(
        json.dumps({"notices": [{
            "id": "fr-esr-essai", "titre": "Laboratoires expérimentaux",
            "page": "https://data.enseignementsup-recherche.gouv.fr/explore/dataset/fr-esr-essai/",
            "modifie_le": "2026-10-09", "licence_declaree": "Licence Ouverte",
        }]}, ensure_ascii=False), encoding="utf-8",
    )
    (dossier / "catalogue_mesr_etat.json").write_text(
        '{"controle_le":"2026-10-09","exhaustivite_constatee":false}', encoding="utf-8",
    )
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    monkeypatch.setattr(MODULE, "BASE_DIR", app_dir)
    with TestClient(app) as client:
        resultat = client.get("/api/v1/catalogue-recherche")
        assert resultat.status_code == 200
        assert resultat.json()["total"] == 1
        assert resultat.json()["fichiers_bruts_copies"] is False
        assert client.get("/api/v1/catalogue-recherche?limite=101").status_code == 422
        page = client.get("/sources-recherche")
        assert page.status_code == 200
        assert "Laboratoires expérimentaux" in page.text
