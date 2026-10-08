import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import AuditEvent, BenchmarkCase, BenchmarkPrediction, CapabilityQuery, Episode, EpisodeResult, KnowledgeItem, NeedVersion, Organization, ReuseEvent, RouteAssessment, SearchRun


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_health():
    reset_db()
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert r.json()["version"] == "0.5.4"


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
        assert "Capacité publique trouvée, mobilisation difficile" in page.text


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

        empirical = client.get("/donnees-terrain")
        assert empirical.status_code == 200
        assert "Données de terrain" in empirical.text
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
        before = client.get("/evaluation")
        assert before.status_code == 200
        assert "https://example.org/hidden-source" not in before.text
        assert "RECHERCHE_PUBLIQUE" not in before.text

        submitted = client.post(
            "/evaluation/BTEST/reponse",
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
        sealed = client.get("/evaluation")
        assert "https://example.org/hidden-source" not in sealed.text
        assert "Des prédictions sont enregistrées" in sealed.text
        assert "Comparaison des méthodes" in sealed.text
        # Les moyennes ne doivent pas divulguer les étiquettes du cas scellé.
        avant_revelation = client.get("/api/v1/evaluation").json()
        assert avant_revelation["prediction_count"] == 1
        assert avant_revelation["sealed_prediction_count"] == 1
        assert avant_revelation["scored_prediction_count"] == 0
        assert avant_revelation["methods"] == []

        duplicate = client.post(
            "/evaluation/BTEST/reponse",
            data={"method": "frontiere-v0.5", "method_version": "0.5"},
            follow_redirects=False,
        )
        assert duplicate.status_code == 409

        blind_api = client.get("/api/v1/evaluation/aveugle")
        assert blind_api.status_code == 200
        blind_case = blind_api.json()["cases"][0]
        assert "source_url" not in blind_case
        assert "expected_routes" not in blind_case

        reveal = client.post("/evaluation/BTEST/reveler", follow_redirects=False)
        assert reveal.status_code == 303
        after = client.get("/evaluation")
        assert "https://example.org/hidden-source" in after.text
        assert "100%" in after.text
        assert 'action="/evaluation/BTEST/reponse"' not in after.text
        assert "nouvelles réponses sont bloquées" in after.text
        contribution_tardive = client.post(
            "/evaluation/BTEST/reponse",
            data={
                "method": "assistant-tardif", "method_version": "1.0",
                "routes": "ROUTAGE, RECHERCHE_PUBLIQUE",
                "resource_forms": "EQUIPE, LABORATOIRE",
            },
            follow_redirects=False,
        )
        assert contribution_tardive.status_code == 409
        api = client.get("/api/v1/evaluation")
        assert api.status_code == 200
        assert api.json()["case_count"] == 1
        assert api.json()["prediction_count"] == 1
        assert api.json()["sealed_prediction_count"] == 0
        assert api.json()["scored_prediction_count"] == 1
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
        reveal = client.post("/evaluation/BSEALED/reveler", follow_redirects=False)
        assert reveal.status_code == 409
        page = client.get("/evaluation")
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
            revealed=True,
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
        data = client.get("/api/v1/evaluation").json()
        method = data["methods"][0]
        assert method["route_recall_mean"] == 1.0
        assert round(method["route_precision_mean"], 6) == round(1/3, 6)
        assert method["route_f1_mean"] == 0.5
        assert method["resource_form_recall_mean"] == 1.0
        assert method["resource_form_precision_mean"] == 0.5
        assert round(method["resource_form_f1_mean"], 6) == round(2/3, 6)


def test_holdout_prediction_template_covers_all_cases():
    import json
    from pathlib import Path

    payload = json.loads(Path("evaluation/modele_reponses.json").read_text(encoding="utf-8"))
    codes = [row["code"] for row in payload["cas"]]
    assert payload["version_schema"] == "reponses-jeu-reserve-v1"
    assert codes == [f"H{i:02d}" for i in range(1, 11)]
    assert len(set(codes)) == 10

    manifest = json.loads(Path("evaluation/jeu_reserve_v1_manifeste.json").read_text(encoding="utf-8"))
    assert manifest["nombre_cas"] == 10
    assert len(manifest["empreinte_sha256_references"]) == 64


def _create_prospective_candidate(client):
    response = client.post(
        "/episodes",
        data={
            "organization_name": "Administration prospective",
            "organizational_unit": "Direction test",
            "title": "Besoin prospectif réel",
            "current_situation": "Une mission actuelle exige une expertise technique qui n'est pas disponible dans l'équipe.",
            "desired_outcome": "Identifier et mobiliser une ressource avant l'échéance opérationnelle.",
            "demand_level": "D2",
            "sensitivity_level": "1",
            "need_preexisting_frontiere": "yes",
            "sponsor": "Responsable opérationnel",
            "latest_useful_date": "2026-10-20",
            "counterfactual_plan": "Poursuivre la recherche manuelle et le recrutement ordinaire.",
            "initial_frontiere_hypothesis": "Une capacité publique existante peut être identifiée avant une recherche extérieure.",
        },
        follow_redirects=False,
    )
    location = response.headers["location"]
    preuve = client.post(
        location + "/evidence",
        data={
            "title": "Note initiale du responsable",
            "evidence_type": "note",
            "source": "responsable opérationnel",
            "evidence_date": "2026-10-07",
            "quality": "B",
            "sensitivity_level": "1",
            "data_environment": "RECHERCHE",
        },
        follow_redirects=False,
    )
    assert preuve.status_code == 303
    return location


def test_prospective_baseline_requires_complete_point_zero():
    reset_db()
    with TestClient(app) as client:
        response = client.post(
            "/episodes",
            data={
                "organization_name": "Administration prospective incomplète",
                "title": "Besoin incomplet",
                "current_situation": "Situation actuelle suffisamment décrite.",
                "desired_outcome": "Résultat observable.",
                "demand_level": "D2",
                "sensitivity_level": "1",
                "need_preexisting_frontiere": "unknown",
                "counterfactual_plan": "Voie ordinaire.",
                "initial_frontiere_hypothesis": "Hypothèse initiale.",
            },
            follow_redirects=False,
        )
        location = response.headers["location"]
        locked = client.post(location + "/prospective/lock", follow_redirects=False)
        assert locked.status_code == 409
        detail = locked.json()["detail"]
        assert "responsable opérationnel" in detail
        assert "préexistence du besoin" in detail
        assert "échéance utile" in detail
        assert "preuve initiale" in detail


def test_prospective_baseline_is_hashed_and_auditable():
    reset_db()
    with TestClient(app) as client:
        location = _create_prospective_candidate(client)
        locked = client.post(location + "/prospective/lock", follow_redirects=False)
        assert locked.status_code == 303
        api = client.get(location.replace("/episodes/", "/api/v1/episodes/") + "/preregistration")
        assert api.status_code == 200
        payload = api.json()["prospective_baseline"]["payload"]
        assert payload["schema_version"] == "prospectif-v1"
        assert len(payload["baseline_sha256"]) == 64
        assert payload["baseline"]["need"]["sponsor"] == "Responsable opérationnel"
        assert len(payload["baseline"]["evidence"]) == 1

    with SessionLocal() as db:
        event = db.scalar(select(AuditEvent).where(AuditEvent.event_type == "CAS_PROSPECTIF_PRE_ENREGISTRE"))
        assert event is not None
        stored = json.loads(event.payload_json)
        assert stored["baseline"]["episode"]["need_preexisting_frontiere"] is True


def test_prospective_case_blocks_frontiere_before_paired_plan():
    reset_db()
    with TestClient(app) as client:
        location = _create_prospective_candidate(client)
        assert client.post(location + "/prospective/lock", follow_redirects=False).status_code == 303
        blocked = client.post(
            location + "/public-search",
            data={"complete": "no", "analyst_minutes": "5"},
            follow_redirects=False,
        )
        assert blocked.status_code == 409
        blocked_query = client.post(
            location + "/capability-query",
            data={
                "raw_request": "Besoin technique",
                "domain": "numérique",
                "function": "expertise",
            },
            follow_redirects=False,
        )
        assert blocked_query.status_code == 409


def test_paired_plan_unlocks_search_and_preserves_preregistration():
    reset_db()
    with TestClient(app) as client:
        location = _create_prospective_candidate(client)
        assert client.post(location + "/prospective/lock", follow_redirects=False).status_code == 303
        plan = client.post(
            location + "/comparison/lock",
            data={
                "usual_method": "recherche manuelle habituelle",
                "frontiere_method": "FRONTIÈRE",
                "usual_owner": "Analyste A",
                "frontiere_owner": "Analyste B",
                "primary_outcome": "temps jusqu'à une ressource mobilisable",
                "observation_date": "2026-10-20",
                "interference_policy": "Les deux recherches restent séparées jusqu'au point de mesure.",
                "usual_budget_minutes": "90",
                "frontiere_budget_minutes": "90",
            },
            follow_redirects=False,
        )
        assert plan.status_code == 303
        search = client.post(
            location + "/public-search",
            data={
                "complete": "yes",
                "relevant_found": "yes",
                "mobilizable_found": "no",
                "analyst_minutes": "35",
                "method_name": "FRONTIÈRE Inside-First",
                "search_scope": "administration concernée, ministère, opérateurs, recherche publique",
                "sources_consulted": "ROAE\nAnnuaire DILA\nCOG",
            },
            follow_redirects=False,
        )
        assert search.status_code == 303
        api = client.get(location.replace("/episodes/", "/api/v1/episodes/") + "/preregistration").json()
        comparison = api["paired_comparison"]["payload"]
        assert comparison["registered_before_search"] is True
        assert len(comparison["plan_sha256"]) == 64

    with SessionLocal() as db:
        event = db.scalar(select(AuditEvent).where(AuditEvent.event_type == "RECHERCHE_PUBLIQUE_ENREGISTREE"))
        payload = json.loads(event.payload_json)
        assert payload["method_name"] == "FRONTIÈRE Inside-First"
        assert payload["sources_consulted"] == ["ROAE", "Annuaire DILA", "COG"]


def test_paired_plan_cannot_be_registered_after_search():
    reset_db()
    with TestClient(app) as client:
        location = _create_locked_episode(client, "Cas déjà investigué")
        assert client.post(
            location + "/public-search",
            data={"complete": "no", "analyst_minutes": "10"},
            follow_redirects=False,
        ).status_code == 303
        late = client.post(location + "/prospective/lock", follow_redirects=False)
        assert late.status_code == 409


def test_prospective_baseline_refuses_existing_route_assessment():
    reset_db()
    with TestClient(app) as client:
        location = _create_prospective_candidate(client)
        assert client.post(location + "/need/lock", follow_redirects=False).status_code == 303
        route = client.post(location + "/route", data={
            "route_code": "COOPERATION", "route_label": "Coopération existante",
        }, follow_redirects=False)
        assert route.status_code == 303
        blocked = client.post(location + "/prospective/lock", follow_redirects=False)
        assert blocked.status_code == 409
        assert "voie évaluée" in blocked.json()["detail"]


def test_prospective_actions_cannot_bypass_paired_comparison():
    reset_db()
    with TestClient(app) as client:
        location = _create_prospective_candidate(client)
        assert client.post(location + "/prospective/lock", follow_redirects=False).status_code == 303
        forbidden = [
            ("/resource", {"resource_type": "ORGANISME", "display_name": "Exemple"}),
            ("/route", {"route_code": "EXPERTISE", "route_label": "Expertise"}),
            ("/friction", {"category": "MOBILITE", "started_at": "2026-10-07T12:00:00"}),
            ("/result", {"result_status": "EN_COURS", "outcome_description": "Résultat test"}),
            ("/knowledge", {"knowledge_type": "VOIE", "title": "Note", "content": "Texte"}),
            ("/reuse", {"knowledge_id": "1"}),
        ]
        for route, donnees in forbidden:
            response = client.post(location + route, data=donnees, follow_redirects=False)
            assert response.status_code == 409, (route, response.status_code, response.text)
        plan = client.post(location + "/comparison/lock", data={
            "usual_method": "méthode existante",
            "frontiere_method": "FRONTIÈRE",
            "usual_owner": "Analyste A",
            "frontiere_owner": "Analyste B",
            "primary_outcome": "temps jusqu'à une capacité mobilisable",
            "observation_date": "2026-10-20",
            "interference_policy": "Aucun échange avant la mesure.",
        }, follow_redirects=False)
        assert plan.status_code == 303
        route = client.post(location + "/route", data={
            "route_code": "EXPERTISE", "route_label": "Expertise",
        }, follow_redirects=False)
        assert route.status_code == 303


def test_paired_comparison_refuses_legacy_intervention():
    reset_db()
    with TestClient(app) as client:
        location = _create_prospective_candidate(client)
        assert client.post(location + "/prospective/lock", follow_redirects=False).status_code == 303
        code = location.rsplit("/", 1)[-1]
        with SessionLocal() as db:
            ep = db.scalar(select(Episode).where(Episode.code == code))
            db.add(RouteAssessment(
                episode_id=ep.id, route_code="ANCIENNE", route_label="Intervention héritée",
            ))
            db.commit()
        blocked = client.post(location + "/comparison/lock", data={
            "usual_method": "recherche habituelle",
            "frontiere_method": "FRONTIÈRE",
            "usual_owner": "Analyste A",
            "frontiere_owner": "Analyste B",
            "primary_outcome": "délai",
            "observation_date": "2026-10-20",
            "interference_policy": "aucun échange",
        }, follow_redirects=False)
        assert blocked.status_code == 409
        assert "voie évaluée" in blocked.json()["detail"]


def test_recherche_publique_complete_inconnue_ne_signifie_pas_absente():
    reset_db()
    with TestClient(app) as client:
        location = _create_locked_episode(client, "Conclusion publique inconnue")
        response = client.post(location + "/public-search", data={
            "complete": "yes", "relevant_found": "unknown",
            "mobilizable_found": "unknown",
        }, follow_redirects=False)
        assert response.status_code == 303
    with SessionLocal() as db:
        run = db.scalar(select(SearchRun).where(SearchRun.search_type == "PUBLIQUE"))
        assert run is not None
        assert run.public_result == "P0"
        assert run.public_relevant_found is None


def test_recherche_publique_refuse_mobilisable_sans_pertinence():
    reset_db()
    with TestClient(app) as client:
        location = _create_locked_episode(client, "Conclusion contradictoire")
        response = client.post(location + "/public-search", data={
            "complete": "yes", "relevant_found": "no",
            "mobilizable_found": "yes",
        }, follow_redirects=False)
        assert response.status_code == 400
        malformed = client.post(location + "/public-search", data={
            "complete": "yes", "relevant_found": "aucun",
            "mobilizable_found": "unknown",
        }, follow_redirects=False)
        assert malformed.status_code == 400
    with SessionLocal() as db:
        assert db.scalar(select(SearchRun.id).limit(1)) is None


def test_sealed_case_cannot_influence_published_aggregates():
    reset_db()
    with SessionLocal() as db:
        revealed = BenchmarkCase(
            code="BREVEAL", title="Cas révélé", prompt="Problème révélé",
            expected_routes_json='["VOIE_A"]',
            expected_resource_forms_json='["EQUIPE"]',
            expected_resources_json='[]', revealed=True,
        )
        sealed = BenchmarkCase(
            code="BSECRET", title="Cas réservé", prompt="Problème réservé",
            expected_routes_json='["ETIQUETTE_SECRETE"]',
            expected_resource_forms_json='["FORME_SECRETE"]',
            expected_resources_json='[]', revealed=False,
        )
        db.add_all([revealed, sealed])
        db.flush()
        db.add_all([
            BenchmarkPrediction(
                case_id=revealed.id, method="methode-a",
                routes_json='["VOIE_A"]', resource_forms_json='["EQUIPE"]',
                resources_json='[]', evidence_urls_json='[]',
                analyst_minutes=10, verification_minutes=1,
            ),
            BenchmarkPrediction(
                case_id=sealed.id, method="methode-a",
                routes_json='[]', resource_forms_json='[]',
                resources_json='[]', evidence_urls_json='[]',
                analyst_minutes=10000, verification_minutes=0,
            ),
            BenchmarkPrediction(
                case_id=sealed.id, method="methode-b",
                routes_json='[]', resource_forms_json='[]',
                resources_json='[]', evidence_urls_json='[]',
            ),
        ])
        db.commit()
    with TestClient(app) as client:
        public = client.get("/api/v1/evaluation").json()
        assert public["case_count"] == 2
        assert public["prediction_count"] == 3
        assert public["scored_prediction_count"] == 1
        assert public["sealed_prediction_count"] == 2
        assert len(public["methods"]) == 1
        assert public["methods"][0]["method"] == "methode-a"
        assert public["methods"][0]["n"] == 1
        assert public["methods"][0]["route_f1_mean"] == 1.0
        assert public["methods"][0]["human_minutes_median"] == 11
        page = client.get("/evaluation")
        assert "ETIQUETTE_SECRETE" not in page.text
        assert "FORME_SECRETE" not in page.text
        assert "Des prédictions sont enregistrées" in page.text


def test_benchmark_separe_les_versions_d_une_meme_methode():
    reset_db()
    with SessionLocal() as db:
        db.add(BenchmarkCase(
            code="BVERS", title="Versions", prompt="Trouver une voie",
            expected_routes_json='["VOIE_CORRECTE"]',
            expected_resource_forms_json='["EQUIPE"]',
            expected_resources_json='[]', revealed=False,
        ))
        db.commit()

    with TestClient(app) as client:
        for version, routes in [("1.0", "VOIE_CORRECTE"), ("2.0", "VOIE_INCORRECTE")]:
            response = client.post("/evaluation/BVERS/reponse", data={
                "method": "frontiere",
                "method_version": version,
                "routes": routes,
                "resource_forms": "EQUIPE",
                "analyst_minutes": "2",
                "verification_minutes": "1",
                "elapsed_seconds": "60",
            }, follow_redirects=False)
            assert response.status_code == 303
        avant = client.get("/api/v1/evaluation").json()
        assert avant["scored_prediction_count"] == 0
        assert client.post("/evaluation/BVERS/reveler", follow_redirects=False).status_code == 303
        resultat = client.get("/api/v1/evaluation").json()
        assert resultat["prediction_count"] == 2
        assert resultat["scored_prediction_count"] == 2
        versions = {m["method_version"]: m for m in resultat["methods"]}
        assert set(versions) == {"1.0", "2.0"}
        assert versions["1.0"]["n"] == 1
        assert versions["2.0"]["n"] == 1
        assert versions["1.0"]["route_f1_mean"] == 1.0
        assert versions["2.0"]["route_f1_mean"] == 0.0
        page = client.get("/evaluation")
        assert "version 1.0" in page.text and "version 2.0" in page.text


def test_benchmark_refuse_les_mesures_invalides_sans_les_modifier():
    reset_db()
    with SessionLocal() as db:
        db.add(BenchmarkCase(
            code="BINVALID", title="Mesures invalides", prompt="Proposer une ressource",
            expected_routes_json='["VOIE"]',
            expected_resource_forms_json='["EQUIPE"]',
            expected_resources_json='[]', revealed=False,
        ))
        db.commit()

    invalides = [
        {"method": "  ", "method_version": "1.0"},
        {"method": "test", "method_version": "   "},
        {"method": "test", "method_version": "1.0", "analyst_minutes": "-3"},
        {"method": "test", "method_version": "1.0", "verification_minutes": "-1"},
        {"method": "test", "method_version": "1.0", "elapsed_seconds": "-2.5"},
        {"method": "test", "method_version": "1.0", "elapsed_seconds": "nan"},
        {"method": "test", "method_version": "1.0", "elapsed_seconds": "inf"},
    ]
    with TestClient(app) as client:
        for data in invalides:
            response = client.post("/evaluation/BINVALID/reponse", data=data, follow_redirects=False)
            assert response.status_code in (400, 422), (data, response.status_code)
        assert client.get("/api/v1/evaluation").json()["prediction_count"] == 0
    with SessionLocal() as db:
        assert db.scalar(select(BenchmarkPrediction.id).limit(1)) is None


def test_export_empirique_preserve_absence_et_dernier_resultat():
    reset_db()
    with SessionLocal() as db:
        org = Organization(name="Organisme export temporel")
        db.add(org)
        db.flush()
        sans_resultat = Episode(
            code="EP-SANS-RESULTAT", organization_id=org.id,
            title="Besoin sans résultat enregistré", synthetic=False,
        )
        avec_resultat = Episode(
            code="EP-AVEC-RESULTAT", organization_id=org.id,
            title="Besoin suivi par deux observations", synthetic=False,
        )
        db.add_all([sans_resultat, avec_resultat])
        db.flush()
        db.add_all([
            SearchRun(episode_id=avec_resultat.id, search_type="PUBLIQUE", public_result="P1"),
            SearchRun(episode_id=avec_resultat.id, search_type="PUBLIQUE", public_result="P2"),
            EpisodeResult(
                episode_id=avec_resultat.id,
                result_status="PROVISOIRE",
                outcome_description="Première observation",
                frontiere_minutes=200, institution_minutes=75,
            ),
            EpisodeResult(
                episode_id=avec_resultat.id,
                result_status="OBSERVE",
                outcome_description="Révision ultérieure",
                frontiere_minutes=0, institution_minutes=14,
                first_useful_contribution_at=datetime(2026, 10, 8, 12, 30, tzinfo=timezone.utc),
            ),
        ])
        db.commit()

    with TestClient(app) as client:
        reponse = client.get("/api/v1/research-export")
        assert reponse.status_code == 200
        export = reponse.json()
        assert export["schema_version"] == "0.3"
        dossiers = {e["code"]: e for e in export["episodes"]}
        vide = dossiers["EP-SANS-RESULTAT"]
        assert vide["result_status"] is None
        assert vide["result_record_id"] is None
        assert vide["first_useful_contribution_at"] is None
        assert vide["frontiere_minutes"] is None
        assert vide["institution_minutes"] is None
        assert vide["public_search_record_id"] is None
        observe = dossiers["EP-AVEC-RESULTAT"]
        assert observe["public_result"] == "P2"
        assert type(observe["public_search_record_id"]) is int
        assert observe["result_status"] == "OBSERVE"
        assert type(observe["result_record_id"]) is int
        assert observe["frontiere_minutes"] == 0
        assert observe["institution_minutes"] == 14
        assert observe["first_useful_contribution_at"].startswith("2026-10-08T12:30:00")
