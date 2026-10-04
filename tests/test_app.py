from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import AuditEvent, Episode, NeedVersion, Organization


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_health():
    reset_db()
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert r.json()["version"] == "0.3.0"


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
        r = client.post(location + "/need/lock", follow_redirects=False)
        assert r.status_code == 303
        r = client.post(
            location + "/public-search",
            data={"complete": "yes", "relevant_found": "yes", "mobilizable_found": "no", "analyst_minutes": "45"},
            follow_redirects=False,
        )
        assert r.status_code == 303
        page = client.get(location)
        assert "P2" in page.text


def test_search_blocked_until_need_is_locked():
    reset_db()
    with TestClient(app) as client:
        r = client.post(
            "/episodes",
            data={
                "organization_name": "Administration test",
                "organizational_unit": "Unité A",
                "title": "Besoin à pré-enregistrer",
                "current_situation": "Situation documentée",
                "desired_outcome": "Décision exploitable",
                "demand_level": "D2",
                "sensitivity_level": "1",
                "need_preexisting_frontiere": "yes",
                "sponsor": "Responsable",
                "counterfactual_plan": "Recrutement ordinaire",
                "initial_frontiere_hypothesis": "Mobilité publique",
            },
            follow_redirects=False,
        )
        location = r.headers["location"]
        blocked = client.post(location + "/public-search", data={"complete": "no"}, follow_redirects=False)
        assert blocked.status_code == 409
        locked = client.post(location + "/need/lock", follow_redirects=False)
        assert locked.status_code == 303


def test_public_prototype_rejects_sensitive_episode():
    reset_db()
    with TestClient(app) as client:
        r = client.post(
            "/episodes",
            data={
                "organization_name": "Administration test",
                "title": "Cas sensible",
                "current_situation": "Situation",
                "desired_outcome": "Résultat",
                "demand_level": "D2",
                "sensitivity_level": "3",
                "need_preexisting_frontiere": "yes",
                "counterfactual_plan": "Voie existante",
                "initial_frontiere_hypothesis": "Hypothèse",
            },
        )
        assert r.status_code == 400


def test_evidence_registry_and_contacts():
    reset_db()
    with TestClient(app) as client:
        episode = client.post(
            "/episodes",
            data={
                "organization_name": "Administration test",
                "title": "Cas avec preuve",
                "current_situation": "Situation",
                "desired_outcome": "Résultat",
                "demand_level": "D2",
                "sensitivity_level": "1",
                "need_preexisting_frontiere": "yes",
                "counterfactual_plan": "Voie existante",
                "initial_frontiere_hypothesis": "Hypothèse",
            },
            follow_redirects=False,
        )
        location = episode.headers["location"]
        r = client.post(location + "/evidence", data={"title": "Note datée", "quality": "A", "data_environment": "RECHERCHE", "sensitivity_level": "1"}, follow_redirects=False)
        assert r.status_code == 303
        assert "Note datée" in client.get(location).text

        r = client.post(
            "/contacts",
            data={
                "institution": "DINUM",
                "function": "Fonction test",
                "priority": "1",
                "hypothesis_tested": "Tester une friction",
                "single_ask": "Obtenir un cas",
                "minimal_success": "Un épisode documentable",
            },
            follow_redirects=False,
        )
        assert r.status_code == 303
        page = client.get("/contacts")
        assert "DINUM" in page.text
        assert "Un épisode documentable" in page.text


def test_research_export_excludes_synthetic():
    reset_db()
    with SessionLocal() as db:
        org = Organization(name="Synthétique", public_sector=False)
        db.add(org); db.flush()
        db.add(Episode(code="TEST-SYN", organization_id=org.id, title="Synth", synthetic=True, demand_level="D3"))
        db.commit()
    with TestClient(app) as client:
        export = client.get("/api/v1/research-export")
        assert export.status_code == 200
        assert export.json()["episodes"] == []


def test_need_revision_preserves_history_and_audit():
    reset_db()
    with TestClient(app) as client:
        r = client.post(
            "/episodes",
            data={
                "organization_name": "Administration test",
                "title": "Besoin versionné",
                "current_situation": "Situation initiale",
                "desired_outcome": "Résultat initial",
                "demand_level": "D2",
                "sensitivity_level": "1",
                "need_preexisting_frontiere": "yes",
                "sponsor": "Responsable",
                "counterfactual_plan": "Recrutement ordinaire",
                "initial_frontiere_hypothesis": "Mobilité publique",
            },
            follow_redirects=False,
        )
        location = r.headers["location"]
        assert client.post(location + "/need/lock", follow_redirects=False).status_code == 303
        revised = client.post(
            location + "/need/revise",
            data={
                "revision_reason": "Une preuve nouvelle précise le problème.",
                "current_situation": "Situation révisée",
                "desired_outcome": "Résultat initial",
                "sponsor": "Responsable",
                "counterfactual_plan": "Recrutement ordinaire",
                "initial_frontiere_hypothesis": "Mobilité publique puis expertise ponctuelle",
            },
            follow_redirects=False,
        )
        assert revised.status_code == 303

    with SessionLocal() as db:
        versions = db.scalars(select(NeedVersion).order_by(NeedVersion.version)).all()
        assert len(versions) == 2
        assert versions[0].version == 1 and versions[0].active is False and versions[0].locked_at is not None
        assert versions[1].version == 2 and versions[1].active is True and versions[1].locked_at is not None
        events = db.scalars(select(AuditEvent).where(AuditEvent.event_type == "BESOIN_REVISE")).all()
        assert len(events) == 1
        assert '"from_version": 1' in (events[0].payload_json or "")
        assert '"to_version": 2' in (events[0].payload_json or "")


def test_resource_entry_requires_locked_need():
    reset_db()
    with TestClient(app) as client:
        r = client.post(
            "/episodes",
            data={
                "organization_name": "Administration test",
                "title": "Besoin non verrouillé",
                "current_situation": "Situation",
                "desired_outcome": "Résultat",
                "demand_level": "D2",
                "sensitivity_level": "1",
                "need_preexisting_frontiere": "yes",
                "counterfactual_plan": "Voie existante",
                "initial_frontiere_hypothesis": "Hypothèse",
            },
            follow_redirects=False,
        )
        location = r.headers["location"]
        blocked = client.post(
            location + "/resource",
            data={"resource_type": "PERSONNE", "display_name": "Ressource test", "state": "R0"},
            follow_redirects=False,
        )
        assert blocked.status_code == 409


def test_search_writes_audit_event_with_need_version():
    reset_db()
    with TestClient(app) as client:
        r = client.post(
            "/episodes",
            data={
                "organization_name": "Administration test",
                "title": "Besoin audité",
                "current_situation": "Situation",
                "desired_outcome": "Résultat",
                "demand_level": "D2",
                "sensitivity_level": "1",
                "need_preexisting_frontiere": "yes",
                "counterfactual_plan": "Voie existante",
                "initial_frontiere_hypothesis": "Hypothèse",
            },
            follow_redirects=False,
        )
        location = r.headers["location"]
        client.post(location + "/need/lock", follow_redirects=False)
        client.post(
            location + "/public-search",
            data={"complete": "yes", "relevant_found": "yes", "mobilizable_found": "no", "analyst_minutes": "12"},
            follow_redirects=False,
        )
    with SessionLocal() as db:
        event = db.scalar(select(AuditEvent).where(AuditEvent.event_type == "RECHERCHE_PUBLIQUE_ENREGISTREE"))
        assert event is not None
        assert '"public_result": "P2"' in (event.payload_json or "")
        assert '"need_version_id":' in (event.payload_json or "")
