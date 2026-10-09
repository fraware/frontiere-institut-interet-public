"""Les essais de propositions n'obtiennent aucun droit de modification distant."""
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def blocs(nom: str) -> tuple[str, str, str]:
    texte = (RACINE / ".github/workflows" / nom).read_text(encoding="utf-8")
    assert "jobs:\n  verification-proposition:\n" in texte
    haut, parties = texte.split("jobs:\n  verification-proposition:\n", 1)
    essai, collecte = parties.split("\n  ingestion:\n", 1)
    return haut, essai, collecte


def test_annuaire_et_territoires_separent_leurs_permissions():
    for nom in ("ingestion-annuaire-local.yml", "ingestion-cog.yml"):
        haut, essai, collecte = blocs(nom)
        assert "permissions:\n  contents: read" in haut
        assert "if: github.event_name == 'pull_request'" in essai
        assert "contents: read" in essai
        assert "contents: write" not in essai
        assert "GH_TOKEN" not in essai
        assert "git push" not in essai
        assert "persist-credentials: false" in essai
        assert "if: github.event_name != 'pull_request'" in collecte
        assert "permissions:\n      contents: write" in collecte
        assert "GH_TOKEN:" in collecte
        assert "persist-credentials: false" in collecte
        assert "gh auth setup-git" in collecte
        assert "git push origin HEAD:main" in collecte
        assert "pull-requests: write" not in collecte
        assert "actions: write" not in collecte


def test_dependances_de_collecte_et_alertes_conservees():
    annuaire = (RACINE / ".github/workflows/ingestion-annuaire-local.yml").read_text(encoding="utf-8")
    cog = (RACINE / ".github/workflows/ingestion-cog.yml").read_text(encoding="utf-8")
    assert 'workflows: ["Ingestion du référentiel DILA"]' in annuaire
    assert 'workflows: ["Ingestion de l\'annuaire local"]' in cog
    assert "github.event.workflow_run.conclusion == 'success'" in annuaire
    assert "github.event.workflow_run.conclusion == 'success'" in cog
    assert "cancel-in-progress: false" in annuaire
    assert "cancel-in-progress: false" in cog
