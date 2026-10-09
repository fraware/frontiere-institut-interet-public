"""La fabrication de l'index conserve des garanties de provenance et de portée."""
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def test_index_boamp_automatise_depuis_main_et_sans_push():
    contenu = (RACINE / ".github/workflows/index-boamp-historique.yml").read_text(
        encoding="utf-8"
    )
    assert "ref: main" in contenu
    assert "persist-credentials: false" in contenu
    assert "institutionnel/besoins_publics/historique_boamp/**" in contenu
    assert "scripts/rechercher_historique_boamp.py indexer" in contenu
    assert "sqlite3" in contenu
    assert "sha256_index" in contenu
    assert '["git", "rev-parse", "HEAD"]' in contenu
    assert '"revision_depot": revision_lue' in contenu
    assert '"revision_evenement_github": os.environ["GITHUB_SHA"]' in contenu
    assert "PRAGMA integrity_check" in contenu
    assert "actions/upload-artifact@v4" in contenu
    assert "retention-days: 14" in contenu
    assert "git push" not in contenu
    assert "contents: write" not in contenu
    assert "contents: read" in contenu
