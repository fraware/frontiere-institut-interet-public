"""Régressions sur les versions révisées et la sélection documentaire BOAMP."""
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sqlite3

import pytest

from scripts.collecter_historique_boamp import chemins_jour, publier_jour
from scripts.rechercher_historique_boamp import ArchiveIncoherente, indexer, chercher
from scripts.surveiller_revisions_boamp import conserver_revision


def notice(code, jour, objet):
    return {
        "id": code, "date_parution": jour, "objet": objet,
        "acheteur": "Organisme fictif", "categorie_marche": "SERVICES",
        "etat_avis": "INITIAL",
        "avis": "https://www.boamp.fr/avis/" + code,
        "contenu_integral_copie": False,
    }


def preparer(tmp_path):
    source = tmp_path / "donnees"
    cible = tmp_path / "recherche.sqlite3"
    jour = "2026-10-01"
    initial = [
        notice("26-100", jour, "Hydrologie initiale"),
        notice("26-101", jour, "Ecologie initiale"),
    ]
    t0 = datetime(2026, 10, 9, 18, tzinfo=timezone.utc)
    fiche = publier_jour(source, date.fromisoformat(jour), initial, 2, t0)
    return source, cible, jour, initial, t0, fiche


def reviser(source, jour, initial, t0, nouvelles, date_revue):
    from datetime import datetime
    conserver_revision(
        source, jour, hashlib_sha_initial(source, jour), initial, nouvelles,
        date_revue, t0.isoformat(),
    )


def hashlib_sha_initial(source, jour):
    import hashlib
    fichier, _ = chemins_jour(source, date.fromisoformat(jour))
    return hashlib.sha256(fichier.read_bytes()).hexdigest()


def test_index_selectionne_derniere_version_et_preserve_initiale(tmp_path):
    source, cible, jour, initial, t0, fiche = preparer(tmp_path)
    premier = indexer(source, cible)
    assert premier["nombre_jours_avec_revision"] == 0
    assert chercher(cible, "hydrologie")["total_candidats"] == 1
    modifies = [
        notice("26-100", jour, "Calculs quantiques validés"),
        notice("26-102", jour, "Etude marine nouvelle"),
    ]
    reviser(source, jour, initial, t0, modifies,
            datetime(2026, 10, 10, tzinfo=timezone.utc))
    bilan = indexer(source, cible)
    assert bilan["nombre_jours_indexes"] == 1
    assert bilan["nombre_avis_indexes"] == 2
    assert bilan["nombre_versions_corrigees_verifiees"] == 1
    assert bilan["nombre_jours_avec_revision"] == 1
    assert chercher(cible, "hydrologie")["total_candidats"] == 0
    assert chercher(cible, "marine")["resultats"][0]["identifiant"] == "26-102"
    assert "revisions_boamp" in chercher(cible, "quantiques")["resultats"][0]["archive_source"]
    with sqlite3.connect(cible) as conn:
        assert conn.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 2
        assert conn.execute("SELECT nombre_initial,nombre_retenu FROM provenance").fetchone() == (2, 2)
    # L'archive d'origine reste inchangée.
    p, _ = chemins_jour(source, date.fromisoformat(jour))
    assert p.is_file()


def test_derniere_de_deux_revisions_et_selection_temps(tmp_path):
    source, cible, jour, initial, t0, _ = preparer(tmp_path)
    reviser(source, jour, initial, t0,
            [notice("26-200", jour, "Première révision scientifique")],
            datetime(2026, 10, 11, tzinfo=timezone.utc))
    reviser(source, jour, initial, t0,
            [notice("26-201", jour, "Deuxième révision maritime")],
            datetime(2026, 10, 10, tzinfo=timezone.utc))
    b = indexer(source, cible)
    assert b["nombre_versions_corrigees_verifiees"] == 2
    assert b["nombre_avis_indexes"] == 1
    assert chercher(cible, "maritime")["total_candidats"] == 0
    assert chercher(cible, "scientifique")["resultats"][0]["identifiant"] == "26-200"
    with sqlite3.connect(cible) as con:
        assert con.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 3


def test_manifest_revision_corrompu_interrompt_sans_detruire_index(tmp_path):
    source, cible, jour, initial, t0, _ = preparer(tmp_path)
    indexer(source, cible)
    reviser(source, jour, initial, t0, [notice("26-100", jour, "Donnée corrigée")],
            datetime(2026, 10, 10, tzinfo=timezone.utc))
    revision = next((source / "revisions_boamp").glob("**/*.json"))
    manifeste = json.loads(revision.read_text(encoding="utf-8"))
    manifeste["identifiants_modifies"] = []
    revision.write_text(json.dumps(manifeste), encoding="utf-8")
    with pytest.raises(ArchiveIncoherente, match="variations"):
        indexer(source, cible)
    assert chercher(cible, "hydrologie")["total_candidats"] == 1


def test_orphelin_revision_refuse(tmp_path):
    source, cible, jour, initial, t0, _ = preparer(tmp_path)
    dossier = source / "revisions_boamp" / "2026" / "10" / jour
    dossier.mkdir(parents=True)
    (dossier / ("a" * 64 + ".jsonl.gz")).write_bytes(b"fichier sans constat")
    with pytest.raises(ArchiveIncoherente, match="sans manifeste"):
        indexer(source, cible)
    assert not cible.exists()


def test_revision_au_meme_instant_refusee(tmp_path):
    source, cible, jour, initial, t0, _ = preparer(tmp_path)
    premiere = [notice("26-100", jour, "Première correction")]
    seconde = [notice("26-100", jour, "Deuxième correction")]
    date_revision = datetime(2026, 10, 10, tzinfo=timezone.utc)
    reviser(source, jour, initial, t0, premiere, date_revision)
    reviser(source, jour, initial, t0, seconde, date_revision)
    with pytest.raises(ArchiveIncoherente, match="même instant"):
        indexer(source, cible)
