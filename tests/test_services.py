from datetime import datetime, timedelta, timezone

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
