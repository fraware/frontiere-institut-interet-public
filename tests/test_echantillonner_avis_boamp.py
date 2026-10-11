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
    constituer, ecrire, mois_couverts, etat_strate, TEMOIN,
)


def jeu(tmp_path, categorie="SERVICES"):
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
                     "https://www.boamp.fr/" + code, categorie,
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
             "https://www.boamp.fr/26-999", categorie,
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
    assert e["nombre_categories_marche_renseignees"] == 63
    assert e["stratification_categorie_marche_effective"] is False
    assert e["stratification_effective"] == ["mois_civil_complet", "etat_documentaire", "domaine_lexical"]
    assert e["nombre_strates"] == 3
    assert e["nombre_tirages"] == 7
    assert e["nombre_avis_distincts"] in (6, 7)
    assert e["temoin_ne_signifie_pas_absence_de_besoin"]
    s = {(r["mois"], r["etat_documentaire"], r["domaine"]): r for r in e["strates"]}
    ai = s[("2026-01", "INITIAL", "intelligence_artificielle")]
    assert ai["population_documentaire"] == 31
    assert ai["nombre_tire"] == 3
    assert ai["fraction_tirage"] == {"numerateur": 3, "denominateur": 31}
    assert len(s[("2026-01", "INITIAL", TEMOIN)]["avis"]) == 3
    assert s[("2026-01", "INITIAL", "robotique")]["nombre_tire"] == 1
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
    assert etat_strate("RECTIFICATIF") == "RECTIFICATIF"
    assert etat_strate("initial") == "INITIAL"
    assert etat_strate(None) == "NON_RENSEIGNE"
    with pytest.raises(BilanInvalide):
        mois_couverts(["2026-02-01", "2026-02-01"])
    with pytest.raises(BilanInvalide):
        mois_couverts(["2026-02-31"])


def test_categories_entierement_absentes_ne_creent_pas_de_fausses_strates(tmp_path):
    index, preuve, bilan = jeu(tmp_path, categorie=None)
    r = constituer(index, preuve, bilan, quota=2)
    assert r["nombre_categories_marche_renseignees"] == 0
    assert r["nombre_categories_marche_manquantes"] == 63
    assert r["stratification_categorie_marche_effective"] is False
    assert r["nombre_etats_documentaires_absents"] == 0
    assert {s["etat_documentaire"] for s in r["strates"]} == {"INITIAL"}


def test_contre_verification_integre_et_replications(tmp_path):
    from scripts.auditer_echantillon_boamp import auditer
    index, preuve, bilan = jeu(tmp_path)
    rapport = constituer(index, preuve, bilan, quota=3)
    selection = tmp_path / "tirages.json"
    ecrire(rapport, selection)
    resultat = auditer(index, preuve, selection)
    assert resultat["conformite_du_tirage"] is True
    assert resultat["nombre_avis_verifies"] == 63
    assert resultat["nombre_journees_verifiees"] == 32
    assert resultat["mois_civils_complets"] == 1
    assert resultat["avis_exclus_mois_incomplets"] == 1
    assert resultat["strates_integralement_rejouees"] == 3
    assert resultat["tirages_integralement_rejoues"] == 7
    assert resultat["categories_de_marche_presentes"] == 63
    assert len(resultat["sensibilite_a_deux_semences"]) == 2
    assert all(0 <= x["fraction_de_tirages_communs"] <= 1
               for x in resultat["sensibilite_a_deux_semences"])


@pytest.mark.parametrize("alteration", ["rang", "population", "archive", "stratification"])
def test_contre_verification_refuse_rapports_alteres(tmp_path, alteration):
    from scripts.auditer_echantillon_boamp import auditer, ControleInvalide
    index, preuve, bilan = jeu(tmp_path)
    selection = tmp_path / "tirages.json"
    ecrire(constituer(index, preuve, bilan, quota=3), selection)
    contenu = json.loads(selection.read_text(encoding="utf-8"))
    if alteration == "rang":
        contenu["strates"][0]["avis"][0]["rang_sha256"] = "f" * 64
    elif alteration == "population":
        contenu["strates"][0]["population_documentaire"] += 1
    elif alteration == "archive":
        contenu["strates"][0]["avis"][0]["archive_source"] = "archive_frauduleuse.gz"
    elif alteration == "stratification":
        contenu["stratification_categorie_marche_effective"] = True
    selection.write_text(json.dumps(contenu), encoding="utf-8")
    with pytest.raises(ControleInvalide):
        auditer(index, preuve, selection)


def test_contre_verification_source_changee_refusee(tmp_path):
    from scripts.auditer_echantillon_boamp import auditer, ControleInvalide
    index, preuve, bilan = jeu(tmp_path)
    selection = tmp_path / "tirages.json"
    ecrire(constituer(index, preuve, bilan), selection)
    with closing(sqlite3.connect(index)) as con:
        con.execute("INSERT INTO informations VALUES ('modification', '1')")
        con.commit()
    with pytest.raises(ControleInvalide, match="Provenance"):
        auditer(index, preuve, selection)
