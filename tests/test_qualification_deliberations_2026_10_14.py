"""Contrôles hors réseau du gel documentaire des onze pistes SCDL du 14 octobre 2026."""
from __future__ import annotations

import json
from pathlib import Path


RACINE = Path(__file__).resolve().parents[1]


def test_gel_des_pistes_et_restrictions_probatoires():
    """Comparer les identifiants gelés au registre et interdire les conclusions indues."""
    gel = json.loads(
        (RACINE / "donnees/qualification_deliberations_2026_10_14.json").read_text(
            encoding="utf-8"
        )
    )
    collecte = json.loads(
        (RACINE / "institutionnel/deliberations_publiques/pistes.json").read_text(
            encoding="utf-8"
        )
    )
    assert gel["version"] == "qualification-pistes-deliberations-2026-10-14-v1"
    assert len(gel["qualifications"]) == 11
    identifiants = [p["identifiant"] for p in gel["qualifications"]]
    assert len(identifiants) == len(set(identifiants))
    par_id = {p["identifiant"]: p for p in collecte["pistes"]}
    assert set(identifiants).issubset(par_id)
    for q in gel["qualifications"]:
        source = par_id[q["identifiant"]]
        assert q["deliberation_id"] == source["deliberation_id"]
        assert q["deliberation_date_csv"] == source["deliberation_date"]
        assert q["url_acte_annoncee"] == source["url_document_annonce"]
        assert q["source_csv_sha256"] == source["sha256_csv"]
        assert q["ligne_csv_sha256"] == source["sha256_ligne"]
        assert q["acte_cible_lu"] is False
        assert q["acte_cible_verifie_par_octets"] is False
        assert q["besoin_technique_deficitaire_etabli"] is False
        assert q["usage_attribuable_a_cet_acte_etabli"] is False
        assert q["effet_causal_etabli"] is False
        assert bool(q["source_connexe_ids"]) == (
            q["collectivite"] == "SYNDICAT MIXTE LA FIBRE64"
        )
        assert set(q["source_connexe_ids"]).issubset(gel["sources_connexes"])
    assert sum(q["url_acte_annoncee"] is None for q in gel["qualifications"]) == 1
