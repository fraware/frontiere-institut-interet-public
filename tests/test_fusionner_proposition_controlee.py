"""Contrôles déterministes de fusion, de concurrence et de protection de main."""
from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from scripts.fusionner_proposition_controlee import (
    CHANGEMENT_BASE, fusionner_avec_reessais, examiner_proposition,
    valider_concurrence,
)
from scripts.publier_mise_a_jour_institutionnelle import PublicationRefusee

SHA = "a" * 40
BRANCHE = "automatisation/deliberations-38629460138-1"
FICHIERS = [
    {"path": "institutionnel/deliberations_publiques/etat_collecte.json"}
]


def proposition():
    return {
        "number": 427,
        "headRefName": BRANCHE, "headRefOid": SHA,
        "baseRefName": "main", "state": "OPEN",
        "isDraft": False, "files": FICHIERS,
    }


def retour(code=0, stderr=""):
    return subprocess.CompletedProcess(args=["gh"], returncode=code,
                                       stdout="", stderr=stderr)


def test_revision_de_main_sur_une_source_independante():
    valider_concurrence(
        "deliberations", SHA, BRANCHE, proposition(),
        {"institutionnel/decp/sonde_aife_json.json",
         "docs/VEILLE_PROGRAMMES_SCIENTIFIQUES_ANR_V1.md"},
    )


@pytest.mark.parametrize("changements,fragment", [
    ({"institutionnel/deliberations_publiques/etat_collecte.json"}, "simultanément"),
    ({"scripts/moissonner_deliberations_publiques.py"}, "Code ou configuration"),
    ({".github/workflows/ci.yml"}, "Code ou configuration"),
    ({"pyproject.toml"}, "Code ou configuration"),
])
def test_refuse_modification_concurrente_ou_nouvelle_configuration(changements, fragment):
    with pytest.raises(PublicationRefusee, match=fragment):
        valider_concurrence(
            "deliberations", SHA, BRANCHE, proposition(), changements,
        )


@pytest.mark.parametrize("champ,valeur", [
    ("headRefOid", "b" * 40),
    ("headRefName", "automatisation/deliberations-12-1"),
    ("baseRefName", "branche-non-principale"),
    ("state", "MERGED"),
    ("isDraft", True),
])
def test_refuse_proposition_modifiee_ou_non_admissible(champ, valeur):
    pr = proposition()
    pr[champ] = valeur
    with pytest.raises(PublicationRefusee, match="Proposition"):
        valider_concurrence("deliberations", SHA, BRANCHE, pr, set())


def test_refuse_fichier_hors_portee():
    pr = proposition()
    pr["files"] = [{"path": "institutionnel/programmes_scientifiques/etat_observations.json"}]
    with pytest.raises(PublicationRefusee, match="hors périmètre"):
        valider_concurrence("deliberations", SHA, BRANCHE, pr, set())


def test_refuse_liste_vide_ou_doublons():
    pr = proposition()
    pr["files"] = []
    with pytest.raises(PublicationRefusee, match="absente"):
        valider_concurrence("deliberations", SHA, BRANCHE, pr, set())
    pr["files"] = FICHIERS + FICHIERS
    with pytest.raises(PublicationRefusee, match="dupliqués"):
        valider_concurrence("deliberations", SHA, BRANCHE, pr, set())


def test_reessaie_uniquement_la_concurrence_de_base():
    operations = []
    resultats = iter([
        retour(1, "GraphQL: " + CHANGEMENT_BASE + " (mergePullRequest)"),
        retour(),
    ])
    numero = fusionner_avec_reessais(
        "fraware/frontiere-institut-interet-public", "deliberations", BRANCHE, SHA,
        verifier=lambda: operations.append("controle"),
        fusionner=lambda: operations.append("fusion") or next(resultats),
        confirmer=lambda: True,
        attendre=lambda secondes: operations.append(("attente", secondes)),
    )
    assert numero == 2
    assert operations == ["controle", "fusion", ("attente", 3), "controle", "fusion"]


def test_interruption_immediate_sur_autre_echec():
    operations = []
    with pytest.raises(PublicationRefusee, match="autre raison"):
        fusionner_avec_reessais(
            "fraware/frontiere-institut-interet-public", "deliberations", BRANCHE, SHA,
            verifier=lambda: operations.append("controle"),
            fusionner=lambda: retour(1, "permission denied"),
            confirmer=lambda: pytest.fail("Aucune fusion à confirmer"),
            attendre=lambda _: pytest.fail("Une nouvelle tentative est interdite"),
        )
    assert operations == ["controle"]


def test_trois_tentatives_maximales():
    nb = []
    with pytest.raises(PublicationRefusee, match="persistante"):
        fusionner_avec_reessais(
            "fraware/frontiere-institut-interet-public", "deliberations", BRANCHE, SHA,
            verifier=lambda: nb.append("controle"),
            fusionner=lambda: retour(1, CHANGEMENT_BASE),
            confirmer=lambda: pytest.fail("Aucune fusion à confirmer"),
            attendre=lambda _: None,
        )
    assert len(nb) == 3


def test_nouvelle_interference_interrompt_la_seconde_tentative():
    essais = iter([None, PublicationRefusee("Chemins modifiés simultanément")])
    with pytest.raises(PublicationRefusee, match="simultanément"):
        fusionner_avec_reessais(
            "fraware/frontiere-institut-interet-public", "deliberations", BRANCHE, SHA,
            verifier=lambda: (
                (_ for _ in ()).throw(err) if (err := next(essais)) else None
            ),
            fusionner=lambda: retour(1, CHANGEMENT_BASE),
            confirmer=lambda: pytest.fail("Aucune fusion à confirmer"),
            attendre=lambda _: None,
        )


def test_examen_integration_consulte_la_base_actuelle(monkeypatch, tmp_path: Path):
    import json
    from scripts import fusionner_proposition_controlee as module

    appels = []
    def faux(*arguments, racine=None):
        appels.append(arguments)
        if arguments[:3] == ("gh", "pr", "view"):
            return json.dumps(proposition())
        if arguments[:3] == ("git", "fetch", "--quiet"):
            return ""
        if arguments[:2] == ("git", "merge-base"):
            return "f" * 40 + "\n"
        if arguments[:3] == ("git", "diff", "--no-renames"):
            return "institutionnel/decp/sonde_aife_json.json\0"
        raise AssertionError(arguments)
    monkeypatch.setattr(module, "sortie", faux)
    examiner_proposition(
        "fraware/frontiere-institut-interet-public", "deliberations",
        BRANCHE, SHA, 427, racine=tmp_path,
    )
    assert any(x[:3] == ("git", "fetch", "--quiet") for x in appels)
    assert any(x[:3] == ("git", "diff", "--no-renames") for x in appels)


def test_succes_de_commande_ne_vaut_pas_preuve_de_fusion():
    with pytest.raises(PublicationRefusee, match="sans preuve"):
        fusionner_avec_reessais(
            "fraware/frontiere-institut-interet-public", "deliberations", BRANCHE, SHA,
            verifier=lambda: None,
            fusionner=lambda: retour(),
            confirmer=lambda: False,
            attendre=lambda _: pytest.fail("Une commande acceptée ne se réessaie pas"),
        )


def test_refuse_numero_incoherent_de_proposition(monkeypatch, tmp_path: Path):
    import json
    from scripts import fusionner_proposition_controlee as module
    def faux(*arguments, racine=None):
        return json.dumps(proposition())
    monkeypatch.setattr(module, "sortie", faux)
    with pytest.raises(PublicationRefusee, match="Numéro"):
        examiner_proposition(
            "fraware/frontiere-institut-interet-public",
            "deliberations", BRANCHE, SHA, 999, racine=tmp_path,
        )
