"""La découverte n'invente aucune ingestion de données et préserve les acquis."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from scripts.decouvrir_sources_publiques import (
    ErreurCollecte, executer, indexer_existants, inserer, normaliser_fiche,
    rapprocher, url_catalogue, verifier_config,
)

RACINE = Path(__file__).resolve().parents[1]


def config():
    return {
        "source": "https://www.data.gouv.fr/api/1/datasets/",
        "recherches": ["recherche publique", "marchés publics"],
        "taille_page": 3,
        "nombre_pages_par_recherche": 2,
        "recherches_transversales": [{"q": None, "sort": "-last_update", "page_size": 2, "pages": 1}],
        "limite_fiches_enregistrees": 100,
        "secondes_entre_appels": 0,
    }


def fiche(uid="ab1234", titre="Données scientifiques", licence="lov2"):
    return {
        "id": uid,
        "title": titre,
        "private": False,
        "license": licence,
        "page": f"https://www.data.gouv.fr/datasets/{uid}/",
        "organization": {"name": "Institution publique"},
        "last_update": "2026-10-08T00:00:00+00:00",
        "resources": [{
            "id": "12c5dc1a-7e93-42c0-b344-ade34907b622",
            "title": "Export courant",
            "url": "https://static.data.gouv.fr/resources/jeu.csv",
            "format": "csv",
        }],
    }


def test_lecture_catalogue_ne_copie_jamais_de_fichiers():
    notice = normaliser_fiche(fiche())
    assert notice["reutilisation_potentielle"] is True
    assert notice["contenu_original_copie"] is False
    assert notice["examen_licence_et_vie_privee_a_faire"] is True
    assert notice["ressources"][0]["url"].startswith("https://")


def test_licence_inconnue_et_dossier_prive_non_promus():
    assert normaliser_fiche(fiche(licence="notspecified"))["reutilisation_potentielle"] is False
    secret = fiche()
    secret["private"] = True
    assert normaliser_fiche(secret) is None


def test_url_dangereuse_pas_enregistree():
    import urllib.parse
    x = fiche()
    x["resources"][0]["url"] = "file:///etc/passwd"
    assert normaliser_fiche(x)["ressources"][0]["url"] is None
    x["resources"][0]["url"] = "http://user:pass@localhost/private"
    assert normaliser_fiche(x)["ressources"][0]["url"] is None


def test_url_catalogue_domaine_et_pagination_fixes():
    u = url_catalogue("recherche science", 2, 50)
    x = urlparse(u)
    assert x.hostname == "www.data.gouv.fr"
    assert parse_qs(x.query) == {
        "q": ["recherche science"], "page": ["2"], "page_size": ["50"]
    }
    assert "sort=-last_update" in url_catalogue(None, 1, 10, "-last_update")
    with pytest.raises(ErreurCollecte):
        url_catalogue("", 1, 5)
    with pytest.raises(ErreurCollecte):
        url_catalogue("test", 0, 5)
    with pytest.raises(ErreurCollecte):
        url_catalogue("test", 1, 101)


def test_ancien_registre_evite_les_doublons():
    registre = {"sources": [{
        "metadata_url": "https://www.data.gouv.fr/api/1/datasets/jeu-existant/",
        "page_url": "https://www.data.gouv.fr/datasets/jeu-existant",
    }]}
    public = fiche(uid="67fff234", titre="Existant")
    public["page"] = "https://www.data.gouv.fr/datasets/jeu-existant/"
    assert rapprocher(normaliser_fiche(public), indexer_existants(registre))


def test_collecte_conserve_les_anciens_et_signale_les_echecs():
    appels = []

    def donnees(url):
        appels.append(url)
        query = parse_qs(urlparse(url).query)
        if query.get("q") == ["marchés publics"] and query["page"] == ["2"]:
            raise OSError("Échec réseau fictif")
        return {"data": [fiche("ab1234")]}

    initiaux = {"candidats": [normaliser_fiche(fiche("ancien99", "Source historique"))]}
    resultat, rapport = executer(
        config(), initiaux, {"sources": []},
        telecharger=donnees, pause=lambda x: None,
        instant="2026-10-09T16:00:00+00:00",
    )
    assert len(appels) == 5
    assert rapport["pages_reussies"] == 4
    assert rapport["pages_echouees"] == 1
    assert rapport["nouveaux_identifiants"] == 1
    assert rapport["collecte_complete"] is False
    assert rapport["couverture_exhaustive_du_web"] is False
    assert rapport["fichiers_sources_originaux_telecharges"] == 0
    assert {x["id"] for x in resultat["candidats"]} == {"ancien99", "ab1234"}
    assert len(next(x for x in resultat["candidats"] if x["id"] == "ab1234")["recherches"]) == 3


def test_config_rejette_provenance_hors_catalogue():
    c = config()
    c["source"] = "https://exemple.invalid/api/"
    with pytest.raises(ErreurCollecte):
        verifier_config(c)


def test_recherches_reelles_du_depot_valides():
    source = json.loads(
        (RACINE / "institutionnel/decouverte/recherches_v1.json").read_text(encoding="utf-8")
    )
    verifier_config(source)
    assert len(source["recherches"]) >= 30
    assert len(set(source["recherches"])) == len(source["recherches"])
