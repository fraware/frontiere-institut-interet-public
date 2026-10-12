"""Tests du contrôle enrichi sans étiquettes d'attribution."""
import hashlib
import json
import sqlite3

import pytest

import scripts.tirer_ensemble_epreuve_infructueux_boamp as module
from scripts.tirer_jeu_independant_boamp import MOIS as MOIS_BASE, QUOTA as QUOTA_BASE
from scripts.tirer_jeu_independant_boamp import VERSION as VERSION_BASE


def preparer(tmp_path, monkeypatch, omettre=None):
    dbp = tmp_path / "index.sqlite3"
    with sqlite3.connect(dbp) as db:
        db.execute(
            "CREATE VIRTUAL TABLE recherche USING fts5("
            "jour UNINDEXED,identifiant UNINDEXED,objet,acheteur)"
        )
        i = 20000
        for mois in module.MOIS:
            if mois == omettre:
                continue
            for n in range(7):
                db.execute(
                    "INSERT INTO recherche(jour,identifiant,objet,acheteur) VALUES (?,?,?,?)",
                    (mois + "-18", f"26-{i}", f"Relance de lot infructueux {mois} {n}",
                     f"Collectivité modèle {mois} {n}"),
                )
                i += 1
        db.execute(
            "INSERT INTO recherche(jour,identifiant,objet,acheteur) VALUES (?,?,?,?)",
            ("2025-07-18", "26-30147", "Lot infructueux radar",
             "Université fictive"),
        )
    preuve = tmp_path / "index.json"
    preuve.write_text(json.dumps({
        "sha256_index": hashlib.sha256(dbp.read_bytes()).hexdigest(),
    }))
    cas = []
    n = 10000
    for mois in MOIS_BASE:
        for _ in range(QUOTA_BASE):
            cas.append({"avis": f"26-{n}", "date_parution": mois + "-15"})
            n += 1
    ids = [c["avis"] for c in cas]
    empreinte = hashlib.sha256(json.dumps(
        ids, ensure_ascii=False, separators=(",", ":")
    ).encode()).hexdigest()
    base = tmp_path / "base.json"
    base.write_text(json.dumps({
        "version": VERSION_BASE, "nombre_cas": len(cas),
        "cas": cas, "sha256_identifiants_ordonnes": empreinte,
        "etiquettes_officielles_verifiees": False,
        "comparaison_de_methodes_effectuee": False,
    }))
    monkeypatch.setattr(module, "EMPREINTE_BASE", empreinte)
    return dbp, preuve, base


def test_tirage_distinct_deterministe_et_explicitement_biaise(tmp_path, monkeypatch):
    dbp, preuve, base = preparer(tmp_path, monkeypatch)
    a = module.tirer(dbp, preuve, base)
    b = module.tirer(dbp, preuve, base)
    assert a == b
    assert a["nombre_cas"] == 24
    assert a["selection_sur_mention_potentiellement_liee_au_resultat"] is True
    assert a["selection_sans_information_de_resultat"] is False
    assert a["issues_verifiees_par_lot"] is False
    assert a["evaluation_independante_effectuee"] is False
    assert len({x["avis"] for x in a["cas"]}) == 24
    assert all(x["issue_reelle"] is None for x in a["cas"])
    assert not any(x["avis"] == "26-30147" for x in a["cas"])


def test_quota_impossible_est_refuse(tmp_path, monkeypatch):
    dbp, preuve, base = preparer(tmp_path, monkeypatch, omettre=module.MOIS[3])
    with pytest.raises(module.EpreuveInvalide, match="Quota"):
        module.tirer(dbp, preuve, base)


def test_empreinte_source_modifiee_est_refusee(tmp_path, monkeypatch):
    dbp, preuve, base = preparer(tmp_path, monkeypatch)
    with dbp.open("ab") as f:
        f.write(b"altération")
    with pytest.raises(module.EpreuveInvalide, match="Index"):
        module.tirer(dbp, preuve, base)


def test_reference_originale_incorrecte_est_refusee(tmp_path, monkeypatch):
    dbp, preuve, base = preparer(tmp_path, monkeypatch)
    monkeypatch.setattr(module, "EMPREINTE_BASE", "f" * 64)
    with pytest.raises(module.EpreuveInvalide, match="différent"):
        module.tirer(dbp, preuve, base)
