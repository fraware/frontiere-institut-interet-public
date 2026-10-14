"""Essais d'une archive de test sans requête réseau et sans vrai DCE."""
from __future__ import annotations

import io
from zipfile import ZipFile, ZIP_DEFLATED

import pytest

from scripts.relever_dce_dgac_public import (
    CIBLES_PDF, CollecteRefusee, TAILLE_MAX_ARCHIVE,
    _verifier_adresse, analyser_archive,
)


def construire(entrees: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with ZipFile(buf, "w", ZIP_DEFLATED) as z:
        for nom, contenu in entrees.items():
            z.writestr(nom, contenu)
    return buf.getvalue()


def jeu_valide():
    return {x: b"%PDF-1.7\nfixture synthetic and public\n" for x in CIBLES_PDF}


def test_validation_et_empreintes_independantes():
    result = analyser_archive(construire(jeu_valide()))
    assert result["nombre_documents_pdf_controles"] == 2
    assert result["contenus_des_pieces_republies"] is False
    assert result["authenticite_de_la_version_place_verifiee"] is False
    assert len(result["sha256_archive"]) == 64
    assert all(len(x["sha256"]) == 64 for x in result["documents_pdf"])


def test_repertoire_zip_inoffensif_accepte():
    documents = jeu_valide()
    documents["dossier/"] = b""
    assert analyser_archive(construire(documents))["nombre_documents_pdf_controles"] == 2


def test_liste_incomplete_refusee():
    with pytest.raises(CollecteRefusee, match="non retrouvées"):
        analyser_archive(construire({"2026-SNARP-001 CCTP.pdf": b"%PDF-1.7\n"}))


def test_entree_traversante_refusee():
    documents = jeu_valide()
    documents["../secret.txt"] = b"surprise"
    with pytest.raises(CollecteRefusee, match="dangereux"):
        analyser_archive(construire(documents))


def test_faux_pdf_refuse():
    documents = jeu_valide()
    documents["2026-SNARP-001 CCTP.pdf"] = b"faux PDF"
    with pytest.raises(CollecteRefusee, match="non conforme"):
        analyser_archive(construire(documents))


def test_archive_invalide_et_volume_excessif_refuses():
    with pytest.raises(CollecteRefusee, match="corrompue"):
        analyser_archive(b"fausse archive")
    with pytest.raises(CollecteRefusee, match="Longueur"):
        analyser_archive(b"x" * (TAILLE_MAX_ARCHIVE + 1))


@pytest.mark.parametrize("url", [
    "http://betterplace.info/files/3013529-dce.zip",
    "https://example.org/files/3013529-dce.zip",
    "https://betterplace.info.evil.org/",
    "https://u:p@betterplace.info/",
    "https://betterplace.info:444/files/3013529-dce.zip",
])
def test_adresses_exterieures_refusees(url):
    with pytest.raises(CollecteRefusee, match="autorisé"):
        _verifier_adresse(url)
