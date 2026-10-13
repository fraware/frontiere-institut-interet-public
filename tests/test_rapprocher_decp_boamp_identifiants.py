"""Contrôles hors réseau du rapprochement conservateur BOAMP/DECP."""
import sqlite3

import pytest

from scripts.rapprocher_decp_boamp_identifiants import (
    RapprochementInvalide, rapprocher,
)


def base(tmp_path):
    p = tmp_path / "index.sqlite3"
    with sqlite3.connect(p) as db:
        db.executescript("""
            CREATE TABLE marches (acheteur_siret TEXT, id_marche TEXT);
            CREATE TABLE versions (acheteur_siret TEXT);
            CREATE TABLE attestations (acheteur_siret TEXT);
            INSERT INTO marches VALUES ('12345678901234', 'M-1');
            INSERT INTO marches VALUES ('12345678901234', 'M-2');
        """)
    return p


def registre(refs):
    return {"version": "references-boamp-decp-v1", "avis": [{
        "id_boamp": "26-30147",
        "url_source": "https://www.boamp.fr/exemple",
        "references": refs,
    }]}


def ref(mid, siret="12345678901234"):
    return {"acheteur_siret": siret, "id_marche": mid,
            "chemin_preuve": "/results/0/donnees/EFORMS/reference"}


def test_cle_exacte_est_une_candidate_jamais_une_preuve(tmp_path):
    r = rapprocher(base(tmp_path), registre([ref("M-1"), ref("M-1")]))
    assert r["cle_exacte_candidate"] == 1
    assert r["liens_juridiques_verifies"] == 0
    assert r["resultats"][0]["continuite_juridique_etablie"] is False
    assert r["resultats"][0]["controle_valeur_dans_source_primaire"] is False
    assert len(r["resultats"][0]["identites_decp_candidates"]) == 1


def test_ambiguite_non_resolue(tmp_path):
    r = rapprocher(base(tmp_path), registre([ref("M-1"), ref("M-2")]))
    assert r["plusieurs_cles_candidates"] == 1
    assert len(r["resultats"][0]["identites_decp_candidates"]) == 2


def test_aucun_lien_ne_signifie_pas_absence_de_marche(tmp_path):
    r = rapprocher(base(tmp_path), registre([ref("M-absent")]))
    assert r["aucune_cle_commune"] == 1
    assert r["resultats"][0]["identites_decp_candidates"] == []


@pytest.mark.parametrize("reference", [
    {"acheteur_siret": "123", "id_marche": "M-1", "chemin_preuve": "/x"},
    {"acheteur_siret": "12345678901234", "id_marche": "M-1", "chemin_preuve": ""},
    {"acheteur_siret": "12345678901234", "id_marche": "M-1",
     "chemin_preuve": "/a/../b"},
])
def test_preuve_insuffisante_refusee(tmp_path, reference):
    with pytest.raises(RapprochementInvalide):
        rapprocher(base(tmp_path), registre([reference]))


def test_doublon_avis_refuse(tmp_path):
    paquet = registre([ref("M-1")])
    paquet["avis"].append(dict(paquet["avis"][0]))
    with pytest.raises(RapprochementInvalide):
        rapprocher(base(tmp_path), paquet)


def test_sans_base_refuse(tmp_path):
    with pytest.raises(RapprochementInvalide):
        rapprocher(tmp_path / "absent.sqlite3", registre([ref("M-1")]))
