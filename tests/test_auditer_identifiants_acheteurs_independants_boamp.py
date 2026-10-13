"""Tests de l'audit indépendant : fichiers intègres, rôles et inconnus."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json

import pytest

from scripts.auditer_identifiants_acheteurs_independants_boamp import (
    AuditInvalide, auditer,
)
from scripts.collecter_notices_pilotes_boamp import adresse
from scripts.extraire_references_boamp_decp import siret_acheteur_sans_reference_projet
from scripts.relever_issues_echantillon_independant import capturer
from scripts.tirer_jeu_independant_boamp import MOIS, QUOTA, VERSION as TIRAGE

SIRET = "12345678901234"


def formulaire(*, explicit=False, avec_projet=False):
    identifiant = (
        {"#text": SIRET, "@schemeName": "FR-SIRET"}
        if explicit else SIRET
    )
    racine = {
        "cac:ContractingParty": {"cac:Party": {
            "cac:PartyIdentification": {"cbc:ID": {"#text": "ORG-1"}}
        }},
        "ext:UBLExtensions": {"ext:UBLExtension": {
            "ext:ExtensionContent": {"efext:EformsExtension": {
                "efac:Organizations": {"efac:Organization": [
                    {"efac:Company": {
                        "cac:PartyIdentification": {"cbc:ID": {"#text": "ORG-1"}},
                        "cac:PartyLegalEntity": {"cbc:CompanyID": identifiant},
                    }},
                    {"efac:Company": {
                        "cac:PartyIdentification": {"cbc:ID": {"#text": "ORG-2"}},
                        "cac:PartyLegalEntity": {
                            "cbc:CompanyID": {"#text": "98765432109876",
                                              "@schemeID": "FR-SIRET"}},
                    }},
                ],
            }},
        }}},
    }
    if avec_projet:
        racine["cac:ProcurementProject"] = {"cbc:ID": "2026-MARCHE-001"}
    return {"EFORMS": {"ContractNotice": racine}}


def constituer(tmp_path, *, modifier=None):
    cas = []
    numero = 900
    for mois in MOIS:
        for _ in range(QUOTA):
            cas.append({"avis": f"26-{numero}", "date_parution": mois + "-08"})
            numero += 1
    codes = [c["avis"] for c in cas]
    identifiant_sha = hashlib.sha256(json.dumps(
        codes, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    tirage = tmp_path / "tirage.json"
    tirage.write_text(json.dumps({
        "version": TIRAGE,
        "cas": cas,
        "nombre_cas": len(cas),
        "sha256_identifiants_ordonnes": identifiant_sha,
        "etiquettes_officielles_verifiees": False,
        "comparaison_de_methodes_effectuee": False,
    }), encoding="utf-8")
    reponses = {}
    for i, item in enumerate(cas):
        donnees = (
            formulaire(explicit=i == 1, avec_projet=i == 2)
            if i < 3 else {"FNSimple": {}}
        )
        reponses[item["avis"]] = json.dumps({
            "total_count": 1,
            "results": [{
                "idweb": item["avis"],
                "dateparution": item["date_parution"],
                "nature": "APPEL_OFFRE",
                "donnees": json.dumps(donnees),
            }],
        }).encode("utf-8")
    if modifier is not None:
        reponses = modifier(reponses, cas)
    captures = tmp_path / "releve"
    def obtenir(url):
        return next(value for identifiant, value in reponses.items()
                    if url == adresse(identifiant))
    capturer(tirage, captures, obtenir=obtenir,
            maintenant=datetime(2026, 10, 13, tzinfo=timezone.utc))
    return tirage, captures, cas


def test_36_avis_separes_et_empreintes_verifiees(tmp_path):
    tirage, captures, _ = constituer(tmp_path)
    r = auditer(tirage, captures)
    assert r["nombre_avis_tires"] == 36
    assert r["nombre_avis_distincts"] == 36
    assert r["identifiants_explicitement_siret"] == 1
    assert r["identifiants_14_chiffres_non_qualifies"] == 2
    assert r["repartition_identifiants"]["aucune_identite_acheteur_qualifiable"] == 33
    assert r["correspondances_contractuelles_verifiees"] == 0
    assert r["verification_registre_sirene_effectuee"] is False
    assert all(r["mois"][mois] == QUOTA for mois in MOIS)
    assert r["avis"][0]["reference_projet"] is None
    assert r["avis"][1]["reference_projet"] is None
    assert r["avis"][2]["reference_projet"] is None
    assert r["avis"][0]["champ_identite"].endswith("/cbc:CompanyID")


def test_source_officielle_alteree_est_refusee(tmp_path):
    tirage, captures, cas = constituer(tmp_path)
    fichier = captures / (cas[0]["avis"] + ".json")
    fichier.write_bytes(fichier.read_bytes() + b" ")
    with pytest.raises(AuditInvalide, match="empreinte"):
        auditer(tirage, captures)


def test_tirage_modifie_est_refuse(tmp_path):
    tirage, captures, _ = constituer(tmp_path)
    tirage.write_bytes(tirage.read_bytes() + b" ")
    with pytest.raises(AuditInvalide, match="tirage"):
        auditer(tirage, captures)


def test_statut_du_manifeste_modifie_est_refuse(tmp_path):
    tirage, captures, _ = constituer(tmp_path)
    p = captures / "rapport.json"
    j = json.loads(p.read_text(encoding="utf-8"))
    j["statuts_releve"] = {"avis_observe_sans_resultat_attribution": 35}
    p.write_text(json.dumps(j), encoding="utf-8")
    with pytest.raises(AuditInvalide, match="Distribution"):
        auditer(tirage, captures)


def test_identifiant_de_titulaire_ne_devient_pas_acheteur():
    form = formulaire()
    form["EFORMS"]["ContractNotice"]["cac:ContractingParty"] = {
        "cac:Party": {"cac:PartyIdentification": {
            "cbc:ID": {"#text": "ORG-2"}
        }}
    }
    assert siret_acheteur_sans_reference_projet({
        "donnees": json.dumps(form)
    })["acheteur_siret"] == "98765432109876"


def test_multi_acheteurs_sans_resolution():
    form = formulaire(explicit=True)
    f = form["EFORMS"]["ContractNotice"]
    f["cac:ContractingParty"] = [
        f["cac:ContractingParty"],
        f["cac:ContractingParty"],
    ]
    assert siret_acheteur_sans_reference_projet({
        "donnees": json.dumps(form)
    }) is None
