from pathlib import Path
import re

FICHIERS_PUBLICS = [
    Path("README.md"),
    Path("CONTRIBUTION.md"),
    Path("SECURITE.md"),
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
