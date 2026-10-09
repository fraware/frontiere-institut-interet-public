"""Continuité temporaire des collectes avec séparation des droits des essais."""
from pathlib import Path

DOSSIER = Path(__file__).resolve().parents[1] / ".github/workflows"


def procedure(nom: str) -> str:
    return (DOSSIER / nom).read_text(encoding="utf-8")


def test_rnsr_conserve_un_essai_en_lecture_seule():
    contenu = procedure("ingestion-rnsr.yml")
    essai, collecte = contenu.split("  verification-proposition:\n", 1)[1].split("\n  ingestion:\n", 1)
    assert "contents: read" in essai
    assert "contents: write" not in essai
    assert "GH_TOKEN" not in essai
    assert "persist-credentials: false" in essai
    assert "    permissions:\n      contents: write" in collecte
    assert "pull-requests: write" not in collecte
    assert "actions: write" not in collecte
    assert "git push origin HEAD:main" in collecte
    assert "gh auth setup-git" in collecte


def test_surveillance_conserve_les_alertes_et_retire_les_droits_superflus():
    contenu = procedure("surveillance-institutionnelle.yml")
    assert "permissions:\n  contents: read" in contenu
    assert "    permissions:\n      contents: write" in contenu
    assert "pull-requests: write" not in contenu
    assert "actions: write" not in contenu
    assert "persist-credentials: false" in contenu
    assert "steps.surveillance.outputs.code == '2'" in contenu
    assert "git push origin HEAD:main" in contenu
    assert "gh auth setup-git" in contenu
