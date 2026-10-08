"""Cas fictifs de raccordement d'une capture aux manifestes de sources."""
from __future__ import annotations

import hashlib

import pytest

from scripts.archiver_source_brute import ErreurArchive, archiver
from scripts.verifier_lien_archive_source import verifier_lien


def preparer(tmp_path, source_id="dila_roae", contenu=b"fichier binaire d'essai"):
    brut = tmp_path / "source.bin"
    brut.write_bytes(contenu)
    racine = tmp_path / "archive"
    capture = archiver(
        racine, brut, source_id=source_id,
        url="https://example.org/public/export", licence="Essai fictif",
        observe_le="2026-10-08T12:00:00Z",
    )["capture"]
    return racine, capture, hashlib.sha256(contenu).hexdigest(), len(contenu)


def test_lien_roae_verifie_les_octets_et_la_taille(tmp_path):
    racine, capture, digest, taille = preparer(tmp_path)
    bilan = verifier_lien({
        "source_id": "dila_roae", "sha256_zip": digest,
        "octets_zip": taille, "observe_le": "2026-10-08T12:00:00+00:00",
    }, racine, capture)
    assert bilan["identite_octets_verifiee"] is True
    assert bilan["date_capture_identique_declaree"] is True
    assert bilan["origine_distante_attestee"] is False
    assert bilan["conservation_immuable_confirmee"] is False


@pytest.mark.parametrize("source_id,champ", [
    ("dila_annuaire_local", "sha256_export"),
    ("insee_cog", "sha256_zip"),
])
def test_liaison_des_deux_autres_transports_bruts(tmp_path, source_id, champ):
    racine, capture, digest, _ = preparer(tmp_path, source_id)
    bilan = verifier_lien({"source_id": source_id, champ: digest}, racine, capture)
    assert bilan["sha256_transport_brut"] == digest


def test_rnsr_ne_sert_pas_une_empreinte_semantique_comme_transport(tmp_path):
    racine, capture, digest, _ = preparer(tmp_path, "mesr_rnsr_structures_actives")
    with pytest.raises(ErreurArchive, match="empreinte sémantique"):
        verifier_lien({
            "source_id": "mesr_rnsr_structures_actives", "sha256_semantique_source": digest,
        }, racine, capture)


def test_lien_refuse_une_empreinte_binaire_differente(tmp_path):
    racine, capture, _, taille = preparer(tmp_path)
    with pytest.raises(ErreurArchive, match="divergentes"):
        verifier_lien({
            "source_id": "dila_roae", "sha256_zip": "f" * 64, "octets_zip": taille,
        }, racine, capture)


def test_lien_refuse_identite_de_source_incoherente(tmp_path):
    racine, capture, digest, _ = preparer(tmp_path, "dila_roae")
    with pytest.raises(ErreurArchive, match="Identité de source"):
        verifier_lien({"source_id": "insee_cog", "sha256_zip": digest}, racine, capture)


def test_lien_refuse_taille_incoherente(tmp_path):
    racine, capture, digest, taille = preparer(tmp_path)
    with pytest.raises(ErreurArchive, match="Taille du transport"):
        verifier_lien({
            "source_id": "dila_roae", "sha256_zip": digest, "octets_zip": taille + 1,
        }, racine, capture)
