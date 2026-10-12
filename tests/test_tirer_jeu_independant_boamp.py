"""Tests de tirage préalable aux classements de résultats de marché."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest
from scripts.tirer_jeu_independant_boamp import (
    MOIS, QUOTA, EXCLUS, SEMENCE, TirageInvalide, tirer,
)


def index_artificiel(tmp_path: Path, *, retirer_mois=None):
    destination = tmp_path / "index.sqlite3"
    with sqlite3.connect(destination) as db:
        db.execute(
            "CREATE VIRTUAL TABLE recherche USING fts5("
            "jour UNINDEXED, identifiant UNINDEXED, objet, acheteur)"
        )
        for n, mois in enumerate(MOIS):
            if mois == retirer_mois:
                continue
            for i in range(9):
                db.execute(
                    "INSERT INTO recherche (jour,identifiant,objet,acheteur) "
                    "VALUES (?,?,?,?)",
                    (mois + "-15", f"{n + 30}-{i + 5000}",
                     f"Étude radar et modélisation scientifique {n} {i}",
                     f"Université fictive {n} {i}"),
                )
        # Des avis proches des pilotes restent exclus.
        db.execute(
            "INSERT INTO recherche (jour,identifiant,objet,acheteur) VALUES (?,?,?,?)",
            (MOIS[0] + "-15", "26-30147", "Traitement du signal radar",
             "Université de Caen Normandie"),
        )
    source = tmp_path / "preuve.json"
    source.write_text(json.dumps({
        "sha256_index": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "completude_historique_etablie": False,
    }), encoding="utf-8")
    return destination, source


def test_tirage_deterministe_distinct_et_sans_etiquettes(tmp_path):
    index, preuve = index_artificiel(tmp_path)
    a = tirer(index, preuve)
    b = tirer(index, preuve)
    assert a == b
    assert a["nombre_cas"] == QUOTA * len(MOIS)
    assert len({c["avis"] for c in a["cas"]}) == a["nombre_cas"]
    assert not ({c["avis"] for c in a["cas"]} & EXCLUS)
    assert set(a["effectifs_par_mois"].values()) == {QUOTA}
    assert a["etiquettes_officielles_verifiees"] is False
    assert a["etude_independante_effectuee"] is False
    assert a["comparaison_de_methodes_effectuee"] is False
    assert all(c["mecanisme_de_competences_non_evalue"] for c in a["cas"])


def test_modification_index_interromp_tirage(tmp_path):
    index, preuve = index_artificiel(tmp_path)
    with index.open("ab") as f:
        f.write(b"alteration")
    with pytest.raises(TirageInvalide, match="Index différent"):
        tirer(index, preuve)


def test_mois_incomplet_interrompt_le_tirage(tmp_path):
    index, preuve = index_artificiel(tmp_path, retirer_mois=MOIS[-1])
    with pytest.raises(TirageInvalide, match="Quota"):
        tirer(index, preuve)


def test_empreinte_tirage_est_reproductible(tmp_path):
    index, preuve = index_artificiel(tmp_path)
    resultat = tirer(index, preuve)
    liste = [c["avis"] for c in resultat["cas"]]
    attendu = hashlib.sha256(json.dumps(
        liste, ensure_ascii=False, separators=(",", ":"),
    ).encode()).hexdigest()
    assert resultat["sha256_identifiants_ordonnes"] == attendu
