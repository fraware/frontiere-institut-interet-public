"""La publication des besoins reste limitée aux quatre fichiers de sortie."""
from pathlib import Path

import pytest

from scripts.publier_mise_a_jour_institutionnelle import (
    PublicationRefusee, identite_branche, verifier_portee,
)

RACINE = Path(__file__).resolve().parents[1]


def test_publication_limitee_aux_besoins_publics():
    admis = [
        "institutionnel/besoins_publics/annonces_boamp.json",
        "institutionnel/besoins_publics/etat_boamp.json",
        "institutionnel/besoins_publics/ressources_emplois_publics.json",
        "institutionnel/besoins_publics/etat_emplois_publics.json",
    ]
    assert verifier_portee("besoins", admis)["nombre_fichiers"] == 4
    assert identite_branche("besoins", "1435", "1") == "automatisation/besoins-1435-1"
    for interdit in ("institutionnel/entites/locales/unite.jsonl",
                     "institutionnel/besoins_publics/contacts_prives.json",
                     "app/main.py"):
        with pytest.raises(PublicationRefusee):
            verifier_portee("besoins", [interdit])


def test_cadence_et_controles_des_sources_de_besoins():
    f = (RACINE / ".github/workflows/collecte-besoins-publics.yml").read_text(encoding="utf-8")
    assert 'cron: "23 3,9,15,21 * * *"' in f
    assert "scripts/collecter_besoins_publics.py" in f
    assert "scripts/publier_mise_a_jour_institutionnelle.py --source besoins --publier" in f
    assert "gh run watch" in f
    assert all(name in f for name in ("Python 3.11", "Python 3.12", "Conteneur"))
    assert "institutionnel/besoins_publics/annonces_boamp.json" in f
    assert "git push origin HEAD:main" not in f
    assert "persist-credentials: false" in f
