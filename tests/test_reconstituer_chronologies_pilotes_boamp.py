"""Éprouver l'extraction des jalons et des résultats par lot."""
from __future__ import annotations
import hashlib
import json
import pytest
from scripts.reconstituer_chronologies_pilotes_boamp import (
    analyser_attribution, champ_date, produire, ChronologieInvalide,
)


def attribution(*, doublon=False, emission="2025-10-07+01:00"):
    racine = {
        "efac:SettledContract": {
            "cbc:ID": {"#text": "CON-0001"},
            "cbc:AwardDate": "2025-09-24+01:00",
            "cbc:IssueDate": emission,
        },
        "efac:LotResult": [
            {"efac:TenderLot": {"cbc:ID": {"#text": "LOT-0001"}},
             "cbc:TenderResultCode": {"#text": "selec-w"},
             "efac:SettledContract": {"cbc:ID": {"#text": "CON-0001"}}},
            {"efac:TenderLot": {"cbc:ID": {"#text": "LOT-0001" if doublon else "LOT-0002"}},
             "cbc:TenderResultCode": {"#text": "clos-nw"},
             "efac:DecisionReason": {"efbc:DecisionReasonCode": {"#text": "no-rece"}}},
        ],
    }
    return {
        "donnees": json.dumps({"EFORMS": {"ContractAwardNotice": {
            "ext:UBLExtensions": {"ext:UBLExtension": {"ext:ExtensionContent": {
                "efext:EformsExtension": {"efac:NoticeResult": racine}
            }}},
            "cac:TenderResult": {"cbc:AwardDate": "2000-01-01Z"},
        }}})
    }


def test_deux_lots_et_dates_exactement_delimitees():
    bilan = analyser_attribution(attribution())
    contrat = bilan["contrats"][0]
    assert contrat["date_attribution_declaree"] == "2025-09-24"
    assert contrat["date_emission_contrat_declaree"] == "2025-10-07"
    assert contrat["date_debut_execution"] is None
    assert contrat["date_premiere_contribution_utile"] is None
    assert "SettledContract" in contrat["origine_date_attribution"]
    assert [x["statut_lot"] for x in bilan["resultats_par_lot"]] == [
        "attribue", "non_attribue",
    ]
    assert bilan["resultats_par_lot"][1]["motif_officiel"] == "no-rece"
    assert bilan["resultats_par_lot"][1]["contrat_reference"] is None


def test_dates_incoherentes_et_lots_identiques_refuses():
    with pytest.raises(ChronologieInvalide, match="antérieure"):
        analyser_attribution(attribution(emission="2025-09-23+01:00"))
    with pytest.raises(ChronologieInvalide, match="lot"):
        analyser_attribution(attribution(doublon=True))
    with pytest.raises(ChronologieInvalide, match="Date"):
        champ_date("2025-27-99+01:00", "exemple")


def test_produire_a_partir_d_un_releve_sans_inference(monkeypatch, tmp_path):
    import scripts.reconstituer_chronologies_pilotes_boamp as module
    source = tmp_path / "principal"
    source.mkdir()
    fiche = {
        "idweb": "26-100", "dateparution": "2026-03-25",
        "nature": "ATTRIBUTION", **attribution(),
    }
    brut = json.dumps({"total_count": 1, "results": [fiche]}).encode()
    (source / "26-100.json").write_bytes(brut)
    registre = tmp_path / "cas.json"
    registre.write_bytes(b"registre-intangible")
    empreinte = hashlib.sha256(registre.read_bytes()).hexdigest()
    monkeypatch.setattr(module, "verifier_capture", lambda _: {
        "sha256_registre": empreinte, "observe_le": "2026-10-11T00:00:00+00:00",
        "cas": [{"identifiant": "26-100",
                 "etat_observation": "notice_retrouvee_et_identifiee",
                 "fichier_reponse": "26-100.json",
                 "sha256_reponse_http": hashlib.sha256(brut).hexdigest()}],
    })
    monkeypatch.setattr(module, "lire_cas", lambda _: [
        {"identifiant": "26-100", "date_attendue": "2026-03-25"}
    ])
    result = produire(source, registre)
    assert result["nombre_cas"] == 1
    assert result["lots_attribues"] == 1
    assert result["lots_non_attribues"] == 1
    assert result["delais_besoin_vers_contribution_mesurables"] == 0
    assert result["cas"][0]["contribution_utile_observee"] is False
    assert result["cas"][0]["deficit_competences_etabli"] is False
