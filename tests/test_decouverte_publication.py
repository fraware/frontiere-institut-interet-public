"""Vérifier les conditions de publication des seuls catalogues publics."""
from pathlib import Path

import pytest

from scripts.publier_mise_a_jour_institutionnelle import (
    PublicationRefusee, identite_branche, verifier_portee,
)

RACINE = Path(__file__).resolve().parents[1]


def test_publication_sources_uniquement_deux_fichiers_de_metadonnees():
    paths = [
        "institutionnel/decouverte/candidats_data_gouv.json",
        "institutionnel/decouverte/etat_collecte.json",
        "institutionnel/decouverte/balayage_etat.json",
        "institutionnel/decouverte/balayage_pages/page_00001.jsonl",
    ]
    assert verifier_portee("sources", paths)["nombre_fichiers"] == 4
    for interdit in (
        "institutionnel/entites/rnsr/source.jsonl",
        "donnees/sensibles.json",
        ".github/workflows/ci.yml",
        "institutionnel/decouverte/catalogues_officiels_v1.json",
    ):
        with pytest.raises(PublicationRefusee):
            verifier_portee("sources", [interdit])
    assert identite_branche("sources", "12345", "1") == "automatisation/sources-12345-1"


def test_rythme_et_controles_explicites_de_la_decouverte():
    source = (
        RACINE / ".github/workflows/decouverte-sources.yml"
    ).read_text(encoding="utf-8")
    assert 'cron: "11 1,7,13,19 * * *"' in source
    assert "cancel-in-progress: false" in source
    assert "scripts/decouvrir_sources_publiques.py" in source
    assert "scripts/balayer_catalogue_national.py" in source
    assert "institutionnel/decouverte/balayage_pages/page_*.jsonl" in source
    assert "scripts/publier_mise_a_jour_institutionnelle.py --source sources --publier" in source
    assert "gh run watch" in source
    assert "Python 3.11" in source and "Python 3.12" in source and "Conteneur" in source
    assert "gh pr merge" in source
    assert "git push origin HEAD:main" not in source
    assert "persist-credentials: false" in source
