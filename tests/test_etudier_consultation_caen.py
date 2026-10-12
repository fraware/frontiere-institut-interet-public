"""Tests sans réseau de la filiation des notices radar de Caen."""
import json
import pytest

from scripts.etudier_consultation_caen import (
    analyser, ConsultationInvalide, INITIAL, ATTRIBUTION, DATE_INITIAL,
)


def formulaire(code, nature, date_publication, reference="2025013AOPS038",
               procedure="e4e7736a-46b6-49a0-b1ad-70318afc70eb"):
    lot = lambda code_lot, titre: {
        "cbc:ID": {"#text": code_lot},
        "cac:ProcurementProject": {
            "cbc:Name": {"#text": titre},
            "cac:PlannedPeriod": {"cbc:DurationMeasure": {"#text": "5"}},
        },
        "cac:TenderingTerms": {"cac:AwardingTerms": {
            "cac:AwardingCriterion": {"cbc:CalculationExpression": {
                "#text": "Compétences scientifiques ; moyens humains ; prix"
            }}
        }},
    }
    racine = {
        "cbc:ContractFolderID": procedure,
        "cac:ProcurementProject": {"cbc:ID": {"#text": reference}},
    }
    if nature == "ContractNotice":
        racine["cac:ProcurementProjectLot"] = [
            lot("LOT-0001", "Données radar Bande-X"),
            lot("LOT-0002", "Traitement du signal et algorithmique radar HF"),
        ]
        racine["cac:TenderingProcess"] = {
            "cac:TenderSubmissionDeadlinePeriod": {
                "cbc:EndDate": "2025-07-18"
            }
        }
    return {
        "idweb": code, "dateparution": date_publication,
        "nomacheteur": "Université de Caen Normandie",
        "datelimitereponse": "2025-07-18" if nature == "ContractNotice" else None,
        "donnees": json.dumps({"EFORMS": {nature: racine}}),
    }


def pair():
    return (formulaire(INITIAL, "ContractNotice", DATE_INITIAL),
            formulaire(ATTRIBUTION, "ContractAwardNotice", "2026-03-25"))


def test_caen_deux_lots_dates_et_filiation():
    initial, attribution = pair()
    rapport = analyser(initial, attribution)
    assert rapport["nombre_lots"] == 2
    assert rapport["publication_initiale"] == DATE_INITIAL
    assert rapport["date_limite_reponse_annonce"] == "2025-07-18"
    assert rapport["meme_identifiant_procedure"] is True
    assert rapport["identifiant_interne_commun"] == "2025013AOPS038"
    assert [x["numero"] for x in rapport["lots"]] == ["LOT-0001", "LOT-0002"]
    assert rapport["lots"][1]["intitule"] == "Traitement du signal et algorithmique radar HF"
    assert any(
        x["champ"] == "cbc:CalculationExpression"
        for x in rapport["lots"][1]["champs_publies"]
    )
    assert rapport["lots"][1]["budget_propre_au_lot_etabli"] is False
    assert rapport["lots"][1]["raison_de_non_reponse_etablie"] is False


def test_reference_interne_differente_refusee():
    initial, attribution = pair()
    attribution = formulaire(
        ATTRIBUTION, "ContractAwardNotice", "2026-03-25", reference="AUTRE",
    )
    with pytest.raises(ConsultationInvalide, match="Référence interne"):
        analyser(initial, attribution)


def test_procedure_differente_signalée_et_jamais_assimilée():
    initial, attribution = pair()
    attribution = formulaire(
        ATTRIBUTION, "ContractAwardNotice", "2026-03-25",
        procedure="a3a2a1a0-0000-0000-0000-000000000000",
    )
    assert analyser(initial, attribution)["meme_identifiant_procedure"] is False


def test_date_initiale_incorrecte_refusee():
    initial, attribution = pair()
    initial["dateparution"] = "2025-06-20"
    with pytest.raises(ConsultationInvalide, match="Date officielle"):
        analyser(initial, attribution)


def test_lot_manquant_ou_dupliqué_refusé():
    initial, attribution = pair()
    x = json.loads(initial["donnees"])
    x["EFORMS"]["ContractNotice"]["cac:ProcurementProjectLot"].pop()
    initial["donnees"] = json.dumps(x)
    with pytest.raises(ConsultationInvalide, match="Lots initialement"):
        analyser(initial, attribution)


def test_acheteur_distinct_refusé():
    initial, attribution = pair()
    attribution["nomacheteur"] = "Un autre établissement"
    with pytest.raises(ConsultationInvalide, match="Acheteurs"):
        analyser(initial, attribution)
