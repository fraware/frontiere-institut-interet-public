from datetime import datetime, timedelta, timezone

import pytest
from types import SimpleNamespace
from scripts.auditer_recherches_publiques import auditer_recherches

from app.services import classify_public_search, critical_path_minutes, elapsed_span_minutes, host_ready


def test_public_search_p0_when_incomplete():
    assert classify_public_search(complete=False, relevant_found=False, mobilizable_found=False) == "P0"


def test_public_search_distinguishes_p1_p2_p3():
    assert classify_public_search(complete=True, relevant_found=True, mobilizable_found=True) == "P1"
    assert classify_public_search(complete=True, relevant_found=True, mobilizable_found=False) == "P2"
    assert classify_public_search(complete=True, relevant_found=False, mobilizable_found=False) == "P3"


def test_unknown_host_gate_never_passes():
    assert host_ready(["PASS", "PASS", "UNKNOWN"]) is False
    assert host_ready(["PASS", "PASS", "PASS"]) is True


def test_critical_path_uses_dependencies_not_naive_sum():
    t0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
    events = [
        (t0, t0 + timedelta(minutes=60), None),
        (t0, t0 + timedelta(minutes=120), None),
        (t0 + timedelta(minutes=120), t0 + timedelta(minutes=150), 1),
    ]
    assert critical_path_minutes(events) == 150


def test_elapsed_span_counts_waiting_time_separately_from_dependency_work():
    t0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
    events = [
        (t0, t0 + timedelta(minutes=60), None),
        (t0 + timedelta(minutes=30), t0 + timedelta(minutes=90), 0),
        (t0 + timedelta(minutes=100), t0 + timedelta(minutes=130), 1),
    ]
    # Le chemin additionne les durées déclarées (60 + 60 + 30).
    assert critical_path_minutes(events) == 150
    # Le délai réel englobe un chevauchement et une attente.
    assert elapsed_span_minutes(events) == 130


def test_elapsed_span_counts_parallelism_without_double_counting():
    t0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
    events = [
        (t0, t0 + timedelta(minutes=60), None),
        (t0, t0 + timedelta(minutes=120), None),
        (t0 + timedelta(minutes=120), t0 + timedelta(minutes=150), 1),
    ]
    assert elapsed_span_minutes(events) == 150


def test_elapsed_span_preserves_unknown_when_event_is_open():
    t0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
    assert elapsed_span_minutes([]) is None
    assert elapsed_span_minutes([(t0, None, None)]) is None


def test_elapsed_span_rejects_inverted_intervals():
    t0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
    try:
        elapsed_span_minutes([(t0 + timedelta(minutes=1), t0, None)])
    except ValueError:
        pass
    else:
        raise AssertionError("Un intervalle inversé doit être rejeté.")


def test_recherche_complete_a_resultat_inconnu_reste_p0():
    assert classify_public_search(
        complete=True, relevant_found=None, mobilizable_found=None
    ) == "P0"


@pytest.mark.parametrize("relevant,mobilizable", [
    (None, True),
    (False, True),
])
def test_mobilisabilite_ne_peut_pas_preceder_pertinence(relevant, mobilizable):
    with pytest.raises(ValueError):
        classify_public_search(
            complete=True, relevant_found=relevant, mobilizable_found=mobilizable
        )


def test_audit_retrospectif_ne_requalifie_pas_silencieusement():
    ancien = SimpleNamespace(
        id=1, episode_id=101, search_type="PUBLIQUE",
        public_result="P3", complete_enough_to_conclude=True,
        public_relevant_found=None, public_mobilizable_found=None,
    )
    bilan = auditer_recherches([ancien])
    assert bilan["nombre_anomalies"] == 1
    assert bilan["anomalies"][0]["resultat_recalcule"] == "P0"
    assert ancien.public_result == "P3"
    assert bilan["donnees_modifiees"] is False


def test_audit_signale_les_incoherences_sans_fausse_certitude():
    ancien = SimpleNamespace(
        id=2, episode_id=102, search_type="PUBLIQUE",
        public_result="P3", complete_enough_to_conclude=True,
        public_relevant_found=False, public_mobilizable_found=True,
    )
    bilan = auditer_recherches([ancien])
    assert bilan["nombre_anomalies"] == 1
    assert bilan["anomalies"][0]["type"] == "saisie_contradictoire"
    assert bilan["anomalies"][0]["resultat_recalcule"] is None
