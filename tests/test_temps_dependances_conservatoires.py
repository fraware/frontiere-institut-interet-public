"""Le temps non observé reste inconnu ; les dépendances invalides sont refusées."""
from datetime import datetime, timedelta, timezone

import pytest

from app.services import critical_path_minutes, elapsed_span_minutes


def origine():
    return datetime(2026, 10, 8, 9, tzinfo=timezone.utc)


def test_intervalle_absent_ou_inacheve_est_inconnu():
    t = origine()
    assert critical_path_minutes([]) is None
    assert elapsed_span_minutes([]) is None
    events = [(t, t + timedelta(minutes=10), None), (t, None, 0)]
    assert critical_path_minutes(events) is None
    assert elapsed_span_minutes(events) is None


def test_dependances_valides_et_calendrier_reel_distincts():
    t = origine()
    events = [
        (t, t + timedelta(minutes=60), None),
        (t + timedelta(minutes=30), t + timedelta(minutes=90), 0),
        (t + timedelta(minutes=100), t + timedelta(minutes=130), 1),
    ]
    assert critical_path_minutes(events) == 150
    assert elapsed_span_minutes(events) == 130


@pytest.mark.parametrize("parent", [-1, 0, 2, True, "0"])
def test_refuse_dependance_d_un_premier_evenement(parent):
    t = origine()
    with pytest.raises(ValueError, match="dépendance"):
        critical_path_minutes([(t, t + timedelta(minutes=1), parent)])


def test_refuse_reference_vers_un_evenement_futur():
    t = origine()
    with pytest.raises(ValueError, match="dépendance"):
        critical_path_minutes([
            (t, t + timedelta(minutes=1), 1),
            (t, t + timedelta(minutes=2), None),
        ])


@pytest.mark.parametrize("fonction", [critical_path_minutes, elapsed_span_minutes])
def test_refuse_une_duree_negative(fonction):
    t = origine()
    with pytest.raises(ValueError, match="précède"):
        fonction([(t + timedelta(minutes=10), t, None)])


@pytest.mark.parametrize("fonction", [critical_path_minutes, elapsed_span_minutes])
def test_refuse_une_date_sans_fuseau(fonction):
    t = datetime(2026, 10, 8, 9)
    with pytest.raises(ValueError, match="fuseau"):
        fonction([(t, t + timedelta(minutes=10), None)])


@pytest.mark.parametrize("fonction", [critical_path_minutes, elapsed_span_minutes])
def test_refuse_une_duree_invalide_meme_si_un_autre_evenement_reste_ouvert(fonction):
    t = origine()
    with pytest.raises(ValueError, match="précède"):
        fonction([
            (t, None, None),
            (t + timedelta(minutes=20), t + timedelta(minutes=15), 0),
        ])
