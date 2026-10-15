"""Essais hors réseau de la collecte DECP permanente AIFE / DGFiP."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json

import pytest

from app.collecteur_decp_continu import (
    _charger, cycle, etat_index, importer_archives,
)
from scripts.consolider_attributions_decp import PAGE_DGFIP
from scripts.indexer_attributions_decp_sqlite import rechercher

AIFE_ID = "db50f1f1-9fe5-4f9e-93dd-d273617d4a26"
XML_ID1 = "118544f1-b022-43d4-b8e0-3856f66a8b1d"
XML_ID2 = "ec06007c-1e84-4314-bee8-716fe54675ec"
CYCLE = "2026-10-14T18:00:00+00:00"


def marche(*, objet="Étude scientifique", id_marche="A-2026"):
    return {
        "acheteur_siret": "21750001630066", "id_marche": id_marche,
        "objet": objet, "code_cpv": "73100000-3",
        "date_notification": "2026-10-12",
        "date_publication_declaree": "2026-10-13",
        "montant_euros_ht_declare": 45000.00, "nature": "Marché",
        "offres_recues_declarees": 2, "marche_innovant_declare": None,
        "preuve_de_premiere_contribution": False,
        "besoin_encore_ouvert_demontre": False,
    }


def aife_report(marche_objet="Étude scientifique", revision="a"):
    return {
        "version": "decp-fichier-json-v1", "source_catalogue": "aife_api_decp",
        "page_catalogue": "https://www.data.gouv.fr/datasets/api-decp",
        "ressource_id": AIFE_ID,
        "sha256_fichier_brut": hashlib.sha256(revision.encode()).hexdigest(),
        "releve_le": CYCLE, "extraits_plafonnes": False,
        "releves": {"marches_uniques_valides": 1},
        "marches_extraits": [marche(objet=marche_objet)],
    }


def xml_file(identifiant=XML_ID1, sha="b" * 64, lines=None, tronque=False):
    lignes = lines if lines is not None else [marche()]
    return {
        "id": identifiant, "empreinte_sha256": sha, "extraits_plafonnes": tronque,
        "releves": {"marches_uniques_valides": len(lignes)},
        "marches_extraits": lignes,
    }


def dgfip_registry(fichiers=None):
    return {
        "version": "lot-decp-dgfip-xml-v1",
        "source_catalogue": "dgfip_pes_marche",
        "page_catalogue": PAGE_DGFIP,
        "controle_le": CYCLE,
        "fichiers": [xml_file()] if fichiers is None else fichiers,
    }


def config_etat():
    return {
        "version": "decp-metadonnees-v1",
        "catalogues": [
            {"source_id": "aife_api_decp",
             "ressources_recentes": [{"id": AIFE_ID,
               "format": "json", "taille_octets_declaree": 200,
               "modifie_le": CYCLE}]},
            {"source_id": "dgfip_pes_marche",
             "ressources_recentes": [{"id": XML_ID1,
               "format": "xml", "taille_octets_declaree": 200,
               "modifie_le": CYCLE}]},
        ],
    }


def ecrire(path, objet):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(objet, ensure_ascii=False), encoding="utf-8")


def test_amorcage_reutilise_le_corpus_existant_et_l_index_est_idempotent(tmp_path):
    archives, dossier = tmp_path / "archives", tmp_path / "durable"
    base = tmp_path / "index.sqlite3"
    ecrire(archives / "etat_ressources.json", config_etat())
    ecrire(archives / "sonde_aife_json.json", aife_report())
    ecrire(archives / "lot_dgfip_xml.json", dgfip_registry())
    avant = importer_archives(base, archives, dossier)
    assert avant["releves_documentaires_importes"] == 2
    assert avant["marches_distincts"] == 1
    assert avant["fichiers"] == 2
    assert avant["versions"] == 1
    assert avant["attestations"] == 2
    apres = importer_archives(base, archives, dossier)
    assert apres["releves_documentaires_importes"] == 0
    assert apres["fichiers"] == 2
    assert len(rechercher(base, "scientifique")) == 1


def test_cycle_sans_nouveaux_fichiers_ne_retelecharge_pas_aife(tmp_path):
    archives, dossier = tmp_path / "archives", tmp_path / "data"
    base = tmp_path / "index.db"
    ecrire(archives / "etat_ressources.json", config_etat())
    ecrire(archives / "sonde_aife_json.json", aife_report())
    ecrire(archives / "lot_dgfip_xml.json", dgfip_registry())
    importer_archives(base, archives, dossier)
    def catalogues(_cfg, _ancien, *, recuperer):
        return {**config_etat(), "sources_reussies": 2, "sources_echouees": []}
    def telecharger(source):
        return {"resources": []}
    def selection(_etat, _fiche):
        return {"id": AIFE_ID, "taille_octets_declaree": 200,
                "modifie_le": CYCLE}
    def aife(_etat, _fiche):
        return aife_report()
    def dgfip(_etat, _fiche, precedent):
        return precedent
    premier = cycle(base, dossier, config_etat(), actualiser=catalogues,
                   telecharger=telecharger, aife=aife, dgfip=dgfip,
                   selectionner_aife=selection)
    assert premier["ressources_nouvelles"] == 0
    assert premier["fichiers"] == 2
    def interdit(*args, **kwargs):
        raise AssertionError("Fichier AIFE déjà traité : aucun téléchargement.")
    second = cycle(base, dossier, config_etat(), actualiser=catalogues,
                   telecharger=telecharger, aife=interdit, dgfip=dgfip,
                   selectionner_aife=selection)
    assert second["ressources_nouvelles"] == 0
    assert second["fichiers"] == 2
    assert not second["erreurs_sources"]


def test_nouveau_fichier_dgfip_ajoute_une_version_avec_provenance(tmp_path):
    base, dossier = tmp_path / "marches.db", tmp_path / "historique"
    old = dgfip_registry()
    ecrire(dossier / "lot_dgfip_xml.json", old)
    nouveau = dgfip_registry([
        xml_file(),
        xml_file(identifiant=XML_ID2, sha="c"*64,
                 lines=[marche(objet="Analyse de matériaux")]),
    ])
    def actualiser(_cfg, _ancien, *, recuperer):
        return {**config_etat(), "sources_reussies": 2, "sources_echouees": []}
    def fiche(_source):
        return {"resources": []}
    def aife_selection(*_args):
        raise ValueError("AIFE momentanément indisponible")
    result = cycle(base, dossier, config_etat(), actualiser=actualiser,
                   telecharger=fiche, selectionner_aife=aife_selection,
                   dgfip=lambda _etat, _fiche, _ancien: nouveau)
    assert result["ressources_nouvelles"] == 1
    assert result["marches_distincts"] == 1
    assert result["versions"] == 2  # Reprise de la fiche ancienne avant nouvelle version.
    assert result["erreurs_sources"][0]["source"] == "AIFE"
    assert _charger(dossier / "lot_dgfip_xml.json")["fichiers"] == nouveau["fichiers"]
    assert len(rechercher(base, "matériaux")) == 1


def test_dgfip_incomplet_preserve_un_ancien_curseur(tmp_path):
    base, dossier = tmp_path / "marches.db", tmp_path / "historique"
    ancien = dgfip_registry()
    ecrire(dossier / "lot_dgfip_xml.json", ancien)
    def catalogues(_config, _etat, *, recuperer):
        return {**config_etat(), "sources_reussies": 2, "sources_echouees": []}
    def telecharger(_source):
        return {}
    incomplet = dgfip_registry([xml_file(tronque=True)])
    result = cycle(base, dossier, config_etat(),
                   actualiser=catalogues, telecharger=telecharger,
                   selectionner_aife=lambda *_: (_ for _ in ()).throw(
                       ValueError("AIFE indisponible")),
                   dgfip=lambda *_: incomplet)
    assert {x["source"] for x in result["erreurs_sources"]} == {"AIFE", "DGFiP"}
    assert _charger(dossier / "lot_dgfip_xml.json") == ancien
    assert etat_index(base)["fichiers"] == 1


def test_catalogue_indisponible_preserve_les_fichiers(tmp_path):
    base, dossier = tmp_path / "marches.db", tmp_path / "historique"
    ancien = config_etat()
    ecrire(dossier / "etat_ressources.json", ancien)
    def panne(*args, **kwargs):
        raise ValueError("Aucun catalogue accessible")
    with pytest.raises(ValueError, match="catalogue"):
        cycle(base, dossier, config_etat(), actualiser=panne)
    assert _charger(dossier / "etat_ressources.json") == ancien
    assert etat_index(base)["marches_distincts"] == 0


def test_interdiction_d_inventer_un_besoin_ouvert(tmp_path):
    base, archives, dossier = (
        tmp_path / "marches.db", tmp_path / "archives", tmp_path / "suivi"
    )
    erreur = aife_report()
    erreur["marches_extraits"][0]["besoin_encore_ouvert_demontre"] = True
    ecrire(archives / "sonde_aife_json.json", erreur)
    with pytest.raises(ValueError, match="besoin ouvert"):
        importer_archives(base, archives, dossier)
    assert etat_index(base)["fichiers"] == 0
