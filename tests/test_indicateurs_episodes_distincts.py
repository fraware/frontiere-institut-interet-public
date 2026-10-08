"""Le nombre de mises à jour ne doit pas augmenter celui des épisodes observés."""
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Discovery, Episode, EpisodeResult, Organization, Resource, SearchRun
from app.services import dashboard_metrics, empirical_metrics


def test_indicateurs_compter_les_episodes_sans_doubler_les_revisions():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        institution = Organization(name="Institution du test d'indicateurs")
        db.add(institution)
        db.flush()
        ep_a = Episode(code="EP-A-MET", organization_id=institution.id, title="Premier besoin", synthetic=False)
        ep_b = Episode(code="EP-B-MET", organization_id=institution.id, title="Second besoin", synthetic=False)
        ep_fictif = Episode(code="EP-F-MET", organization_id=institution.id, title="Démonstration", synthetic=True)
        db.add_all([ep_a, ep_b, ep_fictif])
        db.flush()
        p1 = SearchRun(episode_id=ep_a.id, search_type="PUBLIQUE", public_result="P1")
        p3 = SearchRun(episode_id=ep_a.id, search_type="PUBLIQUE", public_result="P3")
        p2 = SearchRun(episode_id=ep_b.id, search_type="PUBLIQUE", public_result="P2")
        faux = SearchRun(episode_id=ep_fictif.id, search_type="PUBLIQUE", public_result="P3")
        db.add_all([p1, p3, p2, faux])
        db.flush()
        db.add_all([
            EpisodeResult(episode_id=ep_a.id, result_status="ANCIEN", outcome_description="Première version",
                          dominant_friction="FRICTION_ANCIENNE"),
            EpisodeResult(episode_id=ep_a.id, result_status="FINAL", outcome_description="Version récente",
                          dominant_friction="FRICTION_NOUVELLE"),
            EpisodeResult(episode_id=ep_b.id, result_status="PENDANT", outcome_description="État actuel"),
            EpisodeResult(episode_id=ep_fictif.id, result_status="FICTIF", outcome_description="Essai"),
        ])
        resource = Resource(resource_type="EQUIPE", display_name="Ressource de test", sensitivity_level=1)
        db.add(resource)
        db.flush()
        db.add_all([
            Discovery(search_run_id=p1.id, resource_id=resource.id, state="R5"),
            Discovery(search_run_id=p2.id, resource_id=resource.id, state="R5"),
            Discovery(search_run_id=faux.id, resource_id=resource.id, state="R5"),
        ])
        db.commit()

    with SessionLocal() as db:
        tableau = dashboard_metrics(db)
        terrain = empirical_metrics(db)
    assert tableau["episodes"] == 2
    assert tableau["public_results"] == {"P3": 1, "P2": 1}
    assert tableau["public_search_records"] == 3
    assert tableau["public_search_episodes"] == 2
    assert tableau["results"] == 3
    assert tableau["result_episodes"] == 2
    assert terrain["public_results"] == tableau["public_results"]
    assert terrain["result_records"] == 3
    assert terrain["result_episodes"] == 2
    assert terrain["result_statuses"] == {"FINAL": 1, "PENDANT": 1}
    assert terrain["dominant_frictions"] == {"FRICTION_NOUVELLE": 1}
    assert terrain["r5"] == 1
    assert terrain["r5_observations"] == 2
    with TestClient(app) as client:
        metrics = client.get("/api/v1/metrics").json()
        assert metrics["result_episodes"] == 2
        assert "Épisodes avec résultat" in client.get("/").text
        assert "Ressources distinctes signalées au stade R5" in client.get("/donnees-terrain").text
