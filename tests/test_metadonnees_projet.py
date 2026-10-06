from pathlib import Path
import re
import tomllib

from app import __version__
from app.main import app

RACINE = Path(__file__).resolve().parents[1]


def _version_citation() -> str:
    texte = (RACINE / "CITATION.cff").read_text(encoding="utf-8")
    correspondance = re.search(r"^version:\s*[\"']?([^\"'\s]+)", texte, flags=re.MULTILINE)
    assert correspondance is not None
    return correspondance.group(1)


def test_versions_du_projet_synchronisees():
    pyproject = tomllib.loads((RACINE / "pyproject.toml").read_text(encoding="utf-8"))
    version_paquet = pyproject["project"]["version"]

    assert version_paquet == __version__
    assert version_paquet == app.version
    assert version_paquet == _version_citation()


def test_un_seul_guide_de_contribution():
    assert (RACINE / "CONTRIBUTING.md").is_file()
    assert not (RACINE / "CONTRIBUTION.md").exists()


def test_fichiers_de_gouvernance_presents():
    for chemin in [
        RACINE / "SECURITE.md",
        RACINE / ".github" / "SECURITY.md",
        RACINE / ".github" / "PULL_REQUEST_TEMPLATE.md",
        RACINE / "CHANGELOG.md",
        RACINE / "CITATION.cff",
        RACINE / "docs" / "INDEX.md",
        RACINE / "docs" / "REPRODUCTIBILITE.md",
    ]:
        assert chemin.is_file(), f"Fichier attendu absent : {chemin.relative_to(RACINE)}"
