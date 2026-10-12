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



def avec_statistiques(statistiques_lot1, statistiques_lot2):
    """Deux lots, un seul soumis et un sans offre selon l'avis original."""
    avis = attribution()
    formulaire = json.loads(avis["donnees"])
    lots = formulaire["EFORMS"]["ContractAwardNotice"]["ext:UBLExtensions"][
        "ext:UBLExtension"
    ]["ext:ExtensionContent"]["efext:EformsExtension"]["efac:NoticeResult"][
        "efac:LotResult"
    ]
    lots[0]["efac:ReceivedSubmissionsStatistics"] = statistiques_lot1
    lots[1]["efac:ReceivedSubmissionsStatistics"] = statistiques_lot2
    avis["donnees"] = json.dumps(formulaire)
    return avis


def statistique(code, valeur):
    return {
        "efbc:StatisticsCode": {"#text": code},
        "efbc:StatisticsNumeric": valeur,
    }


def test_comptes_officiels_par_lot_et_portee_separee():
    bilan = analyser_attribution(
        avec_statistiques(statistique("t-esubm", "1"),
                          statistique("t-esubm", "0"))
    )
    lot1, lot2 = bilan["resultats_par_lot"]
    assert lot1["statistiques_soumissions"][0]["effectif_declare"] == 1
    assert lot1["statistiques_soumissions"][0]["portee_de_la_mesure"] == (
        "soumissions_electroniques"
    )
    assert lot2["statistiques_soumissions"][0]["effectif_declare"] == 0
    assert lot2["statistiques_soumissions"][0]["code_statistique_officiel"] == "t-esubm"
    assert lot2["motif_officiel"] == "no-rece"
    assert lot2["statut_lot"] == "non_attribue"
    assert lot2["statistiques_soumissions"][0]["origine_effectif"].endswith(
        "/efac:LotResult/1/efac:ReceivedSubmissionsStatistics/efbc:StatisticsNumeric"
    )


def test_statistique_tenders_distincte_de_t_esubm():
    bilan = analyser_attribution(avec_statistiques(
        [statistique("tenders", "3"), statistique("t-esubm", 2)],
        statistique("tenders", "0"),
    ))
    marqueurs = bilan["resultats_par_lot"][0]["statistiques_soumissions"]
    assert [(x["code_statistique_officiel"], x["effectif_declare"]) for x in marqueurs] == [
        ("tenders", 3), ("t-esubm", 2),
    ]
    assert marqueurs[0]["portee_de_la_mesure"] == "soumissions_tous_canaux_declares"
    assert "/efac:ReceivedSubmissionsStatistics/0/" in marqueurs[0]["origine_effectif"]


@pytest.mark.parametrize("nombre", [
    "-1", "1.5", True, None, "moins-un", "4e2",
])
def test_refuser_comptes_incompatibles(nombre):
    with pytest.raises(ChronologieInvalide):
        analyser_attribution(avec_statistiques(
            statistique("t-esubm", "1"), statistique("t-esubm", nombre),
        ))


def test_refuser_soumission_positive_si_motif_aucune_offre():
    with pytest.raises(ChronologieInvalide, match="contradictoire"):
        analyser_attribution(avec_statistiques(
            statistique("t-esubm", "1"), statistique("t-esubm", "1"),
        ))


def test_absence_statistique_reste_inconnue():
    bilan = analyser_attribution(attribution())
    assert bilan["resultats_par_lot"][0]["statistiques_soumissions"] == []
    assert bilan["resultats_par_lot"][1]["statistiques_soumissions"] == []


def test_statistique_repetee_identique_conserve_les_deux_provenances():
    valeurs = [
        statistique("t-esubm", "2"),
        statistique("t-sme", "0"),
        statistique("t-esubm", "2"),
    ]
    bilan = analyser_attribution(avec_statistiques(
        valeurs, statistique("t-esubm", "0")
    ))
    mesure = bilan["resultats_par_lot"][0]["statistiques_soumissions"][0]
    assert mesure["effectif_declare"] == 2
    assert len(mesure["occurrences_identiques"]) == 1
    assert mesure["occurrences_identiques"][0]["origine_effectif"].endswith(
        "/efac:ReceivedSubmissionsStatistics/2/efbc:StatisticsNumeric"
    )
    assert len(bilan["resultats_par_lot"][0]["statistiques_soumissions"]) == 2


def test_statistique_repetee_contradictoire_refusee():
    valeurs = [
        statistique("t-esubm", "2"),
        statistique("t-esubm", "3"),
    ]
    with pytest.raises(ChronologieInvalide, match="contradictoires"):
        analyser_attribution(avec_statistiques(
            valeurs, statistique("t-esubm", "0")
        ))


def test_trois_contrats_sur_un_lot_sont_preserves_sans_reference_unique():
    avis = attribution()
    d = json.loads(avis["donnees"])
    resultats = d["EFORMS"]["ContractAwardNotice"][
        "ext:UBLExtensions"]["ext:UBLExtension"]["ext:ExtensionContent"][
        "efext:EformsExtension"]["efac:NoticeResult"]["efac:LotResult"]
    resultats[0]["efac:SettledContract"] = [
        {"cbc:ID": {"#text": f"CON-000{i}"}} for i in range(1, 4)
    ]
    avis["donnees"] = json.dumps(d)
    bilan = analyser_attribution(avis)
    lot = bilan["resultats_par_lot"][0]
    assert lot["statut_lot"] == "attribue"
    assert lot["contrats_references"] == ["CON-0001", "CON-0002", "CON-0003"]
    assert lot["contrat_reference"] is None
    assert bilan["resultats_par_lot"][1]["contrats_references"] == []


def test_contrats_repetes_sur_un_meme_lot_refuses():
    avis = attribution()
    d = json.loads(avis["donnees"])
    resultats = d["EFORMS"]["ContractAwardNotice"][
        "ext:UBLExtensions"]["ext:UBLExtension"]["ext:ExtensionContent"][
        "efext:EformsExtension"]["efac:NoticeResult"]["efac:LotResult"]
    resultats[0]["efac:SettledContract"] = [
        {"cbc:ID": {"#text": "CON-0001"}},
        {"cbc:ID": {"#text": "CON-0001"}},
    ]
    avis["donnees"] = json.dumps(d)
    with pytest.raises(ChronologieInvalide, match="plusieurs fois"):
        analyser_attribution(avis)
