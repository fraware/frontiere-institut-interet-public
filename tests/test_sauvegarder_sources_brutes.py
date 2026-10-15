"""Essais de copie en flux et restauration vérifiable des originaux."""
import json
from pathlib import Path

import pytest

from scripts.sauvegarder_sources_brutes import (
    ArchiveBruteInvalide, sauvegarder, verifier, _relatif,
)


def deux_sources(tmp_path):
    boamp = tmp_path / "boamp"
    decp = tmp_path / "decp"
    (boamp / "2026").mkdir(parents=True)
    decp.mkdir()
    (boamp / "2026" / "avis.jsonl").write_text(
        '{"id": 1}\n{"id": 2}\n', encoding="utf-8"
    )
    (decp / "consolide.json").write_bytes(b'{"marches":[]}')
    (decp / ".decp-temp").write_text("écriture temporaire", encoding="utf-8")
    (decp / "marches.sqlite3").write_bytes(b"base indépendante")
    return {"boamp": boamp, "decp": decp}


def test_sauvegarde_de_deux_repertoires_et_fichiers_bruts(tmp_path):
    source = deux_sources(tmp_path)
    dossier = sauvegarder(source, tmp_path / "archive-externe")
    bilan = verifier(dossier)
    assert bilan["etat"] == "verifiee"
    assert bilan["nombre_fichiers"] == 2
    assert bilan["originaux_verifies"] is True
    assert (dossier / "originaux/boamp/2026/avis.jsonl").is_file()
    assert (dossier / "originaux/decp/consolide.json").is_file()
    assert not (dossier / "originaux/decp/marches.sqlite3").exists()
    assert not (dossier / "originaux/decp/.decp-temp").exists()
    manifest = json.loads((dossier / "manifest.json").read_text())
    assert manifest["repertoires_attendus"] == ["boamp", "decp"]
    assert manifest["octets_bruts"] == bilan["octets_bruts"]


def test_changement_ulterieur_de_source_ne_modifie_pas_sauvegarde(tmp_path):
    source = deux_sources(tmp_path)
    dossier = sauvegarder(source, tmp_path / "archive-externe")
    (source["decp"] / "consolide.json").write_text("nouvelle version")
    assert verifier(dossier)["nombre_fichiers"] == 2


def test_fichier_de_sauvegarde_altere_est_refuse(tmp_path):
    dossier = sauvegarder(deux_sources(tmp_path), tmp_path / "externe")
    (dossier / "originaux/decp/consolide.json").write_text("corrompu")
    with pytest.raises(ArchiveBruteInvalide, match="Empreinte"):
        verifier(dossier)


def test_fichier_source_etranger_empeche_publication_de_copie(tmp_path):
    sources = deux_sources(tmp_path)
    (sources["decp"] / "executable.exe").write_bytes(b"non document")
    destination = tmp_path / "externe"
    with pytest.raises(ArchiveBruteInvalide, match="format"):
        sauvegarder(sources, destination)
    assert list(destination.iterdir()) == []


def test_lien_symbolique_interdit(tmp_path):
    sources = deux_sources(tmp_path)
    (sources["boamp"] / "raccourci.json").symlink_to(
        sources["decp"] / "consolide.json"
    )
    with pytest.raises(ArchiveBruteInvalide, match="symbolique"):
        sauvegarder(sources, tmp_path / "externe")


def test_refus_des_destinations_embriquees_et_chemins_traversants(tmp_path):
    sources = deux_sources(tmp_path)
    with pytest.raises(ArchiveBruteInvalide, match="imbriquée"):
        sauvegarder(sources, sources["decp"] / "sous-dossier")
    for nom in ("../evasion.json", "/etc/passwd", "a/../b", "a/./b", ""):
        with pytest.raises(ArchiveBruteInvalide):
            _relatif(nom)


def test_manifeste_modifie_est_refuse(tmp_path):
    dossier = sauvegarder(deux_sources(tmp_path), tmp_path / "externe")
    path = dossier / "manifest.json"
    doc = json.loads(path.read_text())
    doc["fichiers"][0]["chemin"] = "../secret.json"
    path.write_text(json.dumps(doc))
    with pytest.raises(ArchiveBruteInvalide):
        verifier(dossier)
