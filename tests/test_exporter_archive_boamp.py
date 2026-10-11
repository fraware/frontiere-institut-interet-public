"""Essais de conservation portable du corpus public BOAMP."""
from datetime import date, datetime, timezone
from pathlib import Path
import json
from zipfile import ZipFile, ZIP_STORED

import pytest

from scripts.collecter_historique_boamp import publier_jour
from scripts.surveiller_revisions_boamp import conserver_revision
from scripts.exporter_archive_boamp import (
    exporter, verifier_paquet, ArchiveIncoherente,
)


def notice(code, jour, objet):
    return {
        "id": code, "date_parution": jour, "objet": objet,
        "acheteur": "Administration fictive", "etat_avis": "INITIAL",
        "categorie_marche": "SERVICES", "avis": "https://www.boamp.fr/avis/" + code,
        "contenu_integral_copie": False,
    }


def source_validee(tmp_path):
    source = tmp_path / "donnees"
    jour = "2026-10-01"
    original = [notice("26-100", jour, "Etude hydraulique initiale")]
    apres = [notice("26-100", jour, "Etude hydraulique corrigée")]
    t0 = datetime(2026, 10, 9, tzinfo=timezone.utc)
    manifeste = publier_jour(source, date.fromisoformat(jour), original, 1, t0)
    conserver_revision(
        source, jour, manifeste["sha256_archive_gzip"],
        original, apres, datetime(2026, 10, 10, tzinfo=timezone.utc), t0.isoformat(),
    )
    (source / "etat_revisions_boamp.json").write_text(
        json.dumps({
            "etat_connu_par_jour": {
                jour: {
                    "sha256_gzip": manifeste["sha256_archive_gzip"],
                    "observe_le": "2026-10-11T00:00:00+00:00",
                },
            },
            "changements_observes": [],
        }), encoding="utf-8",
    )
    return source


def test_zip_reproductible_et_integralement_verifiable(tmp_path):
    source = source_validee(tmp_path)
    a = tmp_path / "a.zip"
    b = tmp_path / "b.zip"
    preuve_a = exporter(source, a, "a" * 40)
    preuve_b = exporter(source, b, "a" * 40)
    assert preuve_a["sha256_paquet"] == preuve_b["sha256_paquet"]
    assert preuve_a["fichiers_verifies"] == 5
    assert preuve_a["avis_indexes_au_depart"] == 1
    assert preuve_a["copie_hors_site_effectuee"] is False
    assert a.read_bytes() == b.read_bytes()
    with ZipFile(a) as z:
        noms = z.namelist()
        assert "boamp/inventaire.json" in noms
        assert all(n.startswith("boamp/") for n in noms)
        inventaire = json.loads(z.read("boamp/inventaire.json"))
        assert inventaire["revision_depot"] == "a" * 40
        assert inventaire["bilan_index"]["retours_au_releve_initial_retenus"] == 1
    assert verifier_paquet(a)["sha256_paquet"] == preuve_a["sha256_paquet"]


def test_une_modification_du_contenu_du_paquet_est_refusee(tmp_path):
    source = source_validee(tmp_path)
    archive = tmp_path / "a.zip"
    altera = tmp_path / "altera.zip"
    exporter(source, archive, "b" * 40)
    with ZipFile(archive) as original, ZipFile(altera, "w") as cible:
        for info in original.infolist():
            contenu = original.read(info.filename)
            if info.filename.endswith(".jsonl.gz"):
                contenu = contenu[:-1] + bytes([contenu[-1] ^ 1])
            cible.writestr(info.filename, contenu, compress_type=ZIP_STORED)
    with pytest.raises(ArchiveIncoherente, match="Empreinte"):
        verifier_paquet(altera)


def test_orphelin_source_refuse_sans_ecraser_export_precedent(tmp_path):
    source = source_validee(tmp_path)
    fichier = tmp_path / "a.zip"
    exporter(source, fichier, "c" * 40)
    octets = fichier.read_bytes()
    dossier = source / "historique_boamp" / "2026" / "10"
    (dossier / "2026-10-02.jsonl.gz").write_bytes(b"archive sans manifeste")
    with pytest.raises(ArchiveIncoherente, match="sans contrepartie"):
        exporter(source, fichier, "c" * 40)
    assert fichier.read_bytes() == octets


def test_refuser_un_chemin_ou_une_revision_incorrecte(tmp_path):
    source = source_validee(tmp_path)
    (source / "historique_boamp" / "2026" / "10" / "donnees_secretes.txt").write_text(
        "Donnée interdite", encoding="utf-8",
    )
    with pytest.raises(ArchiveIncoherente, match="non autorisé"):
        exporter(source, tmp_path / "x.zip", "d" * 40)
    with pytest.raises(ArchiveIncoherente, match="Révision Git"):
        exporter(source, tmp_path / "y.zip", "invalide")
