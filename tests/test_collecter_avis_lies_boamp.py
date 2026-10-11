"""Contrôles des avis sources associés à des rectificatifs."""
from __future__ import annotations
from datetime import datetime, timezone
import json
import pytest

from scripts.collecter_notices_pilotes_boamp import capturer, adresse
from scripts.collecter_avis_lies_boamp import (
    LienInvalide, capturer_lies, verifier_lies,
)


def preparer(tmp_path):
    registre = tmp_path / "registre.json"
    registre.write_text(json.dumps({
        "version": "cas-pilotes-boamp-v1",
        "verification_interpretative_effectuee": False,
        "cas": [
            {"identifiant": "26-100", "date_attendue": "2026-09-01",
             "theme": "cyber", "hypotheses": ["audit"]},
            {"identifiant": "26-102", "date_attendue": "2026-09-03",
             "theme": "radar", "hypotheses": ["achat"]},
        ],
    }), encoding="utf-8")
    def primaires(url):
        code = "26-100" if url == adresse("26-100") else "26-102"
        return json.dumps({"total_count": 1, "results": [{
            "idweb": code,
            "dateparution": "2026-09-01" if code == "26-100" else "2026-09-03",
            "etat": "RECTIFICATIF" if code == "26-100" else "INITIAL",
            "nature": "APPEL_OFFRE",
            "annonce_lie": ["26-099"] if code == "26-100" else None,
        }]}).encode()
    dossier = tmp_path / "primaires"
    capturer(registre, dossier, obtenir=primaires)
    return dossier


def initial(date="2026-08-31", code="26-099", status="INITIAL"):
    return json.dumps({"total_count": 1, "results": [{
        "idweb": code, "dateparution": date, "etat": status,
        "nature": "APPEL_OFFRE", "objet": "Consultation initiale fictive",
    }]}).encode()


def test_collecte_filiation_exacte_et_rejouable(tmp_path):
    captures = preparer(tmp_path)
    sortie = tmp_path / "lies"
    bilan = capturer_lies(
        captures, sortie, obtenir=lambda url: initial(),
        instant=datetime(2026, 10, 11, tzinfo=timezone.utc),
    )
    assert len(bilan["avis"]) == 1
    assert bilan["nombre_retrouves"] == 1
    assert bilan["avis"][0]["avis_rectificatif"] == "26-100"
    assert bilan["avis"][0]["date_parution"] == "2026-08-31"
    assert bilan["avis"][0]["etat_documentaire"] == "INITIAL"
    assert bilan["origine_du_besoin_etablie"] is False
    assert verifier_lies(sortie, captures) == bilan
    with pytest.raises(LienInvalide, match="existe"):
        capturer_lies(captures, sortie, obtenir=lambda url: initial())


def test_absence_est_inconnue_pas_absence_de_consultation(tmp_path):
    captures = preparer(tmp_path)
    bilan = capturer_lies(
        captures, tmp_path / "sortie",
        obtenir=lambda _: b'{"total_count":0,"results":[]}',
    )
    assert bilan["avis"][0]["etat_recherche"] == "non_retrouve_lors_du_releve"
    assert bilan["avis"][0]["date_parution"] is None


@pytest.mark.parametrize("source", [
    initial(date="2026-09-02"),
    initial(code="26-666"),
    b'{"total_count":2,"results":[]}',
    b'{"total_count":1,"results":[]}',
    b'{"total_count":true,"results":[]}',
    "texte impossible à analyser".encode("utf-8"),
])
def test_contradictions_n_enterrent_pas_de_fichier(tmp_path, source):
    captures = preparer(tmp_path)
    sortie = tmp_path / "sortie"
    with pytest.raises(LienInvalide):
        capturer_lies(captures, sortie, obtenir=lambda _: source)
    assert not sortie.exists()


def test_alteration_relevee_par_empreinte(tmp_path):
    captures = preparer(tmp_path)
    sortie = tmp_path / "lies"
    capturer_lies(captures, sortie, obtenir=lambda _: initial())
    with (sortie / "26-099.json").open("ab") as handle:
        handle.write(b"alteration")
    with pytest.raises(LienInvalide, match="corrompue"):
        verifier_lies(sortie, captures)
