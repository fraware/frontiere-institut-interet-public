"""Tests de rapprochement documentaire, sans inférence de capacité mobilisable."""
from contextlib import closing
import hashlib
import json
import sqlite3

import pytest

from scripts.analyser_historique_boamp import produire, ecrire as ecrire_bilan, BilanInvalide
from scripts.rechercher_historique_boamp import VERSION, preparer_base
from scripts.rechercher_capacites_institutionnelles import construire_index
from scripts.croiser_pistes_capacites import (
    croiser, ecrire, expressions_avis, contient_expression,
)


def organisme(code, nom, *, mission=None, domaine=None, etat="ACTIF",
              source=True, famille="organisation_administrative_etat"):
    return {
        "id": "FRONTIERE-INST-" + code,
        "nom_officiel": nom,
        "etat": etat,
        "famille": famille,
        "type_institutionnel": "Service de recherche fictif",
        "observe_le": "2026-10-11",
        "provenance": [{
            "source_id": "source-publique-fictive",
            "url": "https://example.org/document-source",
            "collecte_le": "2026-10-11",
        }],
        "missions": [{
            "texte": mission, "nature": "PUBLIEE",
            **({"source_id": "source-publique-fictive"} if source else {}),
        }] if mission else [],
        "domaines_recherche": [{
            "texte": domaine, "nature": "PUBLIEE",
            "source_id": "classement-public-fictif",
        }] if domaine else [],
    }


def donnees(tmp_path):
    index = tmp_path / "avis.sqlite3"
    preuve = tmp_path / "preuve-index.json"
    bilan = tmp_path / "bilan.json"
    entites = tmp_path / "entites"
    (entites / "roae").mkdir(parents=True)
    notices = [
        organisme("A", "Service de données", mission="Expertise en intelligence artificielle"),
        organisme("B", "Laboratoire des modèles", domaine="Intelligence artificielle",
                  famille="recherche_publique"),
        organisme("C", "Institut intelligence artificielle", mission="Accueil des stagiaires"),
        organisme("D", "Service de recherche",
                  mission="Intelligence stratégique artificielle"),
        organisme("E", "Unité non sourcée",
                  mission="Intelligence artificielle", source=False),
        organisme("F", "Service inactif", mission="Intelligence artificielle", etat="SUPPRIME"),
        organisme("G", "Unité des systèmes informatiques", mission="Sécurité informatique"),
    ]
    chemin_source = entites / "roae" / "donnees.jsonl"
    chemin_source.write_text(
        "".join(json.dumps(n, ensure_ascii=False) + "\n" for n in notices),
        encoding="utf-8",
    )
    institution = tmp_path / "institutions.sqlite3"
    construire_index(entites, institution)
    with closing(sqlite3.connect(index)) as db:
        preparer_base(db)
        db.execute("INSERT INTO informations VALUES('version', ?)", (VERSION,))
        db.execute(
            "INSERT INTO provenance VALUES(?,?,?,?,?,?,?,?,?)",
            ("2026-10-01", "archive-originale.gz", "a" * 64, 4,
             "archive-originale.gz", "a" * 64, 4, "2026-10-02T00:00:00+00:00", 0),
        )
        items = [
            ("a-1", "Étude intelligence artificielle pour l'administration", "Acheteur 1"),
            ("a-2", "Prestations de cybersécurité", "Acheteur 2"),
            ("a-3", "Maintenance robotique et robot de laboratoire", "Acheteur 3"),
            ("a-4", "Fourniture de bureaux", "Acheteur 4"),
        ]
        db.executemany(
            "INSERT INTO recherche VALUES(?,?,?,?,?,?,?,?,?)",
            [
                ("2026-10-01", code, objet, acheteur,
                 "https://www.boamp.fr/" + code, "SERVICES", "INITIAL",
                 "historique_boamp/2026/10/2026-10-01.jsonl.gz",
                 "2026-10-02T00:00:00+00:00")
                for code, objet, acheteur in items
            ],
        )
        db.commit()
    preuve.write_text(json.dumps({
        "version": "publication-index-boamp-v1", "revision_depot": "f" * 40,
        "sha256_index": hashlib.sha256(index.read_bytes()).hexdigest(),
        "jours_indexes": 1, "avis_indexes": 4,
    }), encoding="utf-8")
    ecrire_bilan(produire(index, preuve), bilan)
    return index, preuve, bilan, institution, entites, chemin_source


def test_expressions_contigues_reelles_et_diverses():
    assert contient_expression("Une politique d'intelligence artificielle.",
                               "intelligence artificielle")
    assert not contient_expression("Intelligence stratégique artificielle",
                                   "intelligence artificielle")
    assert contient_expression("Moyens de cybersécurité", "cybersecurite")
    assert not contient_expression("Robotique", "robots")
    assert expressions_avis({
        "objet": "Robots et robotique en laboratoire",
        "regles_correspondantes": [r"\brobotique\b", r"\brobots?\b"],
    }, "robotique") == ["robotique", "robots"]
    with pytest.raises(BilanInvalide, match="incohérentes"):
        expressions_avis({
            "objet": "Étude scientifique", "regles_correspondantes": [r"\b.*\b"],
        }, "robotique")


def test_croisement_distingue_mission_domaine_nom_et_exclusions(tmp_path):
    index, preuve, bilan, institution, entites, _ = donnees(tmp_path)
    r = croiser(index, preuve, bilan, institution, entites, limite=3)
    assert r["nombre_pistes"] == 3
    assert r["nombre_avis_dans_corpus"] == 4
    assert r["nombre_organismes_dans_index"] == 7
    assert r["pistes_avec_mission_ou_capacite_documentaire"] == 1
    assert r["aucune_preuve_de_disponibilite"] is True
    a = next(x for x in r["dossiers"]
             if x["theme"] == "intelligence_artificielle")
    assert a["identifiant_avis"] == "a-1"
    assert a["expressions_extraites"] == ["intelligence artificielle"]
    assert [z["identifiant"] for z in a["groupes"]["mission_publiee"]] == [
        "FRONTIERE-INST-A",
    ]
    assert [z["identifiant"] for z in a["groupes"]["domaine_scientifique_publie"]] == [
        "FRONTIERE-INST-B",
    ]
    assert [z["identifiant"] for z in a["groupes"]["nom_seul"]] == [
        "FRONTIERE-INST-C",
    ]
    assert "FRONTIERE-INST-D" not in str(a)
    assert "FRONTIERE-INST-E" not in str(a)
    assert "FRONTIERE-INST-F" not in str(a)
    m = a["groupes"]["mission_publiee"][0]
    assert m["mobilisabilite"] == "NON_ETABLIE"
    assert m["disponibilite"] == "INCONNUE"
    assert m["passages_justificatifs"][0]["source_id"] == "source-publique-fictive"
    autre = next(x for x in r["dossiers"] if x["theme"] == "cybersecurite")
    assert all(not v for v in autre["groupes"].values())
    assert autre["besoin_scientifique_valide"] is False
    assert autre["lien_contractuel_avec_acheteur_etabli"] is False
    assert r["selection_non_representative"] is True


def test_croisement_reproductible_et_refuse_changement_sources(tmp_path):
    index, preuve, bilan, institution, entites, chemin = donnees(tmp_path)
    rapport = croiser(index, preuve, bilan, institution, entites)
    sortie = tmp_path / "rapport.json"
    ecrire(rapport, sortie)
    avant = sortie.read_bytes()
    ecrire(croiser(index, preuve, bilan, institution, entites), sortie)
    assert sortie.read_bytes() == avant
    chemin.write_text(chemin.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(BilanInvalide, match="modifié"):
        croiser(index, preuve, bilan, institution, entites)
    assert sortie.read_bytes() == avant


def test_croisement_refuse_bilan_different_de_l_index(tmp_path):
    index, preuve, bilan, institution, entites, _ = donnees(tmp_path)
    document = json.loads(bilan.read_text(encoding="utf-8"))
    document["nombre_avis"] = 500
    bilan.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(BilanInvalide, match="reproductible"):
        croiser(index, preuve, bilan, institution, entites)


def test_limite_et_orphelins_rejetes(tmp_path):
    index, preuve, bilan, institution, entites, _ = donnees(tmp_path)
    with pytest.raises(BilanInvalide, match="maximal"):
        croiser(index, preuve, bilan, institution, entites, limite=0)
    with pytest.raises(ValueError, match="Index absent"):
        croiser(index, preuve, bilan, tmp_path / "sans-index.sqlite3", entites)


def test_recherche_exacte_surclasse_les_decoys_or_et_mesure_les_plafonds(tmp_path):
    from scripts.croiser_pistes_capacites import chercher_expressions_exactes
    from scripts.rechercher_capacites_institutionnelles import ouvrir_index
    reper = tmp_path / "enregistrements"
    (reper / "roae").mkdir(parents=True)
    # 80 faux candidats portant un seul des deux termes ; avec le tri initial
    # borné sur une expression OR, ils masquaient l'organisme pertinent.
    organes = [
        organisme(f"DECOY-{i:04d}", f"Service {i}",
                  mission="Programme d'intelligence stratégique")
        for i in range(80)
    ]
    organes.append(
        organisme("Z-EXACT", "Service scientifique",
                  mission="Évaluation des modèles d'intelligence artificielle")
    )
    chemin = reper / "roae" / "institutions.jsonl"
    chemin.write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in organes),
        encoding="utf-8",
    )
    idx = tmp_path / "org.sqlite3"
    construire_index(reper, idx)
    with ouvrir_index(idx) as db:
        vrai = chercher_expressions_exactes(
            db, "intelligence artificielle", plafond=25,
        )
        assert vrai["candidats_examines"] == 1
        assert vrai["candidats"][0]["identifiant"] == "FRONTIERE-INST-Z-EXACT"
        assert vrai["champs_tronques"] == []
        # Requête simple artificiellement bornée : l'outil annonce que le
        # nombre d'organismes retenus n'est pas exhaustif.
        limite = chercher_expressions_exactes(db, "intelligence", plafond=7)
        assert limite["candidats_examines"] == 7
        assert limite["champs_tronques"] == ["mission_index"]
        assert limite["effectifs_par_champ_bornes"]["mission_index"] == 7
        with pytest.raises(BilanInvalide, match="Plafond"):
            chercher_expressions_exactes(db, "intelligence", plafond=0)


def test_recherche_exacte_ne_proclame_pas_l_absence_en_cas_de_troncature(tmp_path):
    from scripts.croiser_pistes_capacites import chercher_expressions_exactes
    from scripts.rechercher_capacites_institutionnelles import ouvrir_index
    repertoire = tmp_path / "entites"
    (repertoire / "roae").mkdir(parents=True)
    membres = [
        organisme(f"N-{i:03d}", f"Unité {i}", domaine="Robotique scientifique")
        for i in range(10)
    ]
    (repertoire / "roae" / "n.jsonl").write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in membres),
        encoding="utf-8",
    )
    idx = tmp_path / "in.sqlite3"
    construire_index(repertoire, idx)
    with ouvrir_index(idx) as db:
        result = chercher_expressions_exactes(db, "robotique", plafond=3)
    assert result["champs_tronques"] == ["domaine_index"]
    assert result["effectifs_par_champ_bornes"]["domaine_index"] == 3
    assert result["candidats_examines"] == 3
