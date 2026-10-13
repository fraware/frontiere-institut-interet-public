"""Tests sans réseau des références documentaires dans les avis eForms."""
import json
import pytest

from scripts.suivre_avis_lies_independants_boamp import LiensInvalides
from scripts.inventorier_pieces_17_et_3_avis_boamp import (
    qualifier_url, extraire,
)


def notice(lots):
    return {"donnees": json.dumps({"EFORMS": {
        "ContractNotice": {"cac:ProcurementProjectLot": lots},
    }})}


def lot(ref, url, id="LOT-0001"):
    return {
        "cbc:ID": id,
        "cac:TenderingTerms": {"cac:CallForTendersDocumentReference": {
            "cbc:ID": ref,
            "cac:Attachment": {"cac:ExternalReference": {"cbc:URI": url}},
        }},
    }


@pytest.mark.parametrize("url,attendue", [
    ("https://www.marches-publics.gouv.fr", "adresse_portail_ou_page_generique"),
    ("https://marches-publics.gouv.fr", "adresse_portail_ou_page_generique"),
    ("https://www.achatpublic.com/sdm/ent2/gen/index.jsp",
     "adresse_portail_ou_page_generique"),
    ("https://www.marches-publics.gouv.fr/?page=Entreprise.EntrepriseAdvancedSearch&AllCons&id=2957868&orgAcronyme=x7c",
     "adresse_dossier_referencee"),
    ("https://www.marches-publics.gouv.fr/entreprise/consultation/3024354?orgAcronyme=s2d",
     "adresse_dossier_referencee"),
    ("https://cc-legrandcharolais.e-marchespublics.com/pack/annonce_marche_public_31312_1127625.html",
     "adresse_dossier_referencee"),
    ("https://www.achatpublic.com/sdm/ent/gen/ent_detail.do?PCSLID=CSL_2026_abcdef",
     "adresse_dossier_referencee"),
    ("https://eur01.safelinks.protection.outlook.com/?url=https%3A%2F%2Fexemple.fr",
     "redirection_externe_non_suivie"),
    ("http://exemple.fr/offre/10", "adresse_absente_ou_inexploitable"),
    ("https://malveillant:secret@exemple.fr/consultation/3024354",
     "adresse_absente_ou_inexploitable"),
    (None, "adresse_absente_ou_inexploitable"),
])
def test_categories_non_probantes(url, attendue):
    assert qualifier_url(url) == attendue


def test_reference_lot_et_url_exacte_sans_piece():
    adresse = "https://www.marches-publics.gouv.fr/entreprise/consultation/3024354"
    resultat = extraire(notice([lot("DOC-1", adresse)]),
                        "26-37752", "avis_echantillon_17", "f" * 64)
    assert len(resultat) == 1
    r = resultat[0]
    assert r["avis"] == "26-37752"
    assert r["reference_declaree"] == "DOC-1"
    assert r["adresse_citee"] == adresse
    assert r["categorie_adresse"] == "adresse_dossier_referencee"
    assert r["chemin_reference"].endswith(
        "/cac:TenderingTerms/cac:CallForTendersDocumentReference")
    assert r["document_telecharge"] is False
    assert r["acte_contractuel_verifie"] is False


def test_reference_identique_repetee_sur_deux_lots():
    adresse = "https://marches.e-marchespublics.com/pack/annonce_marche_public_123_555.html"
    r = extraire(notice([
        lot("DOC-1", adresse, "LOT-0001"),
        lot("DOC-1", adresse, "LOT-0002"),
    ]), "26-37752", "avis_echantillon_17", "a" * 64)
    assert len(r) == 2
    assert [x["lot_position"] for x in r] == [0, 1]
    assert len({x["adresse_citee"] for x in r}) == 1
    assert r[0]["chemin_reference"] != r[1]["chemin_reference"]


def test_reference_sans_url_reste_inconnue():
    r = extraire(
        notice([{"cac:TenderingTerms": {
            "cac:CallForTendersDocumentReference": {"cbc:ID": "DOC-1"},
        }}]), "26-123", "avis_echantillon_17", "b" * 64
    )
    assert r[0]["categorie_adresse"] == "adresse_absente_ou_inexploitable"
    assert r[0]["adresse_citee"] is None


def test_conditions_de_consultation_ambigues_refusees():
    with pytest.raises(LiensInvalides, match="non structurées"):
        extraire(notice([{"cac:TenderingTerms": ["invalide"]}]),
                "26-123", "avis_echantillon_17", "a" * 64)
    with pytest.raises(LiensInvalides, match="Structure"):
        extraire(notice([{"cac:TenderingTerms": {
            "cac:CallForTendersDocumentReference": ["texte"],
        }}]), "26-123", "avis_echantillon_17", "a" * 64)


def test_avis_sans_reference_documentaire():
    assert extraire(notice([{"cbc:ID": "LOT-0001"}]),
                   "26-123", "avis_echantillon_17", "a" * 64) == []
