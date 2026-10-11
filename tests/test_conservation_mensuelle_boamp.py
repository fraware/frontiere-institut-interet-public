"""Vérifier la publication mensuelle durable et sa politique de validation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/conservation-boamp-versions.yml"


def test_version_mensuelle_non_ecrasee():
    c = WORKFLOW.read_text(encoding="utf-8")
    assert "17 6 1 * *" in c
    assert "workflow_dispatch:" in c
    assert "concurrency:" in c
    assert "cancel-in-progress: false" in c
    assert "ref: main" in c
    assert "persist-credentials: false" in c
    assert "contents: read" in c
    assert "contents: write" in c
    assert 'MOIS=$(date -u +%Y-%m)' in c
    assert 'gh release view "$NOM"' in c
    assert "steps.edition.outputs.existe == 'true'" in c
    assert "steps.edition.outputs.existe == 'false'" in c
    assert "gh release delete" not in c
    assert "gh release upload" not in c
    assert "gh release create" in c
    assert "gh release edit" in c


def test_version_publiee_apres_verification_distante():
    c = WORKFLOW.read_text(encoding="utf-8")
    assert "--draft" in c
    assert "--draft=false" in c
    assert "--target" in c
    assert 'REVISION=$(git rev-parse HEAD)' not in c
    assert "SOURCE=$(git rev-parse HEAD)" in c
    assert "SHA256SUMS.txt" in c
    assert "sha256sum --check SHA256SUMS.txt" in c
    assert "cmp" in c
    assert "scripts/exporter_archive_boamp.py verifier" in c
    assert c.index("gh release create") < c.index('cmp "$DOSSIER/$f"')
    assert c.index('cmp "$DOSSIER/$f"') < c.index("gh release edit")
