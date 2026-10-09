"""Publication du fichier quotidien BeauAMP uniquement dans son dossier attribué."""
from pathlib import Path

import pytest

from scripts.publier_mise_a_jour_institutionnelle import (
    PublicationRefusee, identite_branche, verifier_portee,
)

RACINE = Path(__file__).resolve().parents[1]


def test_fichiers_attribues_limites_aux_archives_beauamp():
    valides = [
        "institutionnel/marches_attribues/quotidiens/2026-10-08.csv",
        "institutionnel/marches_attribues/manifest.json",
        "institutionnel/marches_attribues/etat.json",
    ]
    assert verifier_portee("beauamp", valides)["nombre_fichiers"] == 3
    assert identite_branche("beauamp", "12345", "1") == "automatisation/beauamp-12345-1"
    for hors in (".github/workflows/ci.yml",
                 "institutionnel/besoins_publics/annonces_boamp.json"):
        with pytest.raises(PublicationRefusee):
            verifier_portee("beauamp", [hors])


def test_cadence_et_verifications_exactes_des_fichiers():
    s = (RACINE / ".github/workflows/collecte-beauamp.yml").read_text(encoding="utf-8")
    assert 'cron: "47 4,16 * * *"' in s
    assert "scripts/collecter_beauamp.py" in s
    assert "scripts/publier_mise_a_jour_institutionnelle.py --source beauamp --publier" in s
    assert "gh run watch" in s
    assert "Python 3.11" in s and "Python 3.12" in s and "Conteneur" in s
    assert "institutionnel/marches_attribues/quotidiens/20??-??-??.csv" in s
    assert "persist-credentials: false" in s
