from pathlib import Path
import re
from urllib.parse import unquote

RACINE = Path(__file__).resolve().parents[1]

DOCUMENTS = [
    RACINE / "README.md",
    RACINE / "CONTRIBUTING.md",
    RACINE / "CHANGELOG.md",
    RACINE / "SECURITE.md",
    *(RACINE / "docs").glob("*.md"),
    *(RACINE / "evaluation").glob("*.md"),
    *(RACINE / ".github").glob("*.md"),
]

LIEN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def test_liens_relatifs_de_documentation_resolus():
    erreurs = []
    for document in sorted(DOCUMENTS):
        texte = document.read_text(encoding="utf-8")
        for cible_brute in LIEN.findall(texte):
            cible = cible_brute.strip().strip("<>")
            if not cible or cible.startswith(("#", "http://", "https://", "mailto:")):
                continue

            chemin_brut = unquote(cible.split("#", 1)[0].split("?", 1)[0])
            if not chemin_brut:
                continue

            chemin = (document.parent / chemin_brut).resolve()
            try:
                chemin.relative_to(RACINE)
            except ValueError:
                erreurs.append(f"{document.relative_to(RACINE)} -> {cible} sort du dépôt")
                continue

            if not chemin.exists():
                erreurs.append(f"{document.relative_to(RACINE)} -> {cible}")

    assert not erreurs, "Liens relatifs introuvables :\n" + "\n".join(erreurs)
