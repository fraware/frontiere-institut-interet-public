from pathlib import Path
import re

FICHIERS_PUBLICS = [
    *sorted(Path(".").glob("*.md")),
    *sorted(Path("docs").glob("*.md")),
    *sorted(Path("evaluation").glob("*.md")),
    Path("donnees/README.md"),
    Path("institutionnel/README.md"),
    Path(".github/SECURITY.md"),
    Path(".github/PULL_REQUEST_TEMPLATE.md"),
    *sorted(Path(".github/ISSUE_TEMPLATE").glob("*.yml")),
    *sorted(Path("evaluation").glob("*.json")),
    *sorted(Path("app/templates").glob("*.html")),
]

TERMES_INTERDITS = [
    "benchmark", "holdout", "runner", "outreach", "pipeline", "baseline", "snapshot",
    "scoring", "scorer", "capability query", "dataset", "data scientist",
    "workflow", "feedback", "roadmap", "stakeholder", "matching",
    "shadow sourcing", "inside-first", "additionalité", "contrefactuel",
]

MOTIFS_JARGON_INTERNE = [
    r"\bROAE\b", r"\bSL/SIL\b", r"\bSI\b", r"\bSL\b", r"\bSIL\b",
    r"\bP[0-3]\b", r"\bR[0-5]\b", r"\bD[0-4]\b",
    r"\bpoint zéro\b", r"\bcomparaison appariée\b", r"\bplan apparié\b",
    r"\bpré-enregistrement\b", r"\bscellement\b", r"\bsceller\b",
    r"\bscellé(?:e|es|s)?\b",
]


def present(texte: str, terme: str) -> bool:
    motif = r"(?<![A-Za-zÀ-ÿ])" + re.escape(terme) + r"(?![A-Za-zÀ-ÿ])"
    return re.search(motif, texte, flags=re.IGNORECASE) is not None


def texte_visible_markdown(texte: str) -> str:
    texte = re.sub(r"<!--.*?-->", " ", texte, flags=re.DOTALL)
    texte = re.sub(r"```.*?```", " ", texte, flags=re.DOTALL)
    texte = re.sub(r"`[^`]*`", " ", texte)
    texte = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", texte)
    return texte


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


def test_documentation_n_expose_pas_les_raccourcis_internes():
    documents = [
        *sorted(Path(".").glob("*.md")),
        *sorted(Path("docs").glob("*.md")),
        *sorted(Path("evaluation").glob("*.md")),
        Path("donnees/README.md"),
        Path("institutionnel/README.md"),
    ]
    problemes = []
    for chemin in documents:
        if not chemin.exists():
            continue
        visible = texte_visible_markdown(chemin.read_text(encoding="utf-8"))
        trouves = [motif for motif in MOTIFS_JARGON_INTERNE if re.search(motif, visible)]
        if trouves:
            problemes.append(f"{chemin}: {', '.join(trouves)}")
    assert not problemes, "Jargon interne à reformuler dans la documentation :\n" + "\n".join(problemes)


def test_textes_generes_et_messages_publics_en_francais_clair():
    controles = {
        Path("scripts/initialiser_demonstration.py"): ["data scientist"],
        Path("app/main.py"): ["additionalité", "contrefactuel", "point zéro", "comparaison appariée", "pré-enregistrement prospectif"],
        Path("app/templates/detail_cas.html"): ["point zéro", "plan apparié", "pré-enregistrement prospectif"],
    }
    problemes = []
    for chemin, termes in controles.items():
        texte = chemin.read_text(encoding="utf-8")
        trouves = [terme for terme in termes if present(texte, terme)]
        if trouves:
            problemes.append(f"{chemin}: {', '.join(trouves)}")
    assert not problemes, "Termes publics à reformuler :\n" + "\n".join(problemes)
