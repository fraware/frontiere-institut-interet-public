"""Essais locaux, hors réseau, de l'ingestion nationale DECP consolidée."""
from __future__ import annotations

from io import StringIO
import hashlib
import json
from pathlib import Path

import pytest

from app.collecteur_decp_consolides import (
    CollecteConsolideeInvalide, _sha256, cycle, etat, importer, selectionner,
)
from scripts.indexer_attributions_decp_sqlite import importer as importer_releve
from scripts.indexer_attributions_decp_sqlite import rechercher
from scripts.ingerer_fichier_decp_json import DocumentDECPInvalide, iterer_documents


RID_A = "dd50f1f1-9fe5-4f9e-93dd-d273617d4a26"
RID_B = "ee50f1f1-9fe5-4f9e-93dd-d273617d4a26"


def marche(numero="M-1", objet="Étude scientifique", acheteur="21750001630066"):
    return {
        "id": numero, "acheteur": {"id": acheteur}, "objet": objet,
        "codeCPV": "73100000-3", "nature": "Marché",
        "dateNotification": "2026-10-10",
        "datePublicationDonnees": "2026-10-14",
        "montant": 150000.0, "_type": "Marché",
    }


def fichier(tmp_path, contenu, nom="decp-2026-10.json"):
    chemin = tmp_path / nom
    chemin.write_text(json.dumps(contenu, ensure_ascii=False), encoding="utf-8")
    return chemin


def selection(chemin, rid=RID_A, titre="decp-2026-10.json", modif="2026-10-15T00:00:00Z"):
    return {
        "id": rid, "titre": titre, "taille": chemin.stat().st_size,
        "modifie_le": modif,
        "url": "https://static.data.gouv.fr/resources/official-test/decp.json",
    }


def catalogue(ressources):
    return {"resources": [
        {
            "title": elt["titre"], "id": elt["id"], "filesize": elt["taille"],
            "last_modified": elt["modifie_le"], "format": "json", "url": elt["url"],
        } for elt in ressources
    ]}


def test_decouverte_de_tous_les_mois_et_plafond(tmp_path):
    f1 = fichier(tmp_path, {"marches": [marche()]})
    a = selection(f1)
    b = dict(a, id=RID_B, titre="decp-2025-12.json", taille=230000000)
    tous, exclus = selectionner(catalogue([b, a]))
    assert [x["id"] for x in tous] == [RID_A, RID_B]
    assert exclus == 0
    petits, exclus = selectionner(catalogue([b, a]), maximum_octets=100000)
    assert [x["id"] for x in petits] == [RID_A]
    assert exclus == 1
    with pytest.raises(CollecteConsolideeInvalide, match="répété"):
        selectionner(catalogue([a, a]))


def test_importation_en_flux_identites_versions_et_recherche(tmp_path):
    f = fichier(tmp_path, {"marches": {"marche": [
        marche(), marche(), marche(objet="Étude scientifique actualisée"),
        marche(numero="M-2"), marche(numero="M-1", acheteur="12345678901234"),
    ], "contrat-concession": [
        {"id": "C-1", "objet": "Concession distincte"},
    ]}})
    db = tmp_path / "persistent.sqlite3"
    s = selection(f)
    r = importer(db, s, f, sha=_sha256(f))
    assert r["fichiers_nouveaux"] == 1
    assert r["marches_lus"] == 5
    assert r["notices_admises"] == 5
    assert r["concessions_omises"] == 1
    assert r["versions_nouvelles"] == 4
    assert r["attestations_nouvelles"] == 4
    assert etat(db)["identites_marche"] == 3
    assert etat(db)["versions"] == 4
    assert len(rechercher(db, "scientifique")) == 4
    retour = importer(db, s, f)
    assert retour.get("fichiers_nouveaux", 0) == 0
    assert etat(db)["attestations"] == 4


def test_cas_mal_forme_annule_100_pour_cent_des_ecritures(tmp_path):
    db = tmp_path / "donnees.db"
    f = tmp_path / "incomplet.json"
    f.write_text('{"marches":[{"id":"M-1","acheteur":{"id":"21750001630066"},'
                 '"objet":"Étude","nature":"Marché"},', encoding="utf-8")
    s = selection(f)
    with pytest.raises(DocumentDECPInvalide):
        importer(db, s, f)
    assert etat(db)["identites_marche"] == 0
    assert etat(db)["versions"] == 0
    assert etat(db)["ressources_mensuelles"] == 0


def test_notifications_rejetees_sans_suppression_des_valides(tmp_path):
    f = fichier(tmp_path, {"marches": [
        marche(), marche(acheteur="inconnu"), marche(numero="M-3")
    ]})
    db = tmp_path / "donnees.db"
    sortie = importer(db, selection(f), f)
    assert sortie["notices_admises"] == 2
    assert sortie["rejets"] == 1
    assert etat(db)["identites_marche"] == 2


def test_evenement_de_correction_conserve_deux_versions_et_sources(tmp_path):
    db = tmp_path / "donnees.db"
    f1 = fichier(tmp_path, {"marches": [marche(objet="Version initiale")]})
    s1 = selection(f1, modif="2026-10-14T09:00:00Z")
    importer(db, s1, f1)
    f2 = fichier(tmp_path, {"marches": [marche(objet="Version corrigée")]})
    s2 = selection(f2, modif="2026-10-15T09:00:00Z")
    importer(db, s2, f2)
    assert etat(db)["identites_marche"] == 1
    assert etat(db)["versions"] == 2
    assert etat(db)["attestations"] == 2
    assert rechercher(db, "initiale")
    assert rechercher(db, "corrigée")


def test_collecte_incrementale_evite_les_secondes_telechargements(tmp_path):
    db = tmp_path / "donnees.db"
    f1 = fichier(tmp_path, {"marches": [marche()]})
    original = selection(f1)
    catalog = catalogue([original])
    appels = []
    def telecharge(s, _racine):
        appels.append(s["id"])
        return f1, _sha256(f1)
    a = cycle(db, tmp_path / "sources", catalogue=catalog, telecharge=telecharge)
    assert a["fichiers_importes"] == 1
    assert a["identites_marche"] == 1
    b = cycle(db, tmp_path / "sources", catalogue=catalog, telecharge=telecharge)
    assert b["fichiers_importes"] == 0
    assert appels == [RID_A]
    prochain = dict(original, modifie_le="2026-10-16T02:00:00Z")
    c = cycle(db, tmp_path / "sources", catalogue=catalogue([prochain]),
              telecharge=telecharge)
    assert c["fichiers_tentes"] == 1
    assert c["fichiers_importes"] == 0
    assert appels == [RID_A, RID_A]


def test_l_index_reutilise_les_releves_decp_existants(tmp_path):
    db = tmp_path / "donnees.db"
    releve = {
        "version": "decp-fichier-json-v1", "source_catalogue": "aife_api_decp",
        "page_catalogue": "https://www.data.gouv.fr/datasets/api-decp",
        "ressource_id": RID_B, "sha256_fichier_brut": "d" * 64,
        "releve_le": "2026-10-14T08:00:00Z",
        "extraits_plafonnes": False,
        "releves": {"marches_uniques_valides": 1},
        "marches_extraits": [{
            "id_marche": "M-1", "acheteur_siret": "21750001630066",
            "objet": "Recherche en sciences", "code_cpv": "73100000-3",
            "nature": "Marché", "date_notification": "2026-10-10",
            "date_publication_declaree": "2026-10-14",
            "montant_euros_ht_declare": 150000.0,
            "besoin_encore_ouvert_demontre": False,
            "preuve_de_premiere_contribution": False,
        }],
    }
    importer_releve(db, releve)
    f = fichier(tmp_path, {"marches": [
        marche(objet="Étude scientifique"),
    ]})
    sortie = importer(db, selection(f), f)
    assert sortie["attestations_nouvelles"] == 1
    assert etat(db)["identites_marche"] >= 1
    assert etat(db)["attestations"] == 2


def test_plafond_du_parseur_peut_etre_etendu_sans_modifier_son_defaut():
    contenu = json.dumps({"marches": [marche(numero=f"M-{i}") for i in range(4)]})
    with pytest.raises(DocumentDECPInvalide, match="plafond"):
        list(iterer_documents(StringIO(contenu), plafond_notices=3))
    assert len(list(iterer_documents(
        StringIO(contenu), plafond_notices=4, plafond_source_max=2000000
    ))) == 4
    with pytest.raises(DocumentDECPInvalide, match="Plafond"):
        list(iterer_documents(StringIO("[]"), plafond_notices=200001))


def test_archive_deja_importee_ne_disparait_pas_si_nouveau_fichier_corrompu(tmp_path):
    db = tmp_path / "persistent.db"
    valide = fichier(tmp_path, {"marches": [marche()]})
    importer(db, selection(valide), valide)
    cassé = tmp_path / "casse.json"
    cassé.write_text('{"marches":[{"id":', encoding="utf-8")
    with pytest.raises(DocumentDECPInvalide):
        importer(db, selection(cassé, modif="2026-10-16T00:00:00Z"), cassé)
    assert etat(db)["identites_marche"] == 1
    assert etat(db)["ressources_mensuelles"] == 1
