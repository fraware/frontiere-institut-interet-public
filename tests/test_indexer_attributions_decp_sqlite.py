"""Tests hors réseau du registre local d'attributions DECP."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.indexer_attributions_decp_sqlite import (
    IndexDECPInvalide, importer, rechercher, verifier_rapport,
)

RID = "db50f1f1-9fe5-4f9e-93dd-d273617d4a26"


def marche(id_marche="M-1", siret="21750001630066", objet="Étude scientifique"):
    return {
        "id_marche": id_marche, "acheteur_siret": siret,
        "objet": objet, "code_cpv": "73100000-3", "nature": "Marché",
        "date_notification": "2026-10-11",
        "date_publication_declaree": "2026-10-13",
        "montant_euros_ht_declare": 100000.0,
        "offres_recues_declarees": None,
        "marche_innovant_declare": None,
        "preuve_de_premiere_contribution": False,
        "besoin_encore_ouvert_demontre": False,
    }


def rapport(lignes=None, fichier="a"):
    lignes = [marche()] if lignes is None else lignes
    return {
        "version": "decp-fichier-json-v1",
        "source_catalogue": "aife_api_decp",
        "ressource_id": RID,
        "page_catalogue": "https://www.data.gouv.fr/datasets/api-decp",
        "sha256_fichier_brut": hashlib.sha256(fichier.encode()).hexdigest(),
        "releve_le": "2026-10-13T03:30:00+00:00",
        "extraits_plafonnes": False,
        "releves": {"marches_uniques_valides": len(lignes)},
        "marches_extraits": lignes,
    }


def test_indexation_idempotente_et_recherche(tmp_path):
    db = tmp_path / "marches.sqlite3"
    r = importer(db, rapport())
    assert r["identites_marche"] == 1
    assert r["versions_conservees"] == 1
    assert r["attestations_de_fichier"] == 1
    assert not r["indicateur_de_besoin_ouvert"]
    assert r["correspondances_boamp_verifiees"] == 0
    deux = importer(db, rapport())
    assert deux["nouvelles_identites"] == 0
    assert deux["nouvelles_versions"] == 0
    assert deux["nouvelles_attestations"] == 0
    trouve = rechercher(db, "scientifique")
    assert len(trouve) == 1
    assert trouve[0]["acheteur_siret"] == "21750001630066"
    assert trouve[0]["sources_documentaires"] == 1


def test_versions_et_fichiers_differents_conserves(tmp_path):
    db = tmp_path / "marches.sqlite3"
    importer(db, rapport())
    deux = importer(db, rapport(fichier="b"))
    assert deux["versions_conservees"] == 1
    assert deux["attestations_de_fichier"] == 2
    assert rechercher(db, "scientifique")[0]["sources_documentaires"] == 2

    suivant = rapport(lignes=[marche(objet="Étude optique")], fichier="c")
    resultat = importer(db, suivant)
    assert resultat["identites_marche"] == 1
    assert resultat["versions_conservees"] == 2
    assert resultat["fichiers_suivis"] == 3
    assert len(rechercher(db, "optique")) == 1
    assert len(rechercher(db, "scientifique")) == 1


def test_deux_acheteurs_meme_id_restent_independants(tmp_path):
    db = tmp_path / "marches.sqlite3"
    info = rapport(lignes=[
        marche(siret="21750001630066"),
        marche(siret="12345678901234"),
    ])
    result = importer(db, info)
    assert result["identites_marche"] == 2
    assert result["versions_conservees"] == 2


def test_releve_partiel_est_explicitement_refuse(tmp_path):
    db = tmp_path / "releve_partiel.sqlite3"
    p = rapport()
    p["extraits_plafonnes"] = True
    with pytest.raises(IndexDECPInvalide):
        importer(db, p)
    assert not db.exists()


@pytest.mark.parametrize("champ,valeur", [
    ("acheteur_siret", "0001"),
    ("id_marche", ""),
    ("objet", ""),
    ("date_notification", "2026-02-30"),
    ("code_cpv", "ABCDE"),
    ("montant_euros_ht_declare", float("inf")),
    ("besoin_encore_ouvert_demontre", True),
])
def test_notices_invalides_ne_sont_pas_indexees(champ, valeur):
    p = rapport()
    p["marches_extraits"][0][champ] = valeur
    with pytest.raises(IndexDECPInvalide):
        verifier_rapport(p)


def test_indexation_complete_d_une_sonde_reelle_si_disponible(tmp_path):
    source = Path("institutionnel/decp/sonde_aife_json.json")
    if not source.is_file():
        pytest.skip("Première sortie réelle non encore publiée")
    data = json.loads(source.read_text(encoding="utf-8"))
    if data["extraits_plafonnes"]:
        pytest.skip("Sortie précédente bornée à 50 : ingestion locale complète différée")
    statistique = importer(tmp_path / "reel.sqlite3", data)
    assert statistique["identites_marche"] == data["releves"]["marches_uniques_valides"]
    assert statistique["versions_conservees"] == statistique["identites_marche"]
