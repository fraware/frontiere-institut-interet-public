"""Tests hors réseau de l'inventaire des éditeurs et des canaux officiels."""
import json
from pathlib import Path

import pytest

from scripts.inventorier_canaux_publics import (
    InventaireInvalide, normaliser, produire, verifier_configuration,
)


def config():
    return json.loads(Path("institutionnel/canaux_publics/configuration_v1.json").read_text(encoding="utf-8"))


def flux():
    return json.loads(Path("institutionnel/flux_publics/sources_v1.json").read_text(encoding="utf-8"))


def creer_page(dossier: Path, n: int, records: list[dict]) -> Path:
    path = dossier / f"page_{n:05d}.jsonl"
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
    return path


def notice(uid: str, editeur: str, actualise="2026-10-12T10:00:00+00:00"):
    return {
        "id": uid, "titre": "Un jeu de données public",
        "producteur": editeur, "actualise_le": actualise,
        "page": "https://www.data.gouv.fr/datasets/" + uid + "/",
    }


def test_couverture_et_canaux_connus(tmp_path):
    a = creer_page(tmp_path, 1, [
        notice("abcdef123456", "Ministères économiques et financiers"),
        notice("01234567ghij", "Agence nationale de la recherche"),
    ])
    b = creer_page(tmp_path, 2, [
        notice("xyzt98765432", "Ministères économiques et financiers"),
        notice("abcdef123456", "Ministères économiques et financiers", "2026-10-13T10:00:00+00:00"),
        notice("efgh12345678", ""),
    ])
    r = produire(config(), flux(), [a, b])
    s = r["statistiques"]
    assert s["lignes_lues"] == 5
    assert s["jeux_distincts"] == 4
    assert s["reapparitions_identifiants"] == 1
    assert s["lignes_sans_editeur_declare"] == 1
    assert s["pages_presentes"] == 2
    assert s["editeurs_distincts_libelles"] == 2
    assert s["canaux_officiels_documentes"] == 9
    assert not r["couverture_tous_les_organismes_publics"]
    mef = next(x for x in r["editeurs"] if x["organisme_associe"] == "mef")
    assert mef["jeux_declares"] == 2
    assert mef["type_rapprochement"] == "correspondance_de_libelle_configuree"
    assert mef["identite_juridique_verifiee"] is False


def test_lacunes_restent_observables(tmp_path):
    a = creer_page(tmp_path, 1, [notice("abcdef123456", "Producteur non résolu")])
    c = creer_page(tmp_path, 3, [notice("345678uvwxyz", "Producteur non résolu")])
    r = produire(config(), flux(), [a, c])
    assert r["statistiques"]["lacunes_de_pagination"] == 1
    assert r["statistiques"]["numeros_pages_manquantes_exemples"] == [2]
    assert r["statistiques"]["pages_homogenes_temporellement_verifiees"] is False


def test_noms_non_resolus_restent_independants(tmp_path):
    assert normaliser("Ministère des finances") != normaliser("Ministères économiques et financiers")
    a = creer_page(tmp_path, 1, [notice("abcdef123456", "Ministère des finances")])
    r = produire(config(), flux(), [a])
    assert r["editeurs"][0]["organisme_associe"] is None
    assert r["editeurs"][0]["type_rapprochement"] == "non_resolu"
    assert not r["editeurs"][0]["absence_de_canaux_etablie"]


def test_faux_canal_refuse():
    c = config()
    c["organismes_renseignes"][0]["canaux"].append("reseau_inconnu")
    with pytest.raises(InventaireInvalide):
        verifier_configuration(c, flux())


def test_faux_alias_ambigu_refuse():
    c = config()
    c["organismes_renseignes"][1]["editeurs_data_gouv"].append(
        "Ministères économiques et financiers"
    )
    with pytest.raises(InventaireInvalide):
        verifier_configuration(c, flux())


def test_doublon_et_donnees_malformees_refuses(tmp_path):
    a = creer_page(tmp_path, 1, [notice("abcdef123456", "X")])
    with pytest.raises(InventaireInvalide):
        produire(config(), flux(), [a, a])
    a.write_text('{"id": "not-json"\n', encoding="utf-8")
    with pytest.raises(InventaireInvalide):
        produire(config(), flux(), [a])


def test_lecture_des_pages_reelles_si_presentes():
    pages = Path("institutionnel/decouverte/balayage_pages")
    candidats = sorted(pages.glob("page_*.jsonl"))[:10]
    if not candidats:
        pytest.skip("Pages de catalogue absentes")
    r = produire(config(), flux(), candidats)
    assert r["statistiques"]["pages_presentes"] == len(candidats)
    assert r["statistiques"]["jeux_distincts"] > 0
