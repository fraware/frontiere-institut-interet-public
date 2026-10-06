from pathlib import Path
import re

FICHIERS_PUBLICS = [
    Path("README.md"),
    Path("CONTRIBUTING.md"),
    Path("CHANGELOG.md"),
    Path("SECURITE.md"),
    Path(".github/SECURITY.md"),
    Path(".github/PULL_REQUEST_TEMPLATE.md"),
    *sorted(Path(".github/ISSUE_TEMPLATE").glob("*.yml")),
    *sorted(Path("docs").glob("*.md")),
    *sorted(Path("evaluation").glob("*.md")),
    *sorted(Path("evaluation").glob("*.json")),
    *sorted(Path("app/templates").glob("*.html")),
]

TERMES_INTERDITS = [
    "benchmark",
    "holdout",
    "runner",
    "outreach",
    "pipeline",
    "baseline",
    "scoring",
    "scorer",
    "capability query",
    "dataset",
    "data scientist",
    "workflow",
    "feedback",
    "roadmap",
    "stakeholder",
    "matching",
    "shadow sourcing",
    "inside-first",
    "additionalité",
    "contrefactuel",
]


def present(texte: str, terme: str) -> bool:
    motif = r"(?<![A-Za-zÀ-ÿ])" + re.escape(terme) + r"(?![A-Za-zÀ-ÿ])"
    return re.search(motif, texte, flags=re.IGNORECASE) is not None


def test_documents_et_interface_en_francais_clair():
    problemes = []
    for chemin in FICHIERS_PUBLICS:
        if not chemin.exists():
            continue
        texte = chemin.read_text(encoding="utf-8")
        trouves = [terme for terme in TERMES_INTERDITS if present(texte, terme)]
        if trouves:
            problemes.append(f"{chemin}: {', '.join(trouves)}")
    assert not problemes, "Termes à reformuler :\n" + "\n".join(problemes)


def test_textes_generes_et_messages_publics_en_francais_clair():
    controles = {
        Path("scripts/initialiser_demonstration.py"): ["data scientist"],
        Path("app/main.py"): ["additionalité", "contrefactuel"],
    }
    problemes = []
    for chemin, termes in controles.items():
        texte = chemin.read_text(encoding="utf-8")
        trouves = [terme for terme in termes if present(texte, terme)]
        if trouves:
            problemes.append(f"{chemin}: {', '.join(trouves)}")
    assert not problemes, "Termes publics à reformuler :\n" + "\n".join(problemes)
