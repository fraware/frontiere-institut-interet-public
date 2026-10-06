import json
from pathlib import Path


def test_quatre_cas_au_plafond_public():
    contenu = json.loads(Path("donnees/plafond_preuve_publique_v1.json").read_text(encoding="utf-8"))
    assert [cas["id_signal"] for cas in contenu["cas"]] == ["S001", "S016", "S024", "S042"]
    for cas in contenu["cas"]:
        assert cas["ce_que_les_sources_publiques_etablissent"]
        assert cas["ce_qui_manque"].strip()
        assert cas["source_la_plus_prometteuse"].strip()
        assert cas["statut"] == "plafond_public_atteint_provisoirement"


def test_note_plafond_preuve_documente_les_quatre_cas():
    texte = Path("docs/LIMITE_SOURCES_PUBLIQUES_V1.md").read_text(encoding="utf-8")
    for nom in ["France Compétences", "IGN", "Saint-Brieuc", "Sûreté nucléaire"]:
        assert nom in texte
