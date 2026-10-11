"""Contrôles hors connexion des captures de notices complètes BOAMP."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json

import pytest

from scripts.collecter_notices_pilotes_boamp import (
    CaptureInvalide, adresse, capturer, qualifier, verifier_capture,
)


def registre(tmp_path):
    source = tmp_path / "pilotes.json"
    source.write_text(json.dumps({
        "version": "cas-pilotes-boamp-v1",
        "verification_interpretative_effectuee": False,
        "cas": [
            {
                "identifiant": "26-100",
                "date_attendue": "2026-09-01",
                "theme": "calcul_intensif",
                "hypotheses": ["infrastructure"],
            },
            {
                "identifiant": "26-101",
                "date_attendue": "2026-09-02",
                "theme": "robotique",
                "hypotheses": ["materiel"],
            },
        ],
    }), encoding="utf-8")
    return source


def enveloppe(identifiant="26-100", date_parution="2026-09-01", *, count=1):
    resultats = [{
        "idweb": identifiant,
        "dateparution": date_parution,
        "etat": "RECTIFICATIF",
        "objet": "Évaluation technique — texte complet",
        "texte_supplementaire": {"description": "Section source conservée"},
    }] if count else []
    return json.dumps({
        "total_count": count,
        "results": resultats,
    }, ensure_ascii=False).encode("utf-8")


def test_capture_conserve_octets_officiels_et_preuves(tmp_path):
    source = registre(tmp_path)
    brut_a = enveloppe()
    brut_b = enveloppe("26-101", "2026-09-02", count=1)
    appels = []

    def transport(url):
        appels.append(url)
        return brut_a if url == adresse("26-100") else brut_b

    destination = tmp_path / "captures"
    rapport = capturer(
        source, destination, obtenir=transport,
        instant=datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc),
    )
    assert appels == [adresse("26-100"), adresse("26-101")]
    assert rapport["nombre_cas"] == 2
    assert rapport["nombre_notices_retrouvees"] == 2
    assert rapport["pieces_de_consultation_obtenues"] is False
    assert rapport["capacites_mobilisables_verifiees"] is False
    assert rapport["historique_integral_des_avis_etabli"] is False
    assert (destination / "26-100.json").read_bytes() == brut_a
    assert rapport["cas"][0]["sha256_reponse_http"] == hashlib.sha256(brut_a).hexdigest()
    assert rapport["cas"][0]["etat_documentaire_reobserve"] == "RECTIFICATIF"
    assert verifier_capture(destination) == rapport
    with pytest.raises(CaptureInvalide, match="existe"):
        capturer(source, destination, obtenir=transport)


def test_absence_est_observation_incomplete_sans_fausse_inference(tmp_path):
    source = registre(tmp_path)
    def transport(url):
        return enveloppe(count=0) if "26-100" in url else enveloppe(
            "26-101", "2026-09-02"
        )
    rapport = capturer(source, tmp_path / "sortie", obtenir=transport)
    assert rapport["nombre_notices_retrouvees"] == 1
    assert rapport["cas"][0]["etat_observation"] == "non_retrouve_lors_de_ce_releve"
    assert rapport["cas"][0]["date_parution_reobservee"] is None
    assert (tmp_path / "sortie" / "26-100.json").exists()


@pytest.mark.parametrize("reponse", [
    b"",
    b"not-json",
    b"[]",
    b'{"results":[]}',
    b'{"total_count":true,"results":[]}',
    enveloppe("26-999", "2026-09-01"),
    enveloppe("26-100", "2026-09-04"),
    b'{"total_count":2,"results":[]}',
    b'{"total_count":0,"results":[{"idweb":"26-100"}]}',
    b'{"total_count":1,"results":[]}',
])
def test_reponses_invalides_ne_produisent_pas_de_capture_partielle(tmp_path, reponse):
    source = registre(tmp_path)
    destination = tmp_path / "captures"
    def transport(url):
        return enveloppe() if "26-100" in url else reponse
    with pytest.raises(CaptureInvalide):
        capturer(source, destination, obtenir=transport)
    assert not destination.exists()


def test_corruption_des_octets_est_detectee(tmp_path):
    source = registre(tmp_path)
    def transport(url):
        return enveloppe() if "26-100" in url else enveloppe(
            "26-101", "2026-09-02"
        )
    destination = tmp_path / "captures"
    capturer(source, destination, obtenir=transport)
    with (destination / "26-100.json").open("ab") as f:
        f.write(b"corruption")
    with pytest.raises(CaptureInvalide, match="Empreinte"):
        verifier_capture(destination)


def test_les_dates_incorrectes_et_identifiants_non_autorises_sont_refuses():
    with pytest.raises(CaptureInvalide):
        adresse("26-123?limit=999")
    with pytest.raises(CaptureInvalide):
        qualifier(enveloppe("26-100", "mal_forme"), "26-100", "2026-09-01")
    with pytest.raises(CaptureInvalide):
        qualifier(enveloppe("26-100", "2026-09-02"), "26-100", "2026-09-01")


def test_horodatage_naif_refuse_et_aucune_sortie(tmp_path):
    source = registre(tmp_path)
    with pytest.raises(CaptureInvalide, match="fuseau"):
        capturer(source, tmp_path / "sortie",
                 obtenir=lambda _: enveloppe(),
                 instant=datetime(2026, 10, 11, 10))
    assert not (tmp_path / "sortie").exists()
