"""Tests de déduplication documentaire et de reconstruction atomique AIFE/DGFiP."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from scripts.consolider_attributions_decp import (
    PAGE_DGFIP, IndexDECPInvalide, construire_index, rapports_dgfip,
)

RID_AIFE = "db50f1f1-9fe5-4f9e-93dd-d273617d4a26"
RID_XML1 = "118544f1-b022-43d4-b8e0-3856f66a8b1d"
RID_XML2 = "ec06007c-1e84-4314-bee8-716fe54675ec"


def marche(id_marche="M-01", siret="21750001630066", objet="Recherche fondamentale"):
    return {
        "acheteur_siret": siret, "id_marche": id_marche, "objet": objet,
        "code_cpv": "73100000-3", "nature": "Marché",
        "date_notification": "2026-10-11",
        "date_publication_declaree": "2026-10-12",
        "montant_euros_ht_declare": 45000,
        "offres_recues_declarees": None,
        "marche_innovant_declare": None,
        "preuve_de_premiere_contribution": False,
        "besoin_encore_ouvert_demontre": False,
    }


def aife(lignes=None):
    lignes = [marche()] if lignes is None else lignes
    return {
        "version": "decp-fichier-json-v1", "source_catalogue": "aife_api_decp",
        "page_catalogue": "https://www.data.gouv.fr/datasets/api-decp",
        "sha256_fichier_brut": "a" * 64, "ressource_id": RID_AIFE,
        "releve_le": "2026-10-13T04:00:00+00:00",
        "extraits_plafonnes": False,
        "releves": {"marches_uniques_valides": len(lignes)},
        "marches_extraits": lignes,
    }


def fichier_xml(rid, sha, lignes, tronque=False):
    return {
        "id": rid, "empreinte_sha256": sha, "extraits_plafonnes": tronque,
        "releves": {"marches_uniques_valides": len(lignes)},
        "marches_extraits": lignes,
    }


def dgfip(fichiers=None):
    return {
        "version": "lot-decp-dgfip-xml-v1",
        "source_catalogue": "dgfip_pes_marche",
        "page_catalogue": PAGE_DGFIP,
        "controle_le": "2026-10-13T05:00:00+00:00",
        "fichiers": [fichier_xml(RID_XML1, "b" * 64, [marche()])]
        if fichiers is None else fichiers,
    }


def test_index_inter_sources_et_doublons_exacts(tmp_path):
    base = tmp_path / "attributions.sqlite3"
    r = construire_index(
        base, aife=aife(), dgfip=dgfip(), horodatage="2026-10-13T06:00:00+00:00",
    )
    assert r["enregistrements_normalises_par_fichier"] == 2
    assert r["identites_distinctes_par_siret_et_id_marche"] == 1
    assert r["variantes_documentaires_distinctes"] == 1
    assert r["repetitions_de_variantes_deja_observees"] == 1
    assert r["identites_avec_plusieurs_variantes"] == 0
    assert r["fichiers_sources_distincts"] == 2
    assert r["attestations_documentaires"] == 2
    assert r["notices_detaillees_manquantes"] == 0
    assert r["correspondances_boamp_verifiees"] == 0
    assert base.exists()
    with sqlite3.connect(base) as cx:
        assert cx.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_plusieurs_variantes_ne_sont_pas_confondues_avec_avenant(tmp_path):
    autres = [
        fichier_xml(RID_XML1, "b" * 64, [marche(objet="Étude scientifique")]),
        fichier_xml(RID_XML2, "c" * 64, [marche(id_marche="M-02")]),
    ]
    r = construire_index(tmp_path / "index.sqlite3", aife=aife(),
                          dgfip=dgfip(autres))
    assert r["enregistrements_normalises_par_fichier"] == 3
    assert r["identites_distinctes_par_siret_et_id_marche"] == 2
    assert r["variantes_documentaires_distinctes"] == 3
    assert r["identites_avec_plusieurs_variantes"] == 1
    assert r["repetitions_de_variantes_deja_observees"] == 0


def test_deux_acheteurs_meme_numero_ne_sont_pas_fusionnes(tmp_path):
    xml = dgfip([fichier_xml(
        RID_XML1, "b"*64, [marche(siret="12345678901234")]
    )])
    r = construire_index(tmp_path / "index.sqlite3", aife=aife(), dgfip=xml)
    assert r["identites_distinctes_par_siret_et_id_marche"] == 2


def test_document_tronque_refuse_sans_remplacer_la_base(tmp_path):
    base = tmp_path / "index.sqlite3"
    construire_index(base, aife=aife(), dgfip=dgfip())
    avant = hashlib.sha256(base.read_bytes()).hexdigest()
    incomplet = dgfip([fichier_xml(RID_XML1, "b"*64, [marche()], tronque=True)])
    with pytest.raises(IndexDECPInvalide, match="incomplet"):
        construire_index(base, aife=aife(), dgfip=incomplet)
    assert hashlib.sha256(base.read_bytes()).hexdigest() == avant


def test_renseignements_non_valides_ou_provenances_ambiguës_refuses(tmp_path):
    base = tmp_path / "index.sqlite3"
    for changement in [
        {"page_catalogue": "https://exemple.invalid/dgfip"},
        {"source_catalogue": "autre"},
        {"version": "autre"},
    ]:
        xml = dgfip()
        xml.update(changement)
        with pytest.raises(IndexDECPInvalide):
            construire_index(base, aife=aife(), dgfip=xml)
        assert not base.exists()

    double = fichier_xml(RID_XML1, "b"*64, [marche()])
    with pytest.raises(IndexDECPInvalide, match="répétée"):
        rapports_dgfip(dgfip([double, deepcopy(double)]))


def test_importation_reelle_si_registres_complets(tmp_path):
    """Test d'intégration uniquement si la copie de PR possède tous les détails."""
    source_aife = Path("institutionnel/decp/sonde_aife_json.json")
    source_dgfip = Path("institutionnel/decp/lot_dgfip_xml.json")
    if not source_aife.is_file() or not source_dgfip.is_file():
        pytest.skip("Relevés publiés absents de l'environnement")
    a = json.loads(source_aife.read_text(encoding="utf-8"))
    d = json.loads(source_dgfip.read_text(encoding="utf-8"))
    if any(f.get("extraits_plafonnes") for f in d.get("fichiers", [])):
        pytest.skip("L'ingestion intégrale du lot XML n'est pas encore publiée")
    r = construire_index(tmp_path / "reel.sqlite3", aife=a, dgfip=d)
    assert r["fichiers_documentaires"] == len(d["fichiers"]) + 1
    assert r["identites_distinctes_par_siret_et_id_marche"] > 0
    assert r["enregistrements_normalises_par_fichier"] == sum(
        f["releves"]["marches_uniques_valides"] for f in d["fichiers"]
    ) + a["releves"]["marches_uniques_valides"]
