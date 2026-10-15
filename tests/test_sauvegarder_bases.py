"""Sauvegarde SQLite à chaud, vérification intégrale et reprises hors réseau."""
import json
import sqlite3
from pathlib import Path

import pytest

from scripts.sauvegarder_bases import (
    SauvegardeInvalide, _entrees, _copier_sqlite, sauvegarder, verifier,
)

SCHEMAS = {
    "boamp": "avis_boamp versions_avis_boamp captures_boamp",
    "emplois": "versions_emplois_publics captures_emplois_publics",
    "decp": "marches versions fichiers_sources",
}


def exemples(tmp_path):
    bases = {}
    for nom, tables in SCHEMAS.items():
        fichier = tmp_path / f"source_{nom}.sqlite3"
        with sqlite3.connect(fichier) as conn:
            for table in tables.split():
                conn.execute(f"CREATE TABLE {table}(id TEXT PRIMARY KEY)")
                conn.execute(f"INSERT INTO {table} VALUES (?)", (nom,))
        bases[nom] = fichier
    return bases


def test_sauvegarde_et_verification_des_trois_bases(tmp_path):
    sources = exemples(tmp_path)
    dossier = sauvegarder(sources, tmp_path / "externe")
    assert dossier.parent == tmp_path / "externe"
    resultat = verifier(dossier)
    assert resultat["etat"] == "verifiee"
    assert resultat["bases_verifiees"] == 3
    assert resultat["archives_brutes_incluses"] is False
    manifest = json.loads((dossier / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["instantane_multi_bases_global"] is False
    for nom in sources:
        with sqlite3.connect(dossier / f"{nom}.sqlite3") as conn:
            table = SCHEMAS[nom].split()[0]
            assert conn.execute(f"SELECT id FROM {table}").fetchone()[0] == nom
    assert len(list(dossier.glob("*.sqlite3"))) == 3


def test_copie_source_continue_a_ecrire_sans_modifier_sauvegarde(tmp_path):
    sources = exemples(tmp_path)
    dossier = sauvegarder(sources, tmp_path / "externe")
    with sqlite3.connect(sources["boamp"]) as conn:
        conn.execute("INSERT INTO avis_boamp VALUES ('nouvel-avis')")
    with sqlite3.connect(dossier / "boamp.sqlite3") as conn:
        assert conn.execute("SELECT COUNT(*) FROM avis_boamp").fetchone()[0] == 1
    assert verifier(dossier)["bases_verifiees"] == 3


def test_empreinte_incorrecte_refusee(tmp_path):
    sources = exemples(tmp_path)
    dossier = sauvegarder(sources, tmp_path / "externe")
    with sqlite3.connect(dossier / "decp.sqlite3") as conn:
        conn.execute("INSERT INTO marches VALUES ('manipulation')")
    with pytest.raises(SauvegardeInvalide, match="Empreinte"):
        verifier(dossier)


def test_sauvegarde_partielle_ne_laisse_pas_de_faux_manifeste(tmp_path, monkeypatch):
    sources = exemples(tmp_path)
    orig = _copier_sqlite
    def echec(source, destination, nom):
        if nom == "decp":
            raise OSError("Disque saturé")
        return orig(source, destination, nom)
    monkeypatch.setattr("scripts.sauvegarder_bases._copier_sqlite", echec)
    with pytest.raises(OSError):
        sauvegarder(sources, tmp_path / "externe")
    assert list((tmp_path / "externe").iterdir()) == []


def test_source_absente_schema_incompatible_et_liste_duplicative(tmp_path):
    sources = exemples(tmp_path)
    sources["emplois"] = tmp_path / "absente.db"
    with pytest.raises(SauvegardeInvalide, match="introuvable"):
        sauvegarder(sources, tmp_path / "copies")
    autre_dossier = tmp_path / "nouvelle_source"
    autre_dossier.mkdir()
    sources = exemples(autre_dossier)
    with sqlite3.connect(sources["decp"]) as conn:
        conn.execute("DROP TABLE marches")
    with pytest.raises(SauvegardeInvalide, match="Schéma"):
        sauvegarder(sources, tmp_path / "copies")
    assert list((tmp_path / "copies").iterdir()) == []
    with pytest.raises(SauvegardeInvalide, match="répété"):
        _entrees(["decp=/tmp/un.db", "decp=/tmp/deux.db"])
