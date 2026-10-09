"""Contrôler la séparation entre essais externes et publication de confiance."""
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def workflow(nom: str) -> str:
    return (RACINE / ".github/workflows" / nom).read_text(encoding="utf-8")


def test_structures_de_recherche_n_ecrivent_plus_directement_sur_main():
    contenu = workflow("ingestion-rnsr.yml")
    assert "git push" not in contenu
    assert "scripts/publier_mise_a_jour_institutionnelle.py --source rnsr --publier" in contenu
    assert "if: github.event_name == 'pull_request'" in contenu
    assert "if: github.event_name != 'pull_request'" in contenu
    assert "persist-credentials: false" in contenu
    assert "pull-requests: write" in contenu
    assert "actions: write" in contenu


def test_surveillance_conserve_le_signal_d_incident_sans_ecriture_directe():
    contenu = workflow("surveillance-institutionnelle.yml")
    assert "git push" not in contenu
    assert "scripts/publier_mise_a_jour_institutionnelle.py --source surveillance --publier" in contenu
    assert "persist-credentials: false" in contenu
    assert "steps.surveillance.outputs.code == '2'" in contenu
    assert "      - name: Signaler une source critique indisponible" in contenu


def test_roles_limited_by_jobs_for_external_proposals():
    contenu = workflow("ingestion-rnsr.yml")
    verifier = contenu.split("  verification-proposition:\n", 1)[1].split("\n  ingestion:\n", 1)[0]
    assert "contents: read" in verifier
    assert "contents: write" not in verifier
    assert "GH_TOKEN:" not in verifier
