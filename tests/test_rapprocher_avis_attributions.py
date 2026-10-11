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


def test_lots_et_identifiants_distincts(tmp_path):
    index, preuve, source, _ = exemple(tmp_path)
    r = rapprocher(index, preuve, source)
    assert r["lignes_beauamp_examinees"] == 4
    assert r["fichiers_beauamp_verifies"] == 1
    assert r["liaisons_sur_lignes_par_type"] == {
        "id_boamp_attribution": 1, "id_boamp_contrat": 2,
    }
    assert r["identifiants_boamp_distincts_apparies"] == 2
    assert r["ecarts_publication_contrat_attribution_positifs_observes"] == 2
    assert r["jours_ecart_publication_positifs"] == {
        "minimum": 5, "mediane": 5.0, "maximum": 5,
    }
    assert r["attribution_officielle_verifiee"] is False
    assert r["dates_publication_par_contrat_distinct_non_ambigues"] == 1
    assert r["contrats_avec_dates_publication_divergentes"] == 0
    assert r["jours_ecart_contrats_distincts"]["mediane"] == 5
    assert r["lignes_jour_secondaire_hors_intervalle_boamp"] == 4
    assert r["exemples_repartis_par_jour_et_type"]


def test_manifest_corrompu_ne_remplace_pas_la_sortie(tmp_path):
    index, preuve, source, fichier = exemple(tmp_path)
    sortie = tmp_path / "rapport.json"
    ecrire(rapprocher(index, preuve, source), sortie)
    original = sortie.read_bytes()
    fichier.write_bytes(fichier.read_bytes() + b"changement")
    with pytest.raises(BilanInvalide, match="Empreinte"):
        rapprocher(index, preuve, source)
    assert sortie.read_bytes() == original


def test_dates_divergentes_sur_un_meme_contrat_sont_exclues(tmp_path):
    index, preuve, source, fichier = exemple(tmp_path)
    with fichier.open("r", encoding="utf-8-sig", newline="") as handle:
        lecteur = csv.DictReader(handle, delimiter=";")
        colonnes = lecteur.fieldnames
        lignes = list(lecteur)
    lignes[1]["date_avis_attribution"] = "2026-09-07"
    with fichier.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=colonnes, delimiter=";")
        writer.writeheader()
        writer.writerows(lignes)
    chemin = source / "manifest.json"
    manifeste = json.loads(chemin.read_text(encoding="utf-8"))
    manifeste["fichiers"][0]["octets_archives"] = fichier.stat().st_size
    manifeste["fichiers"][0]["sha256"] = hashlib.sha256(fichier.read_bytes()).hexdigest()
    chemin.write_text(json.dumps(manifeste), encoding="utf-8")
    rapport = rapprocher(index, preuve, source)
    assert rapport["contrats_avec_dates_publication_divergentes"] == 1
    assert rapport["dates_publication_par_contrat_distinct_non_ambigues"] == 0
    assert rapport["jours_ecart_contrats_distincts"]["mediane"] is None
    assert rapport["ecarts_publication_contrat_attribution_positifs_observes"] == 2
