"""Essais sans réseau et adversariaux du nettoyage des références GitHub."""
from copy import deepcopy

import pytest

from scripts.nettoyer_branches_fusionnees import (
    NettoyageRefuse, PLAN_VERSION, REPO_ATTENDU,
    executer, selectionner, verifier_plan,
)

A = "a" * 40
B = "b" * 40


def plan():
    return {"version": PLAN_VERSION, "repository": REPO_ATTENDU,
            "candidats": [{"branche": "docs/finie", "sha": A, "pr": 2}]}


def git_data():
    branches = [
        {"name": "main", "commit": {"sha": B}, "protected": True},
        {"name": "docs/finie", "commit": {"sha": A}, "protected": False},
    ]
    pr = {"number": 2, "merged_at": "2026-10-17T01:00:00Z",
          "head": {"ref": "docs/finie", "sha": A,
                   "repo": {"full_name": REPO_ATTENDU}}}
    return branches, [pr], []


class FausseAPI:
    """Simulation à états mutables pour distinguer vérification et suppression."""

    def __init__(self):
        self.branches, self.fermees, self.ouvertes = git_data()
        self.refs = {"docs/finie": A}
        self.supprimees = []

    def appel(self, chemin):
        assert chemin == ""
        return {"full_name": REPO_ATTENDU, "default_branch": "main"}

    def pages(self, chemin):
        return {"/branches": self.branches,
                "/pulls?state=closed": self.fermees,
                "/pulls?state=open": self.ouvertes}[chemin]

    def etat_ref(self, nom):
        return self.refs.get(nom)

    def supprimer(self, nom):
        self.supprimees.append(nom)


def test_plan_valide_et_sans_doublon():
    assert verifier_plan(plan())[0]["pr"] == 2
    p = plan()
    p["candidats"].append(deepcopy(p["candidats"][0]))
    with pytest.raises(NettoyageRefuse, match="répété"):
        verifier_plan(p)


@pytest.mark.parametrize("nom", [
    "main", "master", "refs/heads/a", "foo/../main", "/debut",
    "a//b", "a\\b", "a/", "a\nmalveillant",
])
def test_noms_dangereux_refuses(nom):
    p = plan()
    p["candidats"][0]["branche"] = nom
    with pytest.raises(NettoyageRefuse):
        verifier_plan(p)


def test_simulation_ne_supprime_rien():
    client = FausseAPI()
    rapport = executer(plan(), client, False)
    assert rapport["admissibles"] == 1
    assert rapport["supprimees"] == []
    assert client.supprimees == []


def test_suppression_necessite_correspondance_exacte():
    client = FausseAPI()
    rapport = executer(plan(), client, True)
    assert rapport["supprimees"] == ["docs/finie"]
    assert client.supprimees == ["docs/finie"]


def test_ref_modifiee_apres_selection_preservee():
    client = FausseAPI()
    client.refs["docs/finie"] = B
    rapport = executer(plan(), client, True)
    assert rapport["supprimees"] == []
    assert rapport["exclues"][0]["raison"] == "ref_modifiee_ou_absente"


def test_pr_encore_ouverte_protege_branche():
    branches, fermees, ouvertes = git_data()
    ouvertes.append({"head": {"ref": "docs/finie",
                               "repo": {"full_name": REPO_ATTENDU}}})
    acceptes, exclus = selectionner(
        plan()["candidats"], branches, fermees, ouvertes, "main")
    assert not acceptes and exclus[0]["raison"] == "pr_ouverte"


def test_fusion_absente_ne_permet_pas_suppression():
    branches, fermees, ouvertes = git_data()
    fermees[0]["merged_at"] = None
    acceptes, exclus = selectionner(
        plan()["candidats"], branches, fermees, ouvertes, "main")
    assert not acceptes and exclus[0]["raison"] == "fusion_non_verifiee"


def test_pr_non_correspondante_preservee():
    branches, fermees, ouvertes = git_data()
    fermees[0]["head"]["sha"] = B
    acceptes, exclus = selectionner(
        plan()["candidats"], branches, fermees, ouvertes, "main")
    assert not acceptes and exclus[0]["raison"] == "pr_ou_sha_incompatible"


def test_ref_protegee_preservee():
    branches, fermees, ouvertes = git_data()
    branches[1]["protected"] = True
    acceptes, exclus = selectionner(
        plan()["candidats"], branches, fermees, ouvertes, "main")
    assert not acceptes and exclus[0]["raison"] == "protection_non_exclue"


def test_ref_modifiee_en_amont_preservee():
    branches, fermees, ouvertes = git_data()
    branches[1]["commit"]["sha"] = B
    acceptes, exclus = selectionner(
        plan()["candidats"], branches, fermees, ouvertes, "main")
    assert not acceptes and exclus[0]["raison"] == "sha_branche_modifie"


def test_limite_de_suppressions():
    p = plan()
    p["candidats"] = [
        {"branche": f"archive/{i}", "sha": A, "pr": i + 1}
        for i in range(326)
    ]
    with pytest.raises(NettoyageRefuse, match="Taille"):
        verifier_plan(p)
