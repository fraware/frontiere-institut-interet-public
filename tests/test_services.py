from datetime import datetime, timedelta, timezone

from app.services import classify_public_search, critical_path_minutes, host_ready


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
