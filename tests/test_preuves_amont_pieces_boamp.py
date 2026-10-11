"""Tests hors connexion des avis amont et des références de consultation."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import pytest

from scripts.collecter_notices_pilotes_boamp import adresse, capturer
from scripts.collecter_avis_lies_boamp import capturer_lies
from scripts.capturer_avis_amont_boamp import (
    AvisAmontInvalide, capturer_amont, verifier_amont,
)
from scripts.inventorier_pieces_consultation_boamp import (
    InventaireInvalide, references, produire,
)


def reponse(code, jour, ref, acheteur, nature="APPEL_OFFRE", etat="INITIAL",
            liens=None, dce=False):
    projet = {"cac:ProcurementProject": {"cbc:ID": ref}}
    if dce:
        projet["cac:ProcurementProjectLot"] = {"cac:TenderingTerms": {
            "cac:CallForTendersDocumentReference": {
                "cbc:ID": "1862843",
                "cac:Attachment": {"cac:ExternalReference": {
                    "cbc:URI": "https://www.marches-publics.info/dce?type=DCE&amp;IDM=1862843",
                }},
            }
        }}
    donnees = {"EFORMS": {
        "ContractAwardNotice" if nature == "ATTRIBUTION" else "ContractNotice": projet
    }}
    return json.dumps({"total_count": 1, "results": [{
        "idweb": code, "dateparution": jour, "donnees": json.dumps(donnees),
        "nomacheteur": acheteur, "nature": nature, "etat": etat,
        "annonce_lie": liens,
    }]}, ensure_ascii=False).encode("utf-8")


def preparer(tmp_path):
    registre = tmp_path / "pilotes.json"
    registre.write_text(json.dumps({
        "version": "cas-pilotes-boamp-v1",
        "verification_interpretative_effectuee": False,
        "cas": [
            {"identifiant": "26-74896", "date_attendue": "2026-07-28",
             "theme": "calcul", "hypotheses": ["infrastructure"]},
            {"identifiant": "26-83870", "date_attendue": "2026-08-29",
             "theme": "cyber", "hypotheses": ["audit"]},
        ],
    }), encoding="utf-8")
    aval = {
        "26-74896": reponse("26-74896", "2026-07-28", "METEO-FRANCE 2432F0342",
                            "METEO FRANCE", nature="ATTRIBUTION"),
        "26-83870": reponse("26-83870", "2026-08-29", "M3 2026 04147 M",
                            "Tisséo Ingénierie", etat="RECTIFICATIF",
                            liens=["26-81640"], dce=True),
    }
    principaux = tmp_path / "principaux"
    capturer(registre, principaux,
             obtenir=lambda url: next(val for key, val in aval.items()
                                     if url == adresse(key)))
    lies = tmp_path / "lies"
    capturer_lies(principaux, lies, obtenir=lambda _: reponse(
        "26-81640", "2026-08-20", "M3 2026 04147 M", "Tisséo Ingénierie",
        dce=True,
    ))
    amont_registre = tmp_path / "amont_registre.json"
    amont_registre.write_text(json.dumps({
        "version": "avis-amont-cibles-boamp-v1", "candidats": [
            {"avis_amont": "24-119544", "date_attendue": "2024-10-18",
             "avis_aval": "26-74896",
             "reference_interne_normalisee": "METEOFRANCE2432F0342"},
            {"avis_amont": "26-55633", "date_attendue": "2026-06-07",
             "avis_aval": "26-81640",
             "reference_interne_normalisee": "M3202604147M"},
        ],
    }), encoding="utf-8")
    amont_sources = {
        "24-119544": reponse("24-119544", "2024-10-18",
                             "METEO-FRANCE2432F0342", "Météo-France"),
        "26-55633": reponse("26-55633", "2026-06-07",
                            "M3 2026 04147 M", "Tisseo Ingenierie"),
    }
    return principaux, lies, amont_registre, amont_sources


def obtenir_de(sources):
    return lambda url: next(val for key, val in sources.items()
                            if url == adresse(key))


def test_capture_amont_et_inventaire_integral(tmp_path):
    principaux, lies, registre, sources = preparer(tmp_path)
    destination = tmp_path / "amont"
    rapport = capturer_amont(
        principaux, lies, registre, destination, obtenir=obtenir_de(sources),
        instant=datetime(2026, 10, 11, tzinfo=timezone.utc),
    )
    assert rapport["retrouves"] == 2
    assert rapport["pieces_contractuelles_obtenues"] is False
    assert verifier_amont(destination, principaux, lies, registre) == rapport
    bilan = produire(principaux, lies, destination, registre)
    assert bilan["nombre_avis"] == 5
    assert bilan["avis_avec_lien_de_consultation"] == 2
    assert bilan["nombre_pieces_contenu_obtenu"] == 0
    assert bilan["preuves_de_reception_obtenues"] == 0
    assert bilan["preuves_de_premiere_utilisation_obtenues"] == 0
    assert set(x["avis"] for x in bilan["avis"]) == {
        "26-74896", "26-83870", "26-81640", "24-119544", "26-55633",
    }
    lien = next(x for x in bilan["avis"] if x["avis"] == "26-81640")[
        "references_documentaires_officielles"
    ][0]
    assert lien["identifiant_document_declare"] == "1862843"
    assert lien["uri_normalisee"].endswith("?type=DCE&IDM=1862843")
    assert "&amp;" in lien["uri_litterale"]
    assert lien["contenu_piece_obtenu"] is False


def test_absence_de_l_avis_amont_ne_se_transforme_pas_en_preuve(tmp_path):
    principaux, lies, registre, sources = preparer(tmp_path)
    sources["24-119544"] = b'{"total_count":0,"results":[]}'
    dossier = tmp_path / "amont"
    resultat = capturer_amont(principaux, lies, registre, dossier,
                             obtenir=obtenir_de(sources))
    assert resultat["retrouves"] == 1
    assert resultat["avis"][0]["statut"] == "non_retrouve_lors_du_releve"
    assert produire(principaux, lies, dossier, registre)["nombre_avis"] == 5


def test_refuser_l_avis_sans_identifiant_commun(tmp_path):
    principaux, lies, registre, sources = preparer(tmp_path)
    sources["24-119544"] = reponse("24-119544", "2024-10-18",
                                    "AUTREPROCEDURE", "Météo-France")
    dossier = tmp_path / "amont"
    with pytest.raises(AvisAmontInvalide, match="identifiant interne"):
        capturer_amont(principaux, lies, registre, dossier, obtenir=obtenir_de(sources))
    assert not dossier.exists()


def test_refuser_la_corruption_des_octets_et_le_registre_change(tmp_path):
    principaux, lies, registre, sources = preparer(tmp_path)
    dossier = tmp_path / "amont"
    capturer_amont(principaux, lies, registre, dossier, obtenir=obtenir_de(sources))
    fichier = dossier / "24-119544.json"
    fichier.write_bytes(fichier.read_bytes() + b"corruption")
    with pytest.raises(AvisAmontInvalide, match="Empreinte"):
        verifier_amont(dossier, principaux, lies, registre)
    fichier.write_bytes(sources["24-119544"])
    registre.write_bytes(registre.read_bytes() + b" ")
    with pytest.raises(AvisAmontInvalide, match="registre"):
        verifier_amont(dossier, principaux, lies, registre)


def test_adresse_generique_acheteur_exclue_et_schema_dce_invalide_rejete():
    portail = {"donnees": json.dumps({"EFORMS": {"ContractNotice": {
        "cac:Party": {"cbc:WebsiteURI": "https://example.org"},
    }}})}
    assert references(portail) == []
    interdit = {"donnees": json.dumps({"cac:CallForTendersDocumentReference": {
        "cbc:ID": "DCE",
        "cac:Attachment": {"cac:ExternalReference": {
            "cbc:URI": "javascript:alert(1)",
        }},
    }})}
    with pytest.raises(InventaireInvalide):
        references(interdit)
