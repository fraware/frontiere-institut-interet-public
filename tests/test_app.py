from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import AuditEvent, BenchmarkCase, BenchmarkPrediction, CapabilityQuery, Episode, EpisodeResult, KnowledgeItem, NeedVersion, Organization, ReuseEvent


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_health():
    reset_db()
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert r.json()["version"] == "0.5.2"


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


def _create_locked_episode(client, title="Cas terrain"):
    r = client.post(
        "/episodes",
        data={
            "organization_name": "Administration terrain",
            "title": title,
            "current_situation": "Situation réelle à qualifier",
            "desired_outcome": "Résultat observable",
            "demand_level": "D2",
            "sensitivity_level": "1",
            "need_preexisting_frontiere": "yes",
            "sponsor": "Responsable",
            "counterfactual_plan": "Voie ordinaire",
            "initial_frontiere_hypothesis": "Recherche publique d'abord",
        },
        follow_redirects=False,
    )
    location = r.headers["location"]
    assert client.post(location + "/need/lock", follow_redirects=False).status_code == 303
    return location


def test_resource_progression_and_r5_gate():
    reset_db()
    with TestClient(app) as client:
        location = _create_locked_episode(client)
        skipped = client.post(
            location + "/resource",
            data={"resource_type": "PERSONNE", "display_name": "Profil A", "state": "R2", "state_reason": "expertise vérifiée"},
            follow_redirects=False,
        )
        assert skipped.status_code == 409

        assert client.post(location + "/resource", data={"resource_type": "PERSONNE", "display_name": "Profil A", "state": "R0"}, follow_redirects=False).status_code == 303
        assert client.post(location + "/resource", data={"resource_type": "PERSONNE", "display_name": "Profil A", "state": "R1"}, follow_redirects=False).status_code == 303
        assert client.post(location + "/resource", data={"resource_type": "PERSONNE", "display_name": "Profil A", "state": "R2"}, follow_redirects=False).status_code == 409
        assert client.post(location + "/resource", data={"resource_type": "PERSONNE", "display_name": "Profil A", "state": "R2", "state_reason": "capacité vérifiée"}, follow_redirects=False).status_code == 303
        assert client.post(location + "/resource", data={"resource_type": "PERSONNE", "display_name": "Profil A", "state": "R3", "state_reason": "conditions compatibles"}, follow_redirects=False).status_code == 303
        assert client.post(location + "/resource", data={"resource_type": "PERSONNE", "display_name": "Profil A", "state": "R4", "state_reason": "engagement confirmé"}, follow_redirects=False).status_code == 303

        r5_blocked = client.post(
            location + "/resource",
            data={"resource_type": "PERSONNE", "display_name": "Profil A", "state": "R5", "state_reason": "mobilisable"},
            follow_redirects=False,
        )
        assert r5_blocked.status_code == 409
        r5 = client.post(
            location + "/resource",
            data={
                "resource_type": "PERSONNE",
                "display_name": "Profil A",
                "state": "R5",
                "state_reason": "mobilisable pour la mission",
                "mission_specific_interest": "yes",
                "available_as_of": "2026-10-04",
            },
            follow_redirects=False,
        )
        assert r5.status_code == 303
        assert "R5" in client.get(location).text


def test_result_captures_first_value_and_additionality():
    reset_db()
    with TestClient(app) as client:
        location = _create_locked_episode(client, "Cas résultat")
        response = client.post(
            location + "/result",
            data={
                "result_status": "RESOLU",
                "actual_intervention": "Expertise ponctuelle",
                "actual_route": "Capacité publique",
                "outcome_description": "Décision prise avec expertise documentée.",
                "dominant_friction": "F1_COMPETENCE",
                "first_useful_contribution_at": "2026-10-04T10:30",
                "direct_cost_eur": "250.50",
                "frontiere_minutes": "90",
                "institution_minutes": "45",
                "additionality_outcome": "FORTE",
                "additionality_time": "MODEREE",
                "additionality_quality": "FORTE",
                "additionality_cost": "FAIBLE",
                "additionality_learning": "MODEREE",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    with SessionLocal() as db:
        result = db.scalar(select(EpisodeResult))
        assert result is not None
        assert result.direct_cost_eur == 250.50
        assert result.first_useful_contribution_at is not None
        assert result.additionality_outcome == "FORTE"
        assert result.additionality_time == "MODEREE"


def test_cross_case_reuse_and_empirical_dashboard():
    reset_db()
    with TestClient(app) as client:
        source = _create_locked_episode(client, "Cas source")
        assert client.post(
            source + "/knowledge",
            data={"knowledge_type": "PRECEDENT", "title": "Voie utile", "content": "Un précédent réutilisable", "evidence_level": "B"},
            follow_redirects=False,
        ).status_code == 303
        target = _create_locked_episode(client, "Cas cible")

        with SessionLocal() as db:
            knowledge = db.scalar(select(KnowledgeItem).where(KnowledgeItem.title == "Voie utile"))
            assert knowledge is not None
            knowledge_id = knowledge.id

        reused = client.post(
            target + "/reuse",
            data={
                "knowledge_id": str(knowledge_id),
                "decision_changed": "yes",
                "estimated_minutes_saved": "35",
                "accessible_to_new_analyst": "yes",
                "effect_description": "Le précédent a évité une recherche redondante.",
            },
            follow_redirects=False,
        )
        assert reused.status_code == 303
        page = client.get(target)
        assert "Le précédent a évité une recherche redondante." in page.text

        empirical = client.get("/empirique")
        assert empirical.status_code == 200
        assert "Tableau empirique" in empirical.text
        assert "2" in empirical.text

    with SessionLocal() as db:
        reuse = db.scalar(select(ReuseEvent))
        assert reuse is not None
        assert reuse.decision_changed is True
        assert reuse.estimated_minutes_saved == 35


def test_capability_query_compilation():
    reset_db()
    with TestClient(app) as client:
        location = _create_locked_episode(client, "Cas capacité")
        response = client.post(
            location + "/capability-query",
            data={
                "raw_request": "Évaluer rapidement une technologie pour une décision publique.",
                "domain": "technologies numériques",
                "function": "évaluation technique",
                "depth": "expert",
                "operational_context": "décision avant comité",
                "constraints": "français, 10 jours",
                "resource_forms": "PERSONNE, EQUIPE, LABORATOIRE",
                "must_have": "expérience d'évaluation, expertise technique",
                "nice_to_have": "contexte public",
                "latest_useful_date": "2026-10-20",
                "compiler": "human",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        api = client.get(location.replace("/episodes/", "/api/v1/episodes/") + "/capability-query")
        assert api.status_code == 200
        payload = api.json()
        assert payload["domain"] == "technologies numériques"
        assert payload["function"] == "évaluation technique"
        assert payload["resource_forms"] == ["PERSONNE", "EQUIPE", "LABORATOIRE"]

    with SessionLocal() as db:
        query = db.scalar(select(CapabilityQuery))
        assert query is not None
        assert query.locked_at is not None


def test_benchmark_is_blind_until_prediction_and_scores_vector():
    reset_db()
    with SessionLocal() as db:
        case = BenchmarkCase(
            code="BTEST",
            title="Cas test",
            source_url="https://example.org/hidden-source",
            prompt="Trouver une voie et une forme de ressource.",
            expected_routes_json='["ROUTAGE", "RECHERCHE_PUBLIQUE"]',
            expected_resource_forms_json='["EQUIPE", "LABORATOIRE"]',
            expected_resources_json='[]',
            outcome_summary="Solution connue masquée avant prédiction.",
        )
        db.add(case)
        db.commit()

    with TestClient(app) as client:
        before = client.get("/benchmark")
        assert before.status_code == 200
        assert "https://example.org/hidden-source" not in before.text
        assert "RECHERCHE_PUBLIQUE" not in before.text

        submitted = client.post(
            "/benchmark/BTEST/prediction",
            data={
                "method": "frontiere-v0.5",
                "method_version": "0.5",
                "routes": "ROUTAGE, RECHERCHE_PUBLIQUE",
                "resource_forms": "EQUIPE",
                "resources": "",
                "evidence_urls": "https://example.org/evidence",
                "elapsed_seconds": "12.5",
                "analyst_minutes": "5",
                "verification_minutes": "3",
            },
            follow_redirects=False,
        )
        assert submitted.status_code == 303
        sealed = client.get("/benchmark")
        assert "https://example.org/hidden-source" not in sealed.text
        assert "Des prédictions sont enregistrées" in sealed.text

        duplicate = client.post(
            "/benchmark/BTEST/prediction",
            data={"method": "frontiere-v0.5", "method_version": "0.5"},
            follow_redirects=False,
        )
        assert duplicate.status_code == 409

        blind_api = client.get("/api/v1/benchmark/blind")
        assert blind_api.status_code == 200
        blind_case = blind_api.json()["cases"][0]
        assert "source_url" not in blind_case
        assert "expected_routes" not in blind_case

        reveal = client.post("/benchmark/BTEST/reveal", follow_redirects=False)
        assert reveal.status_code == 303
        after = client.get("/benchmark")
        assert "https://example.org/hidden-source" in after.text
        assert "100%" in after.text
        api = client.get("/api/v1/benchmark")
        assert api.status_code == 200
        assert api.json()["case_count"] == 1
        assert api.json()["prediction_count"] == 1
        method = api.json()["methods"][0]
        assert method["route_recall_mean"] == 1.0
        assert method["route_precision_mean"] == 1.0
        assert method["route_f1_mean"] == 1.0
        assert method["resource_form_recall_mean"] == 0.5
        assert method["resource_form_precision_mean"] == 1.0
        assert round(method["resource_form_f1_mean"], 6) == round(2/3, 6)
        assert method["human_minutes_median"] == 8

    with SessionLocal() as db:
        prediction = db.scalar(select(BenchmarkPrediction))
        assert prediction is not None
        assert prediction.method == "frontiere-v0.5"


def test_benchmark_cannot_reveal_without_prediction():
    reset_db()
    with SessionLocal() as db:
        db.add(BenchmarkCase(
            code="BSEALED",
            title="Cas scellé",
            prompt="Trouver une voie.",
            expected_routes_json='["ROUTAGE"]',
            expected_resource_forms_json='["EQUIPE"]',
            expected_resources_json='[]',
        ))
        db.commit()
    with TestClient(app) as client:
        reveal = client.post("/benchmark/BSEALED/reveal", follow_redirects=False)
        assert reveal.status_code == 409
        page = client.get("/benchmark")
        assert "ROUTAGE" not in page.text


def test_benchmark_precision_penalizes_overprediction():
    reset_db()
    with SessionLocal() as db:
        case = BenchmarkCase(
            code="BPREC",
            title="Cas précision",
            prompt="Trouver une voie.",
            expected_routes_json='["ROUTAGE"]',
            expected_resource_forms_json='["EQUIPE"]',
            expected_resources_json='[]',
        )
        db.add(case)
        db.flush()
        db.add(BenchmarkPrediction(
            case_id=case.id,
            method="surprediction",
            routes_json='["ROUTAGE", "RECRUTEMENT", "ACHAT"]',
            resource_forms_json='["EQUIPE", "PERSONNE"]',
            resources_json='[]',
            evidence_urls_json='[]',
        ))
        db.commit()
    with TestClient(app) as client:
        data = client.get("/api/v1/benchmark").json()
        method = data["methods"][0]
        assert method["route_recall_mean"] == 1.0
        assert round(method["route_precision_mean"], 6) == round(1/3, 6)
        assert method["route_f1_mean"] == 0.5
        assert method["resource_form_recall_mean"] == 1.0
        assert method["resource_form_precision_mean"] == 0.5
        assert round(method["resource_form_f1_mean"], 6) == round(2/3, 6)
