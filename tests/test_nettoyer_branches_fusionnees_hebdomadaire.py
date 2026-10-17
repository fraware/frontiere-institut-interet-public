"""Essais des exclusions et de la période de rétention hebdomadaire."""
from datetime import datetime, timezone
from copy import deepcopy

import pytest

from scripts.nettoyer_branches_fusionnees import NettoyageRefuse, REPO_ATTENDU
from scripts.nettoyer_branches_fusionnees_hebdomadaire import elaborer_plan

MAINTENANT = datetime(2026, 10, 17, 16, 0, tzinfo=timezone.utc)
SHA = "a" * 40


def objets():
    branches = [{"name": "main", "commit": {"sha": "b" * 40}, "protected": True},
                {"name": "travail/termine", "commit": {"sha": SHA}, "protected": False}]
    fermees = [{"number": 21, "merged_at": "2026-10-15T12:00:00Z",
                "head": {"ref": "travail/termine", "sha": SHA,
                         "repo": {"full_name": REPO_ATTENDU}}}]
    return branches, fermees, []


def test_supprime_uniquement_fusion_ancienne():
    p = elaborer_plan(*objets(), MAINTENANT)
    assert p["candidats"] == [{"branche": "travail/termine", "sha": SHA, "pr": 21}]


def test_fusion_recente_conservee():
    b, p, o = objets()
    p[0]["merged_at"] = "2026-10-17T15:00:00Z"
    assert elaborer_plan(b, p, o, MAINTENANT)["candidats"] == []


def test_fusion_non_constatee_conservee():
    b, p, o = objets()
    p[0]["merged_at"] = None
    assert not elaborer_plan(b, p, o, MAINTENANT)["candidats"]


def test_pr_ouverte_conservee():
    b, p, o = objets()
    o.append({"head": {"ref": "travail/termine",
                       "repo": {"full_name": REPO_ATTENDU}}})
    assert not elaborer_plan(b, p, o, MAINTENANT)["candidats"]


def test_modification_apres_fusion_conservee():
    b, p, o = objets()
    b[1]["commit"]["sha"] = "c" * 40
    assert not elaborer_plan(b, p, o, MAINTENANT)["candidats"]


def test_branche_protegee_conservee():
    b, p, o = objets()
    b[1]["protected"] = True
    assert not elaborer_plan(b, p, o, MAINTENANT)["candidats"]


def test_source_exterieure_conservee():
    b, p, o = objets()
    p[0]["head"]["repo"]["full_name"] = "autre/depot"
    assert not elaborer_plan(b, p, o, MAINTENANT)["candidats"]


def test_heure_naive_refusee():
    with pytest.raises(NettoyageRefuse, match="fuseau"):
        elaborer_plan(*objets(), datetime(2026, 10, 17))


def test_ancienne_pr_avec_repo_disparu_ne_provoque_pas_derreur():
    b, p, o = objets()
    p[0]["head"]["repo"] = None
    assert elaborer_plan(b, p, o, MAINTENANT)["candidats"] == []
