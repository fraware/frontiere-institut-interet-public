"""Essais hors réseau de la base opérationnelle BOAMP."""
from datetime import date, datetime, timezone
import json
from pathlib import Path

import pytest

from app.plateforme_boamp import (
    CaptureInvalide, StockageBOAMP, importer_cycle, _lire_archive,
)
from scripts.collecter_historique_boamp import chemins_jour, publier_jour


def notice(identifiant="26-1", objet="Calcul scientifique"):
    return {
        "id": identifiant, "objet": objet, "acheteur": "Organisme public",
        "date_parution": "2026-10-01",
        "date_limite_reponse": "2026-11-01", "categorie_marche": "SERVICES",
        "etat_avis": "INITIAL", "avis": "https://www.boamp.fr/avis/26-1",
    }


def source(tmp_path, lignes=None):
    racine = tmp_path / "collecte"
    publier_jour(
        racine, date(2026, 10, 1), lignes if lignes is not None else [notice()],
        len(lignes if lignes is not None else [notice()]),
        datetime(2026, 10, 2, tzinfo=timezone.utc),
    )
    return racine


def stockage(tmp_path):
    return StockageBOAMP("sqlite:///" + str(tmp_path / "boamp.sqlite3"))


def test_importation_incrementation_recherche_et_reprise(tmp_path):
    racine = source(tmp_path, [notice(), notice("26-2", "Cybersécurité")])
    base = stockage(tmp_path)
    premier = importer_cycle(base, racine)
    assert premier["avis_distincts"] == 2
    assert premier["versions_distinctes"] == 2
    assert premier["captures_importees"] == 1
    assert premier["captures_nouvelles"] == 1
    second = importer_cycle(base, racine)
    assert second["captures_importees"] == 1
    assert second["captures_nouvelles"] == 0
    assert second["avis_lus"] == 0
    trouve = base.rechercher("scientifique")
    assert len(trouve) == 1 and trouve[0]["identifiant"] == "26-1"
    assert base.rechercher("Organisme") and not base.rechercher("inexistant")


def test_variantes_sans_perte_et_ordre_des_captures(tmp_path):
    racine = source(tmp_path)
    base = stockage(tmp_path)
    importer_cycle(base, racine)
    actuel = racine / "annonces_boamp.json"
    actuel.write_text(json.dumps({"version": "avis-boamp-v1", "annonces": [
        notice(objet="Supercalculateurs nouveaux")
    ]}), encoding="utf-8")
    (racine / "etat_boamp.json").write_text(json.dumps({
        "controle_le": "2026-10-14T10:00:00+00:00",
        "pages_reussies": 2, "recherche_partielle": False,
    }), encoding="utf-8")
    importer_cycle(base, racine)
    assert base.etat()["avis_distincts"] == 1
    assert base.etat()["versions_distinctes"] == 2
    assert base.rechercher("Supercalculateurs")[0]["identifiant"] == "26-1"
    assert not base.rechercher("scientifique")
    # Un nouvel import de l'archive antérieure ne remplace pas la version récente.
    importer_cycle(base, racine)
    assert base.etat()["versions_distinctes"] == 2


def test_releve_courant_identique_n_est_pas_duplique(tmp_path):
    racine = source(tmp_path, [])
    (racine / "annonces_boamp.json").write_text(json.dumps({
        "version": "avis-boamp-v1", "annonces": [notice()]
    }), encoding="utf-8")
    (racine / "etat_boamp.json").write_text(json.dumps({
        "controle_le": "2026-10-14T00:00:00Z", "pages_reussies": 1,
        "recherche_partielle": True,
    }), encoding="utf-8")
    base = stockage(tmp_path)
    importer_cycle(base, racine)
    premier = base.etat()
    assert premier["captures_importees"] == 2
    assert premier["avis_distincts"] == 1
    importer_cycle(base, racine)
    assert base.etat() == premier


def test_fichier_corrompu_ne_modifie_pas_la_base(tmp_path):
    racine = source(tmp_path)
    archive, _ = chemins_jour(racine, date(2026, 10, 1))
    archive.write_bytes(archive.read_bytes() + b"alteration")
    base = stockage(tmp_path)
    with pytest.raises(CaptureInvalide, match="comprimés"):
        importer_cycle(base, racine)
    assert base.etat()["captures_importees"] == 0
    assert base.etat()["avis_distincts"] == 0


def test_manifeste_manipule_ou_chemin_exterieur_refuse(tmp_path):
    racine = source(tmp_path)
    _, fiche = chemins_jour(racine, date(2026, 10, 1))
    manifeste = json.loads(fiche.read_text(encoding="utf-8"))
    manifeste["archive_relative"] = "../../../fichier-externe.jsonl.gz"
    fiche.write_text(json.dumps(manifeste), encoding="utf-8")
    with pytest.raises(CaptureInvalide, match="extérieure"):
        importer_cycle(stockage(tmp_path), racine)


def test_releve_invalide_ne_masque_pas_une_erreur(tmp_path):
    racine = source(tmp_path, [])
    (racine / "annonces_boamp.json").write_text(json.dumps({
        "version": "avis-boamp-v1", "annonces": [notice(), notice()]
    }), encoding="utf-8")
    (racine / "etat_boamp.json").write_text(json.dumps({
        "controle_le": "2026-10-14T00:00:00Z", "pages_reussies": 1
    }), encoding="utf-8")
    base = stockage(tmp_path)
    with pytest.raises(CaptureInvalide, match="répété"):
        importer_cycle(base, racine)
    assert base.etat()["avis_distincts"] == 0


def test_recherche_litterale_et_limites(tmp_path):
    racine = source(tmp_path, [notice(objet="Taux 50% public")])
    base = stockage(tmp_path)
    importer_cycle(base, racine)
    assert len(base.rechercher("50%")) == 1
    assert base.rechercher("50_") == []
    with pytest.raises(ValueError):
        base.rechercher("x", limite=101)


def test_lecture_d_une_archive_officielle_deja_versionnee():
    """Essai d'intégration sur les octets réellement présents dans le dépôt."""
    racine = Path(__file__).resolve().parents[1] / "institutionnel/besoins_publics"
    fiche = racine / "historique_boamp/2026/10/2026-10-01.json"
    assert fiche.is_file(), "Archive témoin BOAMP absente du dépôt."
    capture, avis, _ = _lire_archive(racine, fiche)
    manifeste = json.loads(fiche.read_text(encoding="utf-8"))
    assert capture["jour_complet"] is True
    assert len(avis) == manifeste["avis_distincts"]
    assert all(x["date_parution"][:10] == "2026-10-01" for x in avis)
