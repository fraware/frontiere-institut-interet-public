"""Qualification indépendante des avis à partir de captures officielles simulées."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json

import pytest

from scripts.collecter_notices_pilotes_boamp import capturer, adresse
from scripts.qualifier_captures_notices_boamp import (
    QualificationInvalide, ecrire, produire,
)


def creer_registre(tmp_path):
    registre = tmp_path / "cas.json"
    registre.write_text(json.dumps({
        "version": "cas-pilotes-boamp-v1",
        "verification_interpretative_effectuee": False,
        "cas": [
            {"identifiant": "26-100", "date_attendue": "2026-09-01",
             "theme": "audit_technique", "hypotheses": ["competence_specialisee"]},
            {"identifiant": "26-101", "date_attendue": "2026-09-02",
             "theme": "instrument", "hypotheses": ["achat_equipement"]},
            {"identifiant": "26-102", "date_attendue": "2026-09-03",
             "theme": "calcul", "hypotheses": ["infrastructure"]},
        ],
    }), encoding="utf-8")
    return registre


def notice(code, date, nature, etat, *, lie=None, titulaires=None):
    return json.dumps({
        "total_count": 1,
        "results": [{
            "idweb": code, "dateparution": date, "nature": nature,
            "etat": etat, "annonce_lie": lie,
            "type_marche": ["SERVICES"], "titulaire": titulaires,
            "nomacheteur": "Acheteur fictif",
            "datelimitereponse": "2026-10-01T12:00:00+00:00",
        }],
    }, ensure_ascii=False).encode("utf-8")


def fabriquer(tmp_path):
    registre = creer_registre(tmp_path)
    reponses = {
        "26-100": notice("26-100", "2026-09-01", "APPEL_OFFRE",
                         "RECTIFICATIF", lie=["26-099"]),
        "26-101": notice("26-101", "2026-09-02", "APPEL_OFFRE", "INITIAL"),
        "26-102": notice("26-102", "2026-09-03", "ATTRIBUTION", "INITIAL",
                         titulaires=["Entreprise fictive"]),
    }
    captures = tmp_path / "captures"
    def transport(url):
        return next(reponses[c] for c in reponses if url == adresse(c))
    capturer(registre, captures, obtenir=transport,
             instant=datetime(2026, 10, 11, tzinfo=timezone.utc))
    return captures, registre


def test_repartition_et_lien_vers_l_avis_initial(tmp_path):
    captures, registre = fabriquer(tmp_path)
    rapport = produire(captures, registre)
    assert rapport["repartition_documentaire"] == {
        "appel_offres_initial": 1, "avis_attribution": 1, "rectificatif": 1,
    }
    a, b, c = rapport["cas"]
    assert a["avis_anterieurs_explicitement_lies"] == ["26-099"]
    assert a["contenu_des_avis_anterieurs_examine"] is False
    assert b["categorie_documentaire_analytique"] == "appel_offres_initial"
    assert c["titulaires_declares_dans_avis"] == ["Entreprise fictive"]
    assert c["mobilisation_effective_etablie"] is False
    assert c["classification_deficit_competences"] == "indeterminee"
    sortie = tmp_path / "rapport.json"
    ecrire(rapport, sortie)
    avant = sortie.read_bytes()
    ecrire(produire(captures, registre), sortie)
    assert sortie.read_bytes() == avant


def test_refuser_registre_modifie_apres_capture(tmp_path):
    captures, registre = fabriquer(tmp_path)
    avant = registre.read_bytes()
    registre.write_bytes(avant + b" ")
    with pytest.raises(QualificationInvalide, match="registre"):
        produire(captures, registre)


def test_refuser_octets_capture_modifies(tmp_path):
    captures, registre = fabriquer(tmp_path)
    fichier = captures / "26-102.json"
    fichier.write_bytes(fichier.read_bytes() + b"modification")
    with pytest.raises(ValueError, match="Empreinte"):
        produire(captures, registre)


def test_refuser_lien_avant_non_valide(tmp_path):
    registre = creer_registre(tmp_path)
    captures = tmp_path / "captures"
    def transport(url):
        if url == adresse("26-100"):
            return notice("26-100", "2026-09-01",
                          "APPEL_OFFRE", "RECTIFICATIF", lie=["mauvais/lien"])
        if url == adresse("26-101"):
            return notice("26-101", "2026-09-02", "APPEL_OFFRE", "INITIAL")
        return notice("26-102", "2026-09-03", "ATTRIBUTION", "INITIAL")
    capturer(registre, captures, obtenir=transport)
    with pytest.raises(QualificationInvalide, match="Lien"):
        produire(captures, registre)


def test_cas_absent_ne_produit_aucune_attribution_fictive(tmp_path):
    registre = creer_registre(tmp_path)
    captures = tmp_path / "captures"
    def transport(url):
        if url == adresse("26-100"):
            return b'{"total_count":0,"results":[]}'
        if url == adresse("26-101"):
            return notice("26-101", "2026-09-02", "APPEL_OFFRE", "INITIAL")
        return notice("26-102", "2026-09-03", "ATTRIBUTION", "INITIAL")
    capturer(registre, captures, obtenir=transport)
    bilan = produire(captures, registre)
    assert bilan["repartition_documentaire"]["avis_absent_de_la_consultation"] == 1
    assert bilan["cas"][0]["titulaires_declares_dans_avis"] is None
    assert bilan["cas"][0]["classification_deficit_competences"] == "indeterminee"
