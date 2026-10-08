"""Essais exclusivement fictifs de conservation d'octets."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.archiver_source_brute import ErreurArchive, archiver, verifier, restaurer


def scenario(tmp_path: Path, contenu: bytes = b"donnees inventees\x00\xff"):
    """Construire un export binaire inventé et une archive isolée."""
    source = tmp_path / "entree.bin"
    source.write_bytes(contenu)
    return source, tmp_path / "archive"


def capturer(source: Path, racine: Path, date: str = "2026-10-08T14:00:00Z"):
    """Archiver les octets avec une provenance explicitement fictive."""
    return archiver(racine, source, source_id="exemple_fictif",
                   url="https://example.org/export.bin", licence="Essai fictif",
                   observe_le=date, etag='"abc"')


def test_archivage_verification_restauration_binaire(tmp_path):
    source, racine = scenario(tmp_path)
    retour = capturer(source, racine)
    assert retour["objet"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert verifier(racine, retour["capture"])["conforme"] is True
    sortie = tmp_path / "restaure.bin"
    restaurer(racine, retour["capture"], sortie)
    assert sortie.read_bytes() == source.read_bytes()
    with pytest.raises(FileExistsError):
        restaurer(racine, retour["capture"], sortie)


def test_capture_idempotente_et_metadonnees_distinctes(tmp_path):
    source, racine = scenario(tmp_path)
    a = capturer(source, racine)
    b = capturer(source, racine)
    c = capturer(source, racine, date="2026-10-09T14:00:00Z")
    assert a == b
    assert c["objet"] == a["objet"]
    assert c["capture"] != a["capture"]


def test_corruption_octets_est_detectee(tmp_path):
    source, racine = scenario(tmp_path)
    a = capturer(source, racine)
    objet = racine / "objets/sha256" / a["objet"][:2] / a["objet"]
    objet.write_bytes(b"corrompu")
    with pytest.raises(ErreurArchive, match="corrompu"):
        verifier(racine, a["capture"])
    with pytest.raises(ErreurArchive, match="altéré"):
        capturer(source, racine)


def test_fiche_modifiee_est_detectee(tmp_path):
    source, racine = scenario(tmp_path)
    a = capturer(source, racine)
    fiche = racine / a["fiche"]
    fiche.write_text("{}", encoding="utf-8")
    with pytest.raises(ErreurArchive, match="modifiée"):
        verifier(racine, a["capture"])


def test_saisie_incorrecte_et_lien_symbolique_refuses(tmp_path):
    source, racine = scenario(tmp_path)
    for params in [dict(source_id="X"), dict(url="file:///secret"), dict(licence=" "),
                   dict(observe_le="2026-10-08")]:
        kw = dict(source_id="exemple_fictif", url="https://example.org/f",
                  licence="Essai", observe_le="2026-10-08T00:00:00Z")
        kw.update(params)
        with pytest.raises(ErreurArchive):
            archiver(racine, source, **kw)
    lien = tmp_path / "lien.bin"
    lien.symlink_to(source)
    with pytest.raises(ErreurArchive, match="lien symbolique"):
        capturer(lien, racine)


def test_archive_ne_contient_aucun_entete_secret(tmp_path):
    source, racine = scenario(tmp_path)
    a = capturer(source, racine)
    fiche = (racine / a["fiche"]).read_text(encoding="utf-8")
    assert "authorization" not in fiche.lower()
    assert "cookie" not in fiche.lower()
