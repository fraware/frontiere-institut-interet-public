"""Contrôles adversariaux des références ancêtres de main."""
from copy import deepcopy

import pytest

from scripts.nettoyer_branches_ancetres import (
    VERSION, verifier_plan, selectionner,
)
from scripts.nettoyer_branches_fusionnees import NettoyageRefuse, REPO_ATTENDU

A = "a" * 40
NOMS = [f"enquete/historique-{i}" for i in range(6)]


def plan():
    return {
        "version": VERSION, "repository": REPO_ATTENDU,
        "candidats": [{"branche": nom, "sha": A} for nom in NOMS],
    }


def donnees():
    return [
        {"name": x, "commit": {"sha": A}, "protected": False} for x in NOMS
    ]


def test_plan_exact_de_six_references():
    assert len(verifier_plan(plan())) == 6


@pytest.mark.parametrize("nom", [
    "main", "master", "refs/heads/foo", "/foo", "foo/",
    "foo/../main", "foo//bar", "foo\\bar", "foo\nbar",
])
def test_noms_dangereux_refuses(nom):
    p = plan()
    p["candidats"][0]["branche"] = nom
    with pytest.raises(NettoyageRefuse):
        verifier_plan(p)


def test_nombredes_references_fige():
    p = plan()
    p["candidats"].pop()
    with pytest.raises(NettoyageRefuse):
        verifier_plan(p)


def test_doublon_refuse():
    p = plan()
    p["candidats"][1]["branche"] = p["candidats"][0]["branche"]
    with pytest.raises(NettoyageRefuse):
        verifier_plan(p)


def test_supprime_uniquement_ascendance_confirmee():
    a, ex = selectionner(plan()["candidats"], donnees(), [], lambda _: True)
    assert len(a) == 6 and ex == []


def test_refuse_commits_non_integres():
    a, ex = selectionner(plan()["candidats"], donnees(), [], lambda _: False)
    assert a == [] and len(ex) == 6
    assert all(x["raison"] == "contenu_non_integre" for x in ex)


def test_preserve_branche_protegee():
    b = donnees()
    b[0]["protected"] = True
    a, ex = selectionner(plan()["candidats"], b, [], lambda _: True)
    assert len(a) == 5 and ex[0]["raison"] == "protegee"


def test_preserve_branche_demandee_en_fusion():
    o = [{"head": {"ref": NOMS[0],
                   "repo": {"full_name": REPO_ATTENDU}}}]
    a, ex = selectionner(plan()["candidats"], donnees(), o, lambda _: True)
    assert len(a) == 5 and ex[0]["raison"] == "pr_ouverte"


def test_preserve_sha_modifie():
    b = donnees()
    b[0]["commit"]["sha"] = "b" * 40
    a, ex = selectionner(plan()["candidats"], b, [], lambda _: True)
    assert len(a) == 5 and ex[0]["raison"] == "sha_modifie"


def test_preserve_branche_disparue():
    b = donnees()[1:]
    a, ex = selectionner(plan()["candidats"], b, [], lambda _: True)
    assert len(a) == 5 and ex[0]["raison"] == "absente"
