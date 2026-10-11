"""Essais sans accès réseau des comptages documentaires BOAMP."""
from contextlib import closing
from datetime import date
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from scripts.rechercher_historique_boamp import VERSION, preparer_base
from scripts.analyser_historique_boamp import (
    BilanInvalide, ecrire, intervalles, produire,
)


def dossier_index(tmp_path):
    base = tmp_path / "index.sqlite3"
    preuve = tmp_path / "preuve-index.json"
    with closing(sqlite3.connect(base)) as conn:
        preparer_base(conn)
        conn.executemany(
            "INSERT INTO provenance VALUES (?,?,?,?,?,?,?,?,?)",
            [
                ("2026-10-01", "origine-a", "a"*64, 2, "origine-a", "a"*64,
                 2, "2026-10-04T00:00:00+00:00", 0),
                ("2026-10-03", "origine-b", "b"*64, 2, "origine-b", "b"*64,
                 2, "2026-10-04T00:00:00+00:00", 0),
            ],
        )
        conn.executemany(
            "INSERT INTO recherche VALUES (?,?,?,?,?,?,?,?,?)",
            [
                ("2026-10-01", "a-1", "Étude intelligence artificielle et cybersécurité",
                 "Collectivité A", "https://www.boamp.fr/a", "SERVICES",
                 "INITIAL", "origine-a", "2026-10-04"),
                ("2026-10-01", "a-2", "Robotique et robot de laboratoire",
                 "Collectivité A", "https://www.boamp.fr/b", "SERVICES",
                 "INITIAL", "origine-a", "2026-10-04"),
                ("2026-10-03", "b-1", "Diagnostic de géomatique",
                 "Établissement B", "https://www.boamp.fr/c", "FOURNITURES",
                 "INITIAL", "origine-b", "2026-10-04"),
                ("2026-10-03", "b-2", "Matériel de bureau",
                 "Établissement B", "https://www.boamp.fr/d", None,
                 "INITIAL", "origine-b", "2026-10-04"),
            ],
        )
        conn.execute(
            "INSERT INTO informations VALUES ('version', ?)", (VERSION,),
        )
        conn.commit()
    preuve.write_text(json.dumps({
        "version": "publication-index-boamp-v1",
        "revision_depot": "a" * 40,
        "sha256_index": hashlib.sha256(base.read_bytes()).hexdigest(),
        "jours_indexes": 2,
        "avis_indexes": 4,
    }), encoding="utf-8")
    return base, preuve


def test_tableau_archive_avec_denominatrice_et_recouvrements(tmp_path):
    base, preuve = dossier_index(tmp_path)
    b = produire(base, preuve)
    assert b["version"] == "bilan-documentaire-boamp-v1"
    assert b["nombre_avis"] == 4
    assert b["couverture"]["jours_archives"] == 2
    assert b["couverture"]["jours_calendaires_dans_intervalle"] == 3
    assert b["couverture"]["exemples_jours_non_archives"] == ["2026-10-02"]
    assert b["par_mois"] == [
        {"mois": "2026-10", "jours_archives": 2, "avis": 4},
    ]
    assert b["themes_lexicaux"]["intelligence_artificielle"]["avis"] == 1
    assert b["themes_lexicaux"]["cybersecurite"]["avis"] == 1
    assert b["themes_lexicaux"]["robotique"]["avis"] == 1
    assert b["themes_lexicaux"]["imagerie_et_geographie"]["avis"] == 1
    assert b["total_correspondances_avec_recouvrements"] == 4
    assert b["categories_declarees"][0] == {"categorie": "SERVICES", "avis": 2}
    assert b["principaux_acheteurs_declares"][0]["avis"] == 2
    assert b["preuve_de_penurie_de_competences"] is False
    assert b["completude_historique_etablie"] is False
    sortie = tmp_path / "bilan.json"
    ecrire(b, sortie)
    avant = sortie.read_bytes()
    ecrire(produire(base, preuve), sortie)
    assert sortie.read_bytes() == avant


def test_index_modifie_refuse_avant_lecture(tmp_path):
    base, preuve = dossier_index(tmp_path)
    with closing(sqlite3.connect(base)) as conn:
        conn.execute("INSERT INTO informations VALUES('autre', 'donnee')")
        conn.commit()
    with pytest.raises(BilanInvalide, match="Empreinte"):
        produire(base, preuve)


def test_decomptes_incoherents_interrompent_rapport(tmp_path):
    base, preuve = dossier_index(tmp_path)
    p = json.loads(preuve.read_text(encoding="utf-8"))
    p["avis_indexes"] = 12
    preuve.write_text(json.dumps(p), encoding="utf-8")
    with pytest.raises(BilanInvalide, match="Décomptes"):
        produire(base, preuve)


def test_intervalle_jours_valides_et_doublons():
    assert intervalles(["2026-01-01", "2026-01-02"])["jours_non_archives_dans_intervalle"] == 0
    with pytest.raises(BilanInvalide, match="dupliquée"):
        intervalles(["2026-01-01", "2026-01-01"])
    with pytest.raises(BilanInvalide, match="Date"):
        intervalles(["2026-02-31"])
