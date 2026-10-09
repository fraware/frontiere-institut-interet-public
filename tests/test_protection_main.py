"""Contrôle conservateur de main avec réponses GitHub entièrement fictives."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.verifier_protection_main import (
    MODELE, ErreurProtection, evaluer_github, verifier_modele,
)

RACINE = Path(__file__).resolve().parents[1]


def modele():
    return json.loads(MODELE.read_text(encoding="utf-8"))


def etat_de_branche(protegee: bool):
    return {"name": "main", "protected": protegee}


def regle_active():
    valeur = modele()
    valeur["id"] = 123
    return valeur


def test_modele_pret_a_importer_sans_pretendre_protection_active():
    resultat = verifier_modele(modele())
    assert resultat["modele_structurellement_conforme"] is True
    assert resultat["protection_effectivement_active"] is False
    assert resultat["verifications_prevues"] == [
        "Conteneur", "Python 3.11", "Python 3.12"
    ]


def test_refuse_contournement_ou_politique_incomplete():
    exemple = modele()
    exemple["bypass_actors"] = [
        {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
    ]
    with pytest.raises(ErreurProtection, match="contournement"):
        verifier_modele(exemple)

    exemple = modele()
    exemple["rules"].pop()
    with pytest.raises(ErreurProtection, match="required_status_checks"):
        verifier_modele(exemple)

    exemple = modele()
    conditions = exemple["rules"][-1]["parameters"]
    conditions["strict_required_status_checks_policy"] = True
    with pytest.raises(ErreurProtection, match="non stricte"):
        verifier_modele(exemple)


def test_refuse_source_de_controle_non_authentifiee():
    exemple = modele()
    exemple["rules"][-1]["parameters"]["required_status_checks"][0]["integration_id"] = 12
    with pytest.raises(ErreurProtection, match="GitHub Actions"):
        verifier_modele(exemple)


def test_absence_de_protection_ne_constitue_pas_une_validation():
    r = evaluer_github(etat_de_branche(False), [])
    assert r["branche_main_protegee"] is False
    assert r["audit_complet"] is False
    assert r["verifications_obligatoires_github_actions"] == []


def test_regle_active_sur_main_avec_verifications_attestees():
    r = evaluer_github(etat_de_branche(True), [regle_active()])
    assert r["audit_complet"] is True
    assert r["conformite_regles_lisibles"] is True
    assert r["absence_contournement_attestee"] is True
    assert r["verifications_obligatoires_github_actions"] == [
        "Conteneur", "Python 3.11", "Python 3.12"
    ]


def test_une_regle_desactivee_ne_valide_aucune_protection():
    r = regle_active()
    r["enforcement"] = "disabled"
    compte = evaluer_github(etat_de_branche(True), [r])
    assert compte["regles_actives_lisibles"] == 0
    assert compte["audit_complet"] is False


def test_absence_de_liste_de_contournement_reste_inconnue():
    r = regle_active()
    del r["bypass_actors"]
    compte = evaluer_github(etat_de_branche(True), [r])
    assert compte["conformite_regles_lisibles"] is True
    assert compte["absence_contournement_attestee"] is False
    assert compte["audit_complet"] is False


def test_une_source_erronee_invalide_les_controles():
    r = regle_active()
    r["rules"][-1]["parameters"]["required_status_checks"][0]["integration_id"] = 42
    compte = evaluer_github(etat_de_branche(True), [r])
    assert compte["conformite_regles_lisibles"] is False


def test_les_regles_etrangeres_a_main_ne_sont_pas_comptees():
    r = regle_active()
    r["conditions"]["ref_name"]["include"] = ["refs/heads/developpement"]
    compte = evaluer_github(etat_de_branche(True), [r])
    assert compte["regles_actives_lisibles"] == 0
    assert compte["audit_complet"] is False


def test_le_mode_sans_reseau_n_atteste_aucune_activation():
    result = subprocess.run(
        [sys.executable, "scripts/verifier_protection_main.py", "--modele-seulement"],
        cwd=RACINE, text=True, capture_output=True, check=False, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    rapport = json.loads(result.stdout)
    assert rapport["protection_effectivement_active"] is False
