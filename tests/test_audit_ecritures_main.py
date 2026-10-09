"""Tests de détection des écritures directes vers main."""
from pathlib import Path

from scripts.auditer_ecritures_main import auditer


def test_inventory_actuel_signale_dette_sans_fausse_protection():
    bilan = auditer()
    assert bilan["conformite_absence_nouveaux_push"] is True
    assert bilan["protection_main_confirmee"] is False
    assert {x["procedure"] for x in bilan["ecritures_directes_detectees"]} == {
        "ingestion-roae.yml", "ingestion-annuaire-local.yml",
        "ingestion-cog.yml",
    }


def test_une_nouvelle_ecriture_directe_provoque_une_alerte(tmp_path: Path):
    (tmp_path / "autre.yml").write_text("run: |\n  git push origin HEAD:main\n", encoding="utf-8")
    bilan = auditer(tmp_path)
    assert bilan["nouvelles_ecritures"] == ["autre.yml"]
    assert bilan["conformite_absence_nouveaux_push"] is False


def test_commande_de_lecture_ne_cree_aucune_alerte(tmp_path: Path):
    (tmp_path / "lecture.yml").write_text("run: git fetch origin main\n", encoding="utf-8")
    bilan = auditer(tmp_path)
    assert bilan["ecritures_directes_detectees"] == []
