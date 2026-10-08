"""Essais de cohérence publique du jeu H01–H10, sans ouvrir les références."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.verifier_prevol_jeu_reserve import charger_json, verifier_preparation

RACINE = Path(__file__).resolve().parents[1]


def charger_documents():
    """Retourner des copies indépendantes des trois artefacts publics."""
    dossier = RACINE / "evaluation"
    return (
        charger_json(dossier / "jeu_reserve_v1_questions.json"),
        charger_json(dossier / "modele_reponses.json"),
        charger_json(dossier / "jeu_reserve_v1_manifeste.json"),
    )


def test_prevol_public_conforme_sans_ouvrir_le_corrige():
    q, r, m = charger_documents()
    resultat = verifier_preparation(q, r, m)
    assert resultat["conformite_structurelle"] is True
    assert resultat["nombre_cas_publics"] == 10
    assert resultat["references_privees_ouvertes"] is False
    assert resultat["references_privees_verifiees"] is False
    assert resultat["resultat_independant_obtenu"] is False


@pytest.mark.parametrize("mutation,erreur", [
    (lambda q, r, m: q["cas"].reverse(), "dans l'ordre"),
    (lambda q, r, m: q["cas"][0].update({"reference_historique": "divulgation"}), "champs publics"),
    (lambda q, r, m: r["cas"][0]["voies"].append("Réponse préremplie"), "contient une proposition"),
    (lambda q, r, m: r["cas"][0].update({"duree_secondes": 0}), "non vierge"),
    (lambda q, r, m: m.update({"nombre_cas": 9}), "dix cas"),
    (lambda q, r, m: m.update({"empreinte_sha256_references": "0" * 64}), "fictive"),
])
def test_prevol_refuse_alterations(mutation, erreur):
    q, r, m = charger_documents()
    mutation(q, r, m)
    with pytest.raises(ValueError, match=erreur):
        verifier_preparation(q, r, m)


def test_prevol_cli_publie_uniquement_un_controle_structurel():
    processus = subprocess.run(
        [sys.executable, "scripts/verifier_prevol_jeu_reserve.py"],
        cwd=RACINE, text=True, capture_output=True, check=False, timeout=20,
    )
    assert processus.returncode == 0, processus.stderr
    resultat = json.loads(processus.stdout)
    assert resultat["conformite_structurelle"] is True
    assert len(resultat["empreinte_sha256_questions_public"]) == 64
    assert "empreinte_sha256_references" not in resultat
    assert resultat["references_privees_verifiees"] is False
