"""Essais hors réseau des trois liens officiels parmi les dix-sept avis."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from zipfile import ZipFile

import pytest

from scripts.collecter_notices_pilotes_boamp import adresse
from scripts.suivre_avis_lies_independants_boamp import (
    LiensInvalides, capturer, classifier_reponse, sources, verifier_archive,
)


def brut_notice(code, date, nature="APPEL_OFFRE", ref="2025CC05", liens=None):
    return json.dumps({"total_count": 1, "results": [{
        "idweb": code, "dateparution": date, "nature": nature,
        "annonce_lie": liens, "nomacheteur": "Acheteur public",
        "donnees": json.dumps({"EFORMS": {"ContractNotice": {
            "cac:ProcurementProject": {"cbc:ID": ref},
        }}}),
    }]}, ensure_ascii=False).encode()


def preuves(tmp_path):
    archive = tmp_path / "historique.zip"
    rapport = tmp_path / "chaines.json"
    dossiers, liste, octets = [], [], {}
    refs = {1: "25-122175", 2: "26-25119", 3: "26-59281"}
    for i in range(17):
        code = f"26-{70000+i}"
        ref = "2025CC05" if i == 1 else f"REF0000{i:02d}"
        brut = brut_notice(
            code, "2026-05-01", nature="ATTRIBUTION" if i == 1 else "APPEL_OFFRE",
            ref=ref, liens=[refs[i]] if i in refs else None,
        )
        octets[code] = brut
        sha = hashlib.sha256(brut).hexdigest()
        dossiers.append({
            "avis_boamp": code,
            "empreinte_avis_boamp": sha,
            "siret_chiffres_sans_schema_boamp": "21060027600013",
        })
        liste.append({"avis": code, "sha256_reponse_http": sha,
                      "octets_reponse_http": len(brut)})
    for i in range(17, 36):
        code = f"26-{70000+i}"
        brut = brut_notice(code, "2026-05-01")
        octets[code] = brut
        liste.append({"avis": code, "sha256_reponse_http":
                      hashlib.sha256(brut).hexdigest(),
                      "octets_reponse_http": len(brut)})
    rapport.write_text(json.dumps({
        "version": "chaines-documentaires-acheteurs-17-avis-v1",
        "nombre_siret_distincts": 16,
        "dossiers": dossiers,
    }), encoding="utf-8")
    with ZipFile(archive, "w") as z:
        z.writestr("releve-issues-36/rapport.json", json.dumps({"cas": liste}))
        for code, brut in octets.items():
            z.writestr("releve-issues-36/" + code + ".json", brut)
    return archive, rapport, refs


def reponse(code, date="2026-04-01", ref="2025CC05"):
    return brut_notice(code, date, ref=ref)


def test_population_de_trois_avis_deux_natures(tmp_path):
    archive, chaines, refs = preuves(tmp_path)
    links, sig = sources(archive, chaines)
    assert len(links) == 3
    assert set(x["avis_lie"] for x in links) == set(refs.values())
    assert sum(x["nature_source"] == "ATTRIBUTION" for x in links) == 1
    assert len(sig) == 64
    assert all(x["lien_explicite_boamp"] for x in links)


def test_capture_explicite_et_integrite_rejouee(tmp_path):
    archive, chaines, refs = preuves(tmp_path)
    def obtenir(url):
        code = next(k for k in refs.values() if adresse(k) == url)
        return reponse(code)
    sortie = tmp_path / "lies"
    rapport = capturer(
        archive, chaines, sortie, obtenir=obtenir,
        instant=datetime(2026, 10, 13, tzinfo=timezone.utc)
    )
    assert rapport["nombre_avis_sources"] == 17
    assert rapport["nombre_liens_explicites"] == 3
    assert rapport["nombre_retrouves"] == 3
    assert rapport["nombre_actes_contractuels_obtenus"] == 0
    assert rapport["nombre_identites_juridiques_confirmees"] == 0
    assert verifier_archive(sortie, archive, chaines) == rapport
    (sortie / "25-122175.json").write_bytes(b"{}")
    with pytest.raises(LiensInvalides, match="Empreinte"):
        verifier_archive(sortie, archive, chaines)


def test_non_trouve_ne_devient_pas_absence_de_consultation():
    cible = {"avis_lie": "25-122175", "date_parution_source": "2026-05-01",
             "reference_procedure_source": "2025CC05",
             "numero_acheteur_source": "21060027600013"}
    d = classifier_reponse(b'{"total_count":0,"results":[]}', cible)
    assert d["statut_recherche"] == "non_retrouve_dans_la_reponse"
    assert d["acte_contractuel_obtenu"] is False


def test_reference_interne_egale_sans_identite_juridique():
    cible = {"avis_lie": "25-122175", "date_parution_source": "2026-05-01",
             "reference_procedure_source": "2025CC05",
             "numero_acheteur_source": "21060027600013"}
    d = classifier_reponse(reponse("25-122175"), cible)
    assert d["correspondance_reference_procedure"] == "reference_interne_concordante"
    assert d["concordance_numero_acheteur"] == "non_comparable"
    assert d["identite_juridique_procedure_demontree"] is False
    d2 = classifier_reponse(reponse("25-122175", ref="2025CC06"), cible)
    assert d2["correspondance_reference_procedure"] == "references_internes_distinctes"


@pytest.mark.parametrize("brut", [
    reponse("25-122175", date="2026-07-01"),
    reponse("25-999999"),
    b'{"total_count":2,"results":[]}',
    b'{"total_count":true,"results":[]}',
    b'{"total_count":1,"results":[]}',
    b"invalid",
])
def test_source_contradictoire_refusee(brut):
    cible = {"avis_lie": "25-122175", "date_parution_source": "2026-05-01",
             "reference_procedure_source": "2025CC05",
             "numero_acheteur_source": "21060027600013"}
    with pytest.raises(LiensInvalides):
        classifier_reponse(brut, cible)


def test_registre_sources_refuse_alteration(tmp_path):
    archive, chaines, _ = preuves(tmp_path)
    d = json.loads(chaines.read_text())
    d["dossiers"][1]["empreinte_avis_boamp"] = "0" * 64
    chaines.write_text(json.dumps(d))
    with pytest.raises(LiensInvalides, match="Empreinte"):
        sources(archive, chaines)
