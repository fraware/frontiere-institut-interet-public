from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Episode, Organization


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_health():
    reset_db()
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


def test_create_episode_and_public_search():
    reset_db()
    with TestClient(app) as client:
        r = client.post(
            "/episodes",
            data={
                "organization_name": "Administration test",
                "organizational_unit": "Unité A",
                "title": "Besoin scientifique précis",
                "current_situation": "Une décision opérationnelle dépend d'une capacité absente au moment utile.",
                "desired_outcome": "Obtenir une orientation documentée.",
                "demand_level": "D2",
                "sensitivity_level": "1",
                "need_preexisting_frontiere": "yes",
                "sponsor": "Responsable test",
                "counterfactual_plan": "Recrutement classique.",
                "initial_frontiere_hypothesis": "Mobilité publique possible.",
            },
            follow_redirects=False,
        )
        assert r.status_code == 303
        location = r.headers["location"]
        assert location.startswith("/episodes/EP-")
        r = client.post(
            location + "/public-search",
            data={"complete": "yes", "relevant_found": "yes", "mobilizable_found": "no", "analyst_minutes": "45"},
            follow_redirects=False,
        )
        assert r.status_code == 303
        page = client.get(location)
        assert "P2" in page.text
