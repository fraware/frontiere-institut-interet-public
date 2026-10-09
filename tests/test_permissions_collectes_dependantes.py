"""Vérifier les procédures passées en lecture seule et la chaîne programmée."""
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
DOSSIER = RACINE / ".github/workflows"


def procedure(nom: str) -> str:
    return (DOSSIER / nom).read_text(encoding="utf-8")


def test_trois_controles_historiques_sans_ecriture():
    for nom in ("ingestion-roae.yml", "ingestion-annuaire-local.yml", "ingestion-cog.yml"):
        contenu = procedure(nom)
        assert "pull_request:" in contenu
        assert "contents: read" in contenu
        assert "contents: write" not in contenu
        assert "pull-requests: write" not in contenu
        assert "actions: write" not in contenu
        assert "git push" not in contenu
        assert "gh auth" not in contenu
        assert "workflow_run:" not in contenu
        assert "schedule:" not in contenu
        assert "persist-credentials: false" in contenu
        assert "github.workflow, github.event.pull_request.number" in contenu


def test_chaine_programmee_et_seule_habilitee_pour_ces_trois_sources():
    contenu = procedure("preparer-proposition-referentiel.yml")
    assert 'cron: "47 5 * * *"' in contenu
    assert "cancel-in-progress: false" in contenu
    assert "contents: write" in contenu
    assert "pull-requests: write" in contenu
    assert "actions: write" in contenu
    assert "persist-credentials: false" in contenu
    assert "scripts/publier_mise_a_jour_institutionnelle.py --source referentiel --publier" in contenu
    assert "git push origin HEAD:main" not in contenu
    assert "if: ${{ github.event_name == 'schedule' || inputs.publier }}" in contenu
    assert "if: ${{ github.event_name != 'schedule' && !inputs.publier }}" in contenu
