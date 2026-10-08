"""Essais de l'importation RNSR sur des structures fictives."""
import copy
import json

import pytest

from scripts.ingerer_structures_rnsr import (
    SOURCE_ID, elements, empreinte, identifier,
    normaliser, produire, telecharger,
)


def structure(code="200610662T", nom="Institut de recherche imaginaire"):
    return {
        "numero_national_de_structure": code,
        "libelle": nom,
        "sigle": "IRI",
        "type_de_structure": "Unité mixte",
        "site_web": "https://laboratoire.example.org",
        "fiche_rnsr": "https://exemple.gouv.fr/rnsr/fictif",
        "commune": "Lyon",
        "code_postal": "69000",
        "domaine_scientifique": ["Chimie", "Matériaux"],
        "code_domaine_scientifique": ["2"],
        "panel_erc": ["Physique de la matière"],
        "code_panel_erc": "PE3; PE5",
        "nom_du_responsable": ["PERSONNE FICTIVE"],
    }


def test_normalisation_identite_disciplines_et_aucune_capacite_deduite():
    brut = structure()
    entite = normaliser(brut, "2026-10-08T12:00:00+00:00")
    assert entite["id"] == "FRONTIERE-INST-RNSR-200610662T"
    assert entite["identifiants"] == {"rnsr": "200610662T"}
    assert entite["famille"] == "recherche_publique"
    assert entite["etat"] == "ACTIF"
    assert entite["missions"] == []
    assert entite["capacites"] == []
    assert [x["texte"] for x in entite["domaines_recherche"]] == [
        "Chimie", "Matériaux", "Physique de la matière",
    ]
    assert entite["codes_domaines_recherche"]["panel_erc"] == ["PE3", "PE5"]
    assert all(x["nature"] == "PUBLIEE" and x["source_id"] == SOURCE_ID for x in entite["domaines_recherche"])
    assert entite["provenance"][0]["empreinte"] == empreinte(brut)
    assert "PERSONNE FICTIVE" not in json.dumps(entite, ensure_ascii=False)
    assert entite["observe_le"] == "2026-10-08T12:00:00+00:00"


def test_valeurs_manquantes_demeurent_absentes():
    brut = structure()
    brut["domaine_scientifique"] = []
    brut["panel_erc"] = None
    brut["code_panel_erc"] = "PE1;SH3; PE1"
    entite = normaliser(brut, "2026-10-08")
    assert entite["domaines_recherche"] == []
    assert entite["codes_domaines_recherche"]["panel_erc"] == ["PE1", "SH3"]


def test_rejet_id_invalide_ou_nom_manquant():
    brut = structure()
    brut["numero_national_de_structure"] = "../fichier"
    with pytest.raises(ValueError, match="Identifiant"):
        normaliser(brut, "2026-10-08")
    brut = structure()
    brut["libelle"] = ""
    with pytest.raises(ValueError, match="dénomination"):
        normaliser(brut, "2026-10-08")


def test_telechargement_pagine_refuse_incoherences():
    a = structure("200610662T")
    b = structure("200710662T")
    c = structure("200810662T")
    reponses = {
        0: {"total_count": 3, "results": [a, b]},
        2: {"total_count": 3, "results": [c]},
    }
    assert len(telecharger(lambda offset, limite: reponses[offset])) == 3
    r = copy.deepcopy(reponses)
    r[2]["total_count"] = 4
    with pytest.raises(ValueError, match="changé"):
        telecharger(lambda offset, limite: r[offset])
    r = copy.deepcopy(reponses)
    r[2]["results"] = [copy.deepcopy(a)]
    with pytest.raises(ValueError, match="Doublon"):
        telecharger(lambda offset, limite: r[offset])
    r = copy.deepcopy(reponses)
    r[2]["results"] = []
    with pytest.raises(ValueError, match="Page"):
        telecharger(lambda offset, limite: r[offset])


def test_import_versionne_sans_reinitialiser_les_dates(tmp_path):
    a = structure("200610662T")
    b = structure("200710662T", "Laboratoire de biologie fictif")
    premiere = produire(
        [a, b], tmp_path, minimum=1,
        date_collecte="2026-10-08T12:00:00+00:00",
    )
    assert premiere["statut"] == "actualisé"
    assert premiere["nombre_structures"] == 2
    assert premiere["couverture"]["avec_domaines_nommes"] == 2
    fichiers = sorted((tmp_path / "entites" / "rnsr").glob("*.jsonl"))
    assert len(fichiers) == 8
    assert sum(len(f.read_text(encoding="utf-8").splitlines()) for f in fichiers) == 2
    initial = {f.name: f.read_bytes() for f in fichiers}
    identique = produire(
        [b, a], tmp_path, minimum=1,
        date_collecte="2026-10-09T12:00:00+00:00",
    )
    assert identique["statut"] == "inchangé"
    assert {f.name: f.read_bytes() for f in fichiers} == initial
    b2 = copy.deepcopy(b)
    b2["domaine_scientifique"] = ["Sciences du vivant"]
    mis_a_jour = produire(
        [a, b2], tmp_path, minimum=1,
        date_collecte="2026-10-10T12:00:00+00:00",
    )
    assert mis_a_jour["statut"] == "actualisé"
    lignes = [
        json.loads(texte)
        for f in fichiers
        for texte in f.read_text(encoding="utf-8").splitlines()
        if texte.strip()
    ]
    versions = {v["identifiants"]["rnsr"]: v for v in lignes}
    assert versions["200610662T"]["observe_le"] == "2026-10-08T12:00:00+00:00"
    assert versions["200710662T"]["observe_le"] == "2026-10-10T12:00:00+00:00"
    assert versions["200710662T"]["domaines_recherche"][0]["texte"] == "Sciences du vivant"
    assert all(v["capacites"] == [] for v in versions.values())


def test_refuse_doublon_et_baisse_massive_sans_corrompre_sortie(tmp_path):
    a = structure("200610662T")
    b = structure("200710662T")
    c = structure("200810662T")
    produire([a, b, c], tmp_path, minimum=1, date_collecte="2026-10-08")
    chemin = tmp_path / "instantanes" / "rnsr_manifest.json"
    original = chemin.read_bytes()
    with pytest.raises(ValueError, match="occurrences"):
        produire([a, a], tmp_path, minimum=1)
    with pytest.raises(ValueError, match="Baisse"):
        produire([a], tmp_path, minimum=1)
    assert chemin.read_bytes() == original


def test_empreinte_independante_de_l_ordre_des_lignes(tmp_path):
    a, b = structure("200610662T"), structure("200710662T")
    produire([a, b], tmp_path, minimum=1, date_collecte="2026-10-08")
    avant = json.loads((tmp_path / "instantanes/rnsr_manifest.json").read_text(encoding="utf-8"))
    produire([b, a], tmp_path, minimum=1, date_collecte="2026-10-09")
    apres = json.loads((tmp_path / "instantanes/rnsr_manifest.json").read_text(encoding="utf-8"))
    assert avant == apres
    assert elements("PE3;PE5;PE3") == ["PE3", "PE5"]
