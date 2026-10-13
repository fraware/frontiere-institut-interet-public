"""Tests hors réseau de l'extraction strictement liée à l'acheteur BOAMP."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json

import pytest

from scripts.collecter_notices_pilotes_boamp import adresse, capturer
from scripts.extraire_references_boamp_decp import (
    references_notice, produire, identifiant_acheteur_14_non_qualifie,
)

SIRET = "12345678901234"
FORMULAIRE = "ContractAwardNotice"


def formulaire(*, schema="FR-SIRET", rattachement="ORG-0001",
               avec_acheteur=True):
    racine = {
        "cac:ProcurementProject": {"cbc:ID": {"#text": "M-01"}},
        "ext:UBLExtensions": {"ext:UBLExtension": {
            "ext:ExtensionContent": {"efext:EformsExtension": {
                "efac:Organizations": {"efac:Organization": [{
                    "efac:Company": {
                        "cac:PartyIdentification": {
                            "cbc:ID": {"#text": rattachement}},
                        "cac:PartyLegalEntity": {
                            "cbc:CompanyID": {"#text": SIRET, "@schemeID": schema}},
                    }
                }, {
                    "efac:Company": {
                        "cac:PartyIdentification": {"cbc:ID": {"#text": "ORG-SUPPLIER"}},
                        "cac:PartyLegalEntity": {"cbc:CompanyID": {
                            "#text": "98765432109876", "@schemeID": "FR-SIRET"}},
                    }
                }]
            }}
        }}},
    }
    if avec_acheteur:
        racine["cac:ContractingParty"] = {
            "cac:Party": {"cac:PartyIdentification": {
                "cbc:ID": {"#text": "ORG-0001"}}}}
    return {"EFORMS": {FORMULAIRE: racine}}


def notice(form=None):
    return {"idweb": "26-100", "donnees": json.dumps(
        formulaire() if form is None else form)}


def test_rattachement_univoque_acheteur_meme_avec_un_fournisseur():
    refs, statut = references_notice(notice())
    assert statut == "reference_couple_explicitement_extraite"
    assert len(refs) == 1
    assert refs[0]["acheteur_siret"] == SIRET
    assert refs[0]["id_marche"] == "M-01"
    assert "cac:ContractingParty" not in refs[0]["chemin_preuve_siret"]
    assert "efac:Organizations" in refs[0]["chemin_preuve_siret"]
    assert refs[0]["type_reference"] == "identifiant_interne_projet_eforms"
    assert refs[0]["identite_contrat_etablie"] is False


def test_acheteur_direct_declare_comme_siret():
    data = formulaire()
    partie = data["EFORMS"][FORMULAIRE]["cac:ContractingParty"]["cac:Party"]
    partie["cac:PartyLegalEntity"] = {
        "cbc:CompanyID": {"#text": SIRET, "@schemeName": "FR-SIRET"}}
    refs, statut = references_notice(notice(data))
    assert len(refs) == 1
    assert statut == "reference_couple_explicitement_extraite"
    assert refs[0]["chemin_preuve_siret"].endswith(
        "/cac:Party/cac:PartyLegalEntity/cbc:CompanyID")


@pytest.mark.parametrize("form,statut", [
    ({"FNSimple": {"attribution": "texte"}}, "format_non_pris_en_charge"),
    (formulaire(avec_acheteur=False), "acheteurs_multiples_ou_absents"),
    (formulaire(schema="FR-SIREN"), "rattachement_organisation_non_univoque"),
    (formulaire(rattachement="ORG-0002"), "rattachement_organisation_non_univoque"),
])
def test_aucun_lien_depuis_un_format_ou_role_incompatible(form, statut):
    assert references_notice(notice(form)) == ([], statut)


def test_deux_acheteurs_differents_rejetes():
    data = formulaire()
    data["EFORMS"][FORMULAIRE]["cac:ContractingParty"] = [
        {"cac:Party": {"cac:PartyIdentification": {"cbc:ID": {"#text": "ORG-0001"}}}},
        {"cac:Party": {"cac:PartyIdentification": {"cbc:ID": {"#text": "ORG-SUPPLIER"}}}},
    ]
    assert references_notice(notice(data))[0] == []


def test_reference_non_identique_ou_non_scalaire_exclue():
    for valeur in ("M 01", ["M-01"], "", "x" * 101):
        data = formulaire()
        data["EFORMS"][FORMULAIRE]["cac:ProcurementProject"]["cbc:ID"] = valeur
        assert references_notice(notice(data))[0] == []


def test_organisations_ambiguës_rejetées():
    data = formulaire()
    organisations = data["EFORMS"][FORMULAIRE]["ext:UBLExtensions"][
        "ext:UBLExtension"]["ext:ExtensionContent"]["efext:EformsExtension"][
        "efac:Organizations"]["efac:Organization"]
    autre = deepcopy(organisations[0])
    autre["efac:Company"]["cac:PartyLegalEntity"]["cbc:CompanyID"]["#text"] = (
        "11111111111111"
    )
    organisations.append(autre)
    assert references_notice(notice(data))[1] == "rattachement_organisation_non_univoque"


def test_capture_reelle_simulee_et_empreinte_verifiee(tmp_path):
    registre = tmp_path / "reg.json"
    registre.write_text(json.dumps({
        "version": "cas-pilotes-boamp-v1",
        "verification_interpretative_effectuee": False,
        "cas": [{"identifiant": "26-100", "date_attendue": "2026-03-25",
                 "theme": "recherche", "hypotheses": ["mobilisation"]}],
    }), encoding="utf-8")

    def transport(url):
        assert url == adresse("26-100")
        return json.dumps({
            "total_count": 1,
            "results": [{"idweb": "26-100", "dateparution": "2026-03-25",
                         "etat": "INITIAL", "nature": "ATTRIBUTION",
                         "donnees": json.dumps(formulaire())}],
        }).encode("utf-8")

    captures = tmp_path / "captures"
    capturer(registre, captures, obtenir=transport,
             instant=datetime(2026, 10, 13, tzinfo=timezone.utc))
    resultat = produire(captures)
    assert len(resultat["avis"]) == 1
    assert resultat["avis"][0]["references"][0]["acheteur_siret"] == SIRET
    assert resultat["avis"][0]["sha256_reponse_http"]
    assert resultat["identites_contractuelles_juridiques_etablies"] == 0
    (captures / "26-100.json").write_bytes(b"alteration")
    with pytest.raises(ValueError, match="Empreinte"):
        produire(captures)


def test_provenance_avec_candidat_incomplet():
    data = formulaire()
    data["EFORMS"][FORMULAIRE].pop("cac:ProcurementProject")
    refs, why = references_notice(notice(data))
    assert refs == []
    assert why == "reference_projet_absente_ou_ambigue"


def test_identifiant_14_sans_schema_est_une_categorie_distincte():
    # Forme structurelle constatée dans les captures officielles, valeurs fictives.
    data = formulaire()
    organisations = data["EFORMS"][FORMULAIRE]["ext:UBLExtensions"][
        "ext:UBLExtension"]["ext:ExtensionContent"]["efext:EformsExtension"][
        "efac:Organizations"]["efac:Organization"]
    organisations[0]["efac:Company"]["cac:PartyLegalEntity"]["cbc:CompanyID"] = SIRET
    refs, statut = references_notice(notice(data))
    assert refs == []
    assert statut == "rattachement_organisation_non_univoque"
    candidat = identifiant_acheteur_14_non_qualifie(notice(data))
    assert candidat["identifiant_14_chiffres"] == SIRET
    assert candidat["siret_juridiquement_verifie"] is False
    assert candidat["categorie"] == "identifiant_acheteur_14_chiffres_sans_schema"
    assert "efac:Organizations" in candidat["chemin_preuve"]


def test_identifiant_14_extrait_meme_sans_reference_projet():
    data = formulaire()
    data["EFORMS"][FORMULAIRE].pop("cac:ProcurementProject")
    organisations = data["EFORMS"][FORMULAIRE]["ext:UBLExtensions"][
        "ext:UBLExtension"]["ext:ExtensionContent"]["efext:EformsExtension"][
        "efac:Organizations"]["efac:Organization"]
    organisations[0]["efac:Company"]["cac:PartyLegalEntity"]["cbc:CompanyID"] = SIRET
    assert references_notice(notice(data))[0] == []
    assert identifiant_acheteur_14_non_qualifie(notice(data))[
        "identifiant_14_chiffres"] == SIRET


def test_identifiant_europeen_ou_titulaire_nest_pas_siret_acheteur():
    data = formulaire()
    organisations = data["EFORMS"][FORMULAIRE]["ext:UBLExtensions"][
        "ext:UBLExtension"]["ext:ExtensionContent"]["efext:EformsExtension"][
        "efac:Organizations"]["efac:Organization"]
    organisations[0]["efac:Company"]["cac:PartyLegalEntity"]["cbc:CompanyID"] = {
        "@schemeName": "eu", "#text": "12345"}
    organisations[1]["efac:Company"]["cac:PartyLegalEntity"]["cbc:CompanyID"] = SIRET
    assert identifiant_acheteur_14_non_qualifie(notice(data)) is None
