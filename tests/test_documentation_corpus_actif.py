"""Éviter que les modes d'emploi désignent des versions de corpus obsolètes."""
from pathlib import Path
import re

RACINE = Path(__file__).resolve().parents[1]


def valeur_par_defaut(script: str, option: str) -> str:
    """Lire le chemin de source choisi par défaut dans une commande publique."""
    code = (RACINE / script).read_text(encoding="utf-8")
    motif = (
        r'add_argument\("' + re.escape(option)
        + r'",\s*type=Path,\s*default=Path\("(donnees/[^"]+)"\)\)'
    )
    correspondances = re.findall(motif, code)
    assert len(correspondances) == 1, f"Option {option} introuvable ou ambiguë."
    return correspondances[0]


def test_guide_de_reproduction_documente_la_chronologie_active():
    chemin = valeur_par_defaut("scripts/verifier_corpus_public.py", "--chronologies")
    texte = (RACINE / "docs/REPRODUCTIBILITE.md").read_text(encoding="utf-8")
    assert f"collection active `{chemin}`" in texte


def test_guide_de_reproduction_documente_les_passages_actifs():
    chemin = valeur_par_defaut("scripts/verifier_passages_sources.py", "--passages")
    texte = (RACINE / "docs/REPRODUCTIBILITE.md").read_text(encoding="utf-8")
    assert f"pièces primaires est conservé dans `{chemin}`" in texte
