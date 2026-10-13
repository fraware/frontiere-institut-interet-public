"""Contrôles hors réseau des relations explicites au sein d'un avis BOAMP."""
from __future__ import annotations

from copy import deepcopy
import json

import pytest

from scripts.reconstituer_chaines_acheteurs_boamp_decp import (
    ChaineInvalide, organisations_acheteur, declarations_lots,
    attributs_attribution, nom_normalise,
)

SIRET = "11000201100044"
ACHETEUR = "ORG-0001"


def formulaire():
    return {
        "cac:ContractingParty": {
            "cac:Party": {"cac:PartyIdentification": {
                "cbc:ID": {"#text": ACHETEUR}}},
        },
        "ext:UBLExtensions": {"ext:UBLExtension": {
            "ext:ExtensionContent": {"efext:EformsExtension": {
                "efac:Organizations": {"efac:Organization": [
                    {"efac:Company": {
                        "cac:PartyIdentification": {"cbc:ID": ACHETEUR},
                        "cac:PartyLegalEntity": {"cbc:CompanyID": SIRET},
                        "cac:PartyName": {"cbc:Name": "MINARM"},
                    }},
                    {"efac:Company": {
                        "cac:PartyIdentification": {"cbc:ID": "ORG-SUPPLIER"},
                        "cac:PartyLegalEntity": {
                            "cbc:CompanyID": "48276116000019"},
                        "cac:PartyName": {"cbc:Name": "Un fournisseur"},
                    }},
                ]},
                "efac:NoticeResult": {
                    "efac:SettledContract": {
                        "cbc:ID": {
                            "#text": "CON-0001", "@schemeName": "contract"},
                        "efac:ContractReference": {"cbc:ID": "2025CC0501"},
                    },
                    "efac:LotResult": {
                        "cbc:TenderResultCode": {"#text": "selec-w"},
                        "efac:TenderLot": {"cbc:ID": "LOT-0001"},
                        "efac:SettledContract": {"cbc:ID": "CON-0001"},
                    },
                },
            }},
        }}},
        "cac:ProcurementProjectLot": [
            {"cbc:ID": {"#text": "LOT-0001", "@schemeName": "Lot"}},
            {"cbc:ID": "LOT-0002"},
        ],
    }


def avis_attribution(form):
    return {"nature": "ATTRIBUTION",
            "donnees": json.dumps({"EFORMS": {
                "ContractAwardNotice": form,
            }})}


def test_rattachement_explicite_acheteur_et_non_fournisseur():
    o = organisations_acheteur(formulaire(), SIRET)
    assert o["identifiant_organisation_dans_avis"] == ACHETEUR
    assert o["nom_organisation_dans_avis"] == "MINARM"
    assert o["index_organisation"] == 0
    with pytest.raises(ChaineInvalide, match="ambigu"):
        organisations_acheteur(formulaire(), "48276116000019")


def test_plusieurs_acheteurs_bloquent_le_lien():
    f = formulaire()
    f["cac:ContractingParty"] = [
        f["cac:ContractingParty"], f["cac:ContractingParty"],
    ]
    with pytest.raises(ChaineInvalide, match="multiple"):
        organisations_acheteur(f, SIRET)


def test_organisations_identiques_repetees_sont_ambigues():
    f = formulaire()
    o = f["ext:UBLExtensions"]["ext:UBLExtension"][
        "ext:ExtensionContent"]["efext:EformsExtension"]["efac:Organizations"][
        "efac:Organization"]
    o.append(deepcopy(o[0]))
    with pytest.raises(ChaineInvalide, match="ambigu"):
        organisations_acheteur(f, SIRET)


def test_lots_sont_locaux_et_les_doublons_sont_refuses():
    f = formulaire()
    assert declarations_lots(f) == ["LOT-0001", "LOT-0002"]
    f["cac:ProcurementProjectLot"].append({"cbc:ID": "LOT-0001"})
    with pytest.raises(ChaineInvalide, match="répété"):
        declarations_lots(f)


def test_relation_contrat_par_identifiants_explicites():
    f = formulaire()
    resultat = attributs_attribution(
        avis_attribution(f), ["LOT-0001", "LOT-0002"]
    )
    assert len(resultat["contrats_locaux"]) == 1
    assert resultat["contrats_locaux"][0]["reference_contrat_declaree"] == "2025CC0501"
    assert resultat["contrats_locaux"][0]["reference_contrat_comparable_decp"] is True
    assert resultat["contrats_locaux"][0]["origine_reference_contrat"].endswith(
        "/efac:ContractReference/cbc:ID"
    )
    assert len(resultat["resultats_lots"]) == 1
    assert resultat["relations_lot_contrat_dans_avis"] == [{
        "lot": "LOT-0001",
        "reference_contrat_locale": "CON-0001",
        "lien_dans_meme_avis": True,
        "identite_contrat_decp_etablie": False,
    }]


def test_reference_de_contrat_sans_definition_est_refusee():
    f = formulaire()
    f["ext:UBLExtensions"]["ext:UBLExtension"]["ext:ExtensionContent"][
        "efext:EformsExtension"]["efac:NoticeResult"][
        "efac:LotResult"]["efac:SettledContract"]["cbc:ID"] = "CON-9999"
    with pytest.raises(ChaineInvalide, match="sans définition"):
        attributs_attribution(avis_attribution(f), ["LOT-0001", "LOT-0002"])


def test_resultat_d_un_lot_non_declare_est_refuse():
    with pytest.raises(ChaineInvalide, match="non déclaré"):
        attributs_attribution(avis_attribution(formulaire()), ["LOT-0002"])


def test_denomination_normalisee_na_pas_de_portee_juridique():
    assert nom_normalise("  MINARM  ") == nom_normalise("minarm")
    assert nom_normalise("MINARM") != nom_normalise(
        "SERVICES DE L'ETAT POUR LA FACTURATION ELECTRONIQUE"
    )


def test_reference_description_nest_pas_une_cle_comparable_decp():
    f = formulaire()
    c = f["ext:UBLExtensions"]["ext:UBLExtension"][
        "ext:ExtensionContent"]["efext:EformsExtension"][
        "efac:NoticeResult"]["efac:SettledContract"]
    c["efac:ContractReference"]["cbc:ID"] = "Lot 1"
    r = attributs_attribution(avis_attribution(f), ["LOT-0001"])
    assert r["contrats_locaux"][0]["reference_contrat_declaree"] == "Lot 1"
    assert r["contrats_locaux"][0]["reference_contrat_comparable_decp"] is False
