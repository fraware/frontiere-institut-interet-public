from datetime import datetime, timedelta, timezone

from app.preregistration_integrity import empreinte, verifier_preenregistrements


def scenario():
    t0 = datetime(2026, 10, 7, tzinfo=timezone.utc)
    baseline = {"episode": {"code": "EP-2026-0001"}, "need": {"version": 1}}
    baseline_payload = {"baseline": baseline, "baseline_sha256": empreinte(baseline)}
    plan = {
        "schema_version": "comparaison-appariee-v1",
        "baseline_sha256": baseline_payload["baseline_sha256"],
        "usual_method": "recherche interne",
        "frontiere_method": "FRONTIÈRE",
    }
    comparison_payload = {**plan, "plan_sha256": empreinte(plan)}
    return baseline_payload, comparison_payload, t0


def test_valid_preregistrations_are_internally_consistent():
    baseline, comparison, t0 = scenario()
    result = verifier_preenregistrements(baseline, comparison, t0, t0 + timedelta(seconds=1))
    assert result["internally_consistent"] is True
    assert result["external_timestamp_verified"] is False
    assert all(value is True for value in result["checks"].values())


def test_modified_baseline_is_detected():
    baseline, comparison, t0 = scenario()
    baseline["baseline"]["need"]["version"] = 2
    result = verifier_preenregistrements(baseline, comparison, t0, t0)
    assert result["checks"]["empreinte_etat_initial"] is False
    assert result["internally_consistent"] is False


def test_modified_plan_is_detected():
    baseline, comparison, t0 = scenario()
    comparison["usual_method"] = "méthode réécrite"
    result = verifier_preenregistrements(baseline, comparison, t0, t0)
    assert result["checks"]["empreinte_comparaison"] is False


def test_broken_link_is_detected_even_if_plan_is_rehashed():
    baseline, comparison, t0 = scenario()
    comparison["baseline_sha256"] = "0" * 64
    comparison["plan_sha256"] = empreinte({k: v for k, v in comparison.items() if k != "plan_sha256"})
    result = verifier_preenregistrements(baseline, comparison, t0, t0)
    assert result["checks"]["empreinte_comparaison"] is True
    assert result["checks"]["lien_etat_initial_comparaison"] is False


def test_reversed_registration_order_is_detected():
    baseline, comparison, t0 = scenario()
    result = verifier_preenregistrements(baseline, comparison, t0 + timedelta(seconds=1), t0)
    assert result["checks"]["ordre_enregistrement"] is False


def test_missing_baseline_does_not_look_valid():
    result = verifier_preenregistrements(None, None)
    assert result["internally_consistent"] is False
    assert result["checks"]["empreinte_etat_initial"] is None
