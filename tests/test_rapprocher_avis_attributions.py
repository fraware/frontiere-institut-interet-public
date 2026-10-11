"""Essais hors connexion des liens documentaires BOAMP et BeauAMP."""
from contextlib import closing
import csv
import hashlib
import json
import sqlite3
import pytest

from scripts.rechercher_historique_boamp import VERSION, preparer_base
from scripts.rapprocher_avis_attributions import rapprocher, ecrire, BilanInvalide


def exemple(tmp_path):
    index, preuve = tmp_path / "index.sqlite3", tmp_path / "preuve.json"
    source = tmp_path / "beauamp"
    (source / "quotidiens").mkdir(parents=True)
    with closing(sqlite3.connect(index)) as con:
        preparer_base(con)
        con.execute("INSERT INTO informations VALUES('version', ?)", (VERSION,))
        con.execute(
            "INSERT INTO provenance VALUES (?,?,?,?,?,?,?,?,?)",
            ("2026-09-01", "a.gz", "a"*64, 2, "a.gz", "a"*64,
             2, "2026-09-02T00:00:00+00:00", 0),
        )
        for nom, objet in (("26-100", "Étude géomatique"),
                           ("26-101", "Calcul intensif")):
            con.execute(
                "INSERT INTO recherche VALUES (?,?,?,?,?,?,?,?,?)",
                ("2026-09-01", nom, objet, "Acheteur fictif",
                 "https://www.boamp.fr/" + nom, "SERVICES", "INITIAL",
                 "a.gz", "2026-09-02T00:00:00+00:00"),
            )
        con.commit()
    preuve.write_text(json.dumps({
        "version": "publication-index-boamp-v1", "revision_depot": "e"*40,
        "sha256_index": hashlib.sha256(index.read_bytes()).hexdigest(),
        "jours_indexes": 1, "avis_indexes": 2,
    }), encoding="utf-8")
    rows = [
        {"id_boamp_contrat": "26-100", "id_boamp_attribution": "26-900",
         "date_avis_attribution": "2026-09-06", "id_lot": "lot-1"},
        {"id_boamp_contrat": "26-100", "id_boamp_attribution": "26-900",
         "date_avis_attribution": "2026-09-06", "id_lot": "lot-2"},
        {"id_boamp_contrat": "", "id_boamp_attribution": "26-101",
         "date_avis_attribution": "2026-09-06", "id_lot": "lot-3"},
        {"id_boamp_contrat": "26-999", "id_boamp_attribution": "",
         "date_avis_attribution": "2026-09-06", "id_lot": "lot-4"},
    ]
    fichier = source / "quotidiens" / "2026-09-06.csv"
    champs = ["id_boamp_attribution", "id_boamp_contrat",
              "date_avis_attribution", "date_avis_marche", "objet", "id_lot"]
    with fichier.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=champs, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    manifeste = {
        "version": "beauamp-quotidiens-v1",
        "nombre_fichiers": 1, "licence": "cc-by-sa",
        "producteur": "Producteur fictif",
        "source": "https://example.org/beauamp",
        "fichiers": [{
            "jour": "2026-09-06", "chemin": "quotidiens/2026-09-06.csv",
            "octets_archives": fichier.stat().st_size,
            "sha256": hashlib.sha256(fichier.read_bytes()).hexdigest(),
        }],
    }
    (source / "manifest.json").write_text(json.dumps(manifeste), encoding="utf-8")
    return index, preuve, source, fichier


