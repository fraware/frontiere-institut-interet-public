"""Sélection traçable d'avis publics et contrôle des limites d'interprétation."""
from contextlib import closing
import hashlib
import json
import sqlite3

import pytest

from scripts.rechercher_historique_boamp import VERSION, preparer_base
from scripts.analyser_historique_boamp import produire, ecrire as ecrire_bilan
from scripts.constituer_pistes_boamp import constituer, ecrire, BilanInvalide


def exemple(tmp_path):
    index = tmp_path / "index.sqlite3"
    preuve = tmp_path / "preuve-index.json"
    bilan = tmp_path / "bilan.json"
    with closing(sqlite3.connect(index)) as conn:
        preparer_base(conn)
        conn.execute("INSERT INTO informations VALUES('version', ?)", (VERSION,))
        conn.execute(
            "INSERT INTO provenance VALUES (?,?,?,?,?,?,?,?,?)",
            ("2026-10-01", "a.jsonl.gz", "a"*64, 5, "a.jsonl.gz", "a"*64,
             5, "2026-10-02T00:00:00+00:00", 0),
        )
        avis = [
            ("26-100", "Intelligence artificielle et cybersécurité", "Acheteur A"),
            ("26-101", "Intelligence artificielle en laboratoire", "Acheteur A"),
            ("26-102", "Intelligence artificielle", "Acheteur A"),
            ("26-103", "Intelligence artificielle", "Acheteur B"),
            ("26-104", "Bureaux administratifs", "Acheteur B"),
        ]
        conn.executemany(
            "INSERT INTO recherche VALUES (?,?,?,?,?,?,?,?,?)",
            [
                ("2026-10-01", idweb, objet, acheteur,
                 "https://www.boamp.fr/" + idweb, "SERVICES", "INITIAL",
                 "historique_boamp/2026/10/2026-10-01.jsonl.gz",
                 "2026-10-02T00:00:00+00:00")
                for idweb, objet, acheteur in avis
            ],
        )
        conn.commit()
    preuve.write_text(json.dumps({
        "version": "publication-index-boamp-v1",
        "revision_depot": "c" * 40,
        "sha256_index": hashlib.sha256(index.read_bytes()).hexdigest(),
        "jours_indexes": 1,
        "avis_indexes": 5,
    }), encoding="utf-8")
    ecrire_bilan(produire(index, preuve), bilan)
    return index, preuve, bilan


def test_selection_limite_par_acheteur_et_provenance(tmp_path):
    index, preuve, bilan = exemple(tmp_path)
    r = constituer(index, preuve, bilan, plafond=5, plafond_acheteur=2)
    artificielle = r["pistes"]["intelligence_artificielle"]
    assert artificielle["total_correspondances_dans_bilan"] == 4
    assert artificielle["nombre_pistes"] == 3
    assert [x["identifiant"] for x in artificielle["pistes"]] == [
        "26-100", "26-101", "26-103"
    ]
    assert r["pistes"]["cybersecurite"]["nombre_pistes"] == 1
    p = artificielle["pistes"][0]
    assert p["identifiant"] == "26-100"
    assert p["archive_verifiee"].endswith(".jsonl.gz")
    assert p["besoin_scientifique_valide"] is False
    assert r["selection_non_representative"] is True
    assert r["aucune_validation_de_besoin"] is True
    sortie = tmp_path / "pistes.json"
    ecrire(r, sortie)
    octets = sortie.read_bytes()
    ecrire(constituer(index, preuve, bilan, 5, 2), sortie)
    assert sortie.read_bytes() == octets


def test_bilan_ancien_ou_regles_modifiees_refuses(tmp_path):
    index, preuve, bilan = exemple(tmp_path)
    contenu = json.loads(bilan.read_text(encoding="utf-8"))
    contenu["themes_lexicaux"]["robotique"]["regles"] = [r"\bprojet\b"]
    bilan.write_text(json.dumps(contenu), encoding="utf-8")
    with pytest.raises(BilanInvalide, match="Règles"):
        constituer(index, preuve, bilan)


def test_index_incoherent_ou_parametres_excessifs_refuses(tmp_path):
    index, preuve, bilan = exemple(tmp_path)
    with pytest.raises(BilanInvalide, match="Limites"):
        constituer(index, preuve, bilan, plafond=31)
    contenu = json.loads(preuve.read_text(encoding="utf-8"))
    contenu["sha256_index"] = "0" * 64
    preuve.write_text(json.dumps(contenu), encoding="utf-8")
    with pytest.raises(BilanInvalide, match="incohérents"):
        constituer(index, preuve, bilan)
