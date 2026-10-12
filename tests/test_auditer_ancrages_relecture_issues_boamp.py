"""Tests des références documentaires exactes sur une notice eForms fictive."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import pytest

from scripts.auditer_ancrages_relecture_issues_boamp import (
    auditer, pointeur, JugementInvalide,
)
from scripts.preparer_relecture_issues_boamp import VERSION


DEBUT = (
    "/results/0/donnees/EFORMS/ContractAwardNotice/"
    "ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/"
    "efext:EformsExtension/efac:NoticeResult/efac:LotResult"
)
STAT = DEBUT + "/efac:ReceivedSubmissionsStatistics"


def paquet_fictif(tmp_path):
    reponse = {
        "total_count": 1, "results": [{
            "idweb": "26-6175", "dateparution": "2026-01-20",
            "nature": "ATTRIBUTION",
            "donnees": json.dumps({"EFORMS": {"ContractAwardNotice": {
                "ext:UBLExtensions": {"ext:UBLExtension": {
                    "ext:ExtensionContent": {"efext:EformsExtension": {
                        "efac:NoticeResult": {"efac:LotResult": {
                            "efac:TenderLot": {
                                "cbc:ID": {"#text": "LOT-0001"},
                            },
                            "cbc:TenderResultCode": {"#text": "clos-nw"},
                            "efac:DecisionReason": {
                                "efbc:DecisionReasonCode": {"#text": "other"}
                            },
                            "efac:ReceivedSubmissionsStatistics": [
                                {"efbc:StatisticsCode": {"#text": "tenders"},
                                 "efbc:StatisticsNumeric": "0"},
                                {"efbc:StatisticsCode": {"#text": "t-esubm"},
                                 "efbc:StatisticsNumeric": "0"},
                            ],
                        }},
                    }},
                }},
            }}}),
        }],
    }
    dossier = tmp_path / "sources"
    dossier.mkdir()
    raw = json.dumps(reponse).encode()
    (dossier / "CAS001.json").write_bytes(raw)
    paquet = {
        "version": VERSION,
        "nombre_cas": 1,
        "references_independantes_etablies": False,
        "prequalifications_automatiques_exclues": True,
        "cas": [{"cas": "CAS001", "avis": "26-6175",
                 "sha256_source": hashlib.sha256(raw).hexdigest()}],
    }
    paquet_path = tmp_path / "paquet.json"
    paquet_path.write_text(json.dumps(paquet))
    lot = {
        "lot": "LOT-0001", "decision": "NON_ATTRIBUE",
        "code_motif": "other", "offres_totales": 0,
        "offres_electroniques": 0,
        "cause_non_attribution": "NON_ETABLIE",
        "preuve_identifiant_lot": DEBUT + "/efac:TenderLot/cbc:ID/#text",
        "preuve_decision": DEBUT + "/cbc:TenderResultCode/#text",
        "preuve_motif": DEBUT + "/efac:DecisionReason/efbc:DecisionReasonCode/#text",
        "preuve_offres_totales": STAT + "/0/efbc:StatisticsNumeric",
        "preuve_offres_electroniques": STAT + "/1/efbc:StatisticsNumeric",
        "preuve_effectifs": STAT + "/0/efbc:StatisticsNumeric",
    }
    formulaire = {
        "version": VERSION,
        "sha256_paquet": hashlib.sha256(paquet_path.read_bytes()).hexdigest(),
        "identifiant_relecteur": "lecteur-fictif",
        "declaration_lecture_sans_predictions": True,
        "jugements": [{
            "cas": "CAS001", "statut_avis": "RESULTATS_PAR_LOT",
            "preuve_statut": "/results/0/nature",
            "cause_de_non_attribution": "A_VERIFIER",
            "lots": [lot],
        }],
    }
    # La source, la lecture et l'empreinte sont ici artificielles.
    formulaire["jugements"][0].pop("cause_de_non_attribution")
    lecture = tmp_path / "lecture.json"
    lecture.write_text(json.dumps(formulaire))
    return paquet_path, lecture, dossier


def test_deux_compteurs_zero_distincts_avec_motif_autre(tmp_path):
    p, l, d = paquet_fictif(tmp_path)
    resultat = auditer(p, l, d)
    assert resultat["avis_controles"] == 1
    assert resultat["lots_ancres"] == 1
    assert resultat["statistiques_verifiees"] == 2
    assert resultat["independance_des_lecteurs_etablie"] is False


def test_zero_non_atteste_est_refuse(tmp_path):
    p, l, d = paquet_fictif(tmp_path)
    fiche = json.loads(l.read_text())
    fiche["jugements"][0]["lots"][0]["offres_totales"] = 2
    l.write_text(json.dumps(fiche))
    with pytest.raises(JugementInvalide, match="Effectif déclaré incompatible"):
        auditer(p, l, d)


def test_compteur_electronique_ne_peut_servir_de_total(tmp_path):
    p, l, d = paquet_fictif(tmp_path)
    fiche = json.loads(l.read_text())
    fiche["jugements"][0]["lots"][0]["preuve_offres_totales"] = (
        STAT + "/1/efbc:StatisticsNumeric"
    )
    l.write_text(json.dumps(fiche))
    with pytest.raises(JugementInvalide, match="Code de statistique"):
        auditer(p, l, d)


def test_motif_other_ne_peut_etre_reecrit_no_rece(tmp_path):
    p, l, d = paquet_fictif(tmp_path)
    fiche = json.loads(l.read_text())
    fiche["jugements"][0]["lots"][0]["code_motif"] = "no-rece"
    l.write_text(json.dumps(fiche))
    with pytest.raises(JugementInvalide, match="Motif officiel"):
        auditer(p, l, d)


def test_identifiant_d_un_autre_lot_est_refuse(tmp_path):
    p, l, d = paquet_fictif(tmp_path)
    fiche = json.loads(l.read_text())
    fiche["jugements"][0]["lots"][0]["lot"] = "LOT-0002"
    l.write_text(json.dumps(fiche))
    with pytest.raises(JugementInvalide, match="Identifiant de lot"):
        auditer(p, l, d)


def test_source_alteree_est_refusee(tmp_path):
    p, l, d = paquet_fictif(tmp_path)
    with (d / "CAS001.json").open("ab") as f:
        f.write(b"alteration")
    with pytest.raises(JugementInvalide, match="Empreinte source incompatible"):
        auditer(p, l, d)


def test_pointeur_absent_et_echappement_incorrect(tmp_path):
    p, l, d = paquet_fictif(tmp_path)
    source = json.loads((d / "CAS001.json").read_text())
    assert pointeur(source, "/results/0/nature") == "ATTRIBUTION"
    with pytest.raises(JugementInvalide, match="Champ de preuve absent"):
        pointeur(source, "/results/0/champ_inexistant")
    with pytest.raises(JugementInvalide, match="Échappement"):
        pointeur(source, "/results/0/~5")


def test_decision_attribuee_incompatible_avec_clos_nw(tmp_path):
    p, l, d = paquet_fictif(tmp_path)
    fiche = json.loads(l.read_text())
    lot = fiche["jugements"][0]["lots"][0]
    lot["decision"] = "ATTRIBUE"
    lot["cause_non_attribution"] = "SANS_OBJET"
    l.write_text(json.dumps(fiche))
    with pytest.raises(JugementInvalide, match="Décision de lot différente"):
        auditer(p, l, d)
