"""Tests de tirage stratifié sans accès aux sources extérieures."""
from contextlib import closing
from datetime import date, timedelta
import hashlib
import json
import sqlite3
import pytest

from scripts.analyser_historique_boamp import (
    BilanInvalide, produire, ecrire as ecrire_bilan,
)
from scripts.rechercher_historique_boamp import VERSION, preparer_base
from scripts.echantillonner_avis_boamp import (
    constituer, ecrire, mois_couverts, categorie_strate, TEMOIN,
)


def jeu(tmp_path):
    index, preuve, bilan = (
        tmp_path / "index.sqlite3",
        tmp_path / "preuve.json",
        tmp_path / "bilan.json",
    )
    with closing(sqlite3.connect(index)) as conn:
        preparer_base(conn)
        conn.execute("INSERT INTO informations VALUES('version', ?)", (VERSION,))
        for j in range(1, 32):
            jour = f"2026-01-{j:02d}"
            conn.execute(
                "INSERT INTO provenance VALUES(?,?,?,?,?,?,?,?,?)",
                (jour, "archive.gz", "a" * 64, 2, "archive.gz", "a" * 64,
                 2, "2026-02-02T00:00:00+00:00", 0),
            )
            objets = [
                "Robotique et intelligence artificielle" if j == 1
                else "Étude en intelligence artificielle",
                "Fourniture courante de bureaux",
            ]
            for n, objet in enumerate(objets):
                code = f"26-{j:02d}-{n}"
                conn.execute(
                    "INSERT INTO recherche VALUES (?,?,?,?,?,?,?,?,?)",
                    (jour, code, objet, "Acheteur fictif",
                     "https://www.boamp.fr/" + code, "SERVICES",
                     "INITIAL", "archive.gz", "2026-02-02T00:00:00+00:00"),
                )
        conn.execute(
            "INSERT INTO provenance VALUES(?,?,?,?,?,?,?,?,?)",
            ("2026-02-01", "archive.gz", "b" * 64, 1,
             "archive.gz", "b" * 64, 1, "2026-02-02T00:00:00+00:00", 0),
        )
        conn.execute(
            "INSERT INTO recherche VALUES(?,?,?,?,?,?,?,?,?)",
            ("2026-02-01", "26-999", "Cybersecurite des réseaux", "Temoin",
             "https://www.boamp.fr/26-999", "SERVICES",
             "INITIAL", "archive.gz", "2026-02-02T00:00:00+00:00"),
        )
        conn.commit()
    preuve.write_text(json.dumps({
        "version": "publication-index-boamp-v1", "revision_depot": "a" * 40,
        "sha256_index": hashlib.sha256(index.read_bytes()).hexdigest(),
        "jours_indexes": 32, "avis_indexes": 63,
    }), encoding="utf-8")
    ecrire_bilan(produire(index, preuve), bilan)
    return index, preuve, bilan


def test_selection_avec_mois_complets_et_temoin(tmp_path):
    index, preuve, bilan = jeu(tmp_path)
    e = constituer(index, preuve, bilan, quota=3)
    assert e["nombre_avis_examines"] == 63
    assert e["mois_complets"] == ["2026-01"]
    assert e["nombre_avis_mois_incomplets_exclus"] == 1
    assert e["nombre_avis_multithemes"] == 1
    assert e["nombre_strates"] == 3
    assert e["nombre_tirages"] == 7
    assert e["nombre_avis_distincts"] in (6, 7)
    assert e["temoin_ne_signifie_pas_absence_de_besoin"]
    s = {(r["mois"], r["categorie"], r["domaine"]): r for r in e["strates"]}
    ai = s[("2026-01", "SERVICES", "intelligence_artificielle")]
    assert ai["population_documentaire"] == 31
    assert ai["nombre_tire"] == 3
    assert ai["fraction_tirage"] == {"numerateur": 3, "denominateur": 31}
    assert len(s[("2026-01", "SERVICES", TEMOIN)]["avis"]) == 3
    assert s[("2026-01", "SERVICES", "robotique")]["nombre_tire"] == 1
    assert all(not v["besoin_scientifique_valide"]
               for st in e["strates"] for v in st["avis"])


def test_reproductible_sensible_a_la_semence_et_refus_sources_modifiees(tmp_path):
    index, preuve, bilan = jeu(tmp_path)
    a = constituer(index, preuve, bilan, quota=4, semence="experience-alpha")
    b = constituer(index, preuve, bilan, quota=4, semence="experience-alpha")
    c = constituer(index, preuve, bilan, quota=4, semence="experience-beta")
    assert a == b
    assert a != c
    cible = tmp_path / "tirage.json"
    ecrire(a, cible)
    original = cible.read_bytes()
    ecrire(b, cible)
    assert cible.read_bytes() == original
    with pytest.raises(BilanInvalide, match="Quota"):
        constituer(index, preuve, bilan, quota=0)
    texte = json.loads(bilan.read_text(encoding="utf-8"))
    texte["nombre_avis"] = 999
    bilan.write_text(json.dumps(texte), encoding="utf-8")
    with pytest.raises(BilanInvalide, match="Bilan"):
        constituer(index, preuve, bilan)
    assert cible.read_bytes() == original


def test_controle_mois_incomplets_et_categories():
    jours = [f"2026-01-{j:02d}" for j in range(1, 32)] + ["2026-02-01"]
    complets, stats = mois_couverts(jours)
    assert complets == ["2026-01"]
    assert stats[-1]["jours_archives"] == 1
    assert categorie_strate("Fournitures") == "FOURNITURES"
    assert categorie_strate("Prestations de services") == "SERVICES"
    assert categorie_strate(None) == "AUTRE"
    with pytest.raises(BilanInvalide):
        mois_couverts(["2026-02-01", "2026-02-01"])
    with pytest.raises(BilanInvalide):
        mois_couverts(["2026-02-31"])
