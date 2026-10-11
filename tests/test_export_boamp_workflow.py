"""Vérifier la procédure automatisée de conservation documentaire."""
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def test_export_boamp_sans_ecriture_vers_depot():
    contenu = (RACINE / ".github/workflows/export-boamp-portable.yml").read_text(
        encoding="utf-8",
    )
    assert "ref: main" in contenu
    assert "persist-credentials: false" in contenu
    assert "contents: read" in contenu
    assert "contents: write" not in contenu
    assert "scripts/exporter_archive_boamp.py exporter" in contenu
    assert "scripts/exporter_archive_boamp.py verifier" in contenu
    assert "actions/upload-artifact@v4" in contenu
    assert "retention-days: 30" in contenu
    assert 'REVISION=$(git rev-parse HEAD)' in contenu
    assert "sha256_paquet" in contenu
    assert "copie_hors_site_effectuee" in contenu
