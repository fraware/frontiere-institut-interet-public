"""Contrats de l'index de recherche BOAMP alimenté par des archives vérifiées."""
from datetime import date, datetime, timezone
from pathlib import Path
import json

import pytest

from scripts.collecter_historique_boamp import chemins_jour, publier_jour
from scripts.rechercher_historique_boamp import (
    ArchiveIncoherente, avis_archive, chercher, indexer, mots,
)


def notice(code, jour, objet):
    return {
        "id": code,
        "date_parution": jour.isoformat(),
        "objet": objet,
        "acheteur": "Etablissement public fictif",
        "avis": "https://www.boamp.fr/pages/avis/?q=idweb:" + code,
        "categorie_marche": "SERVICES",
        "etat_avis": "INITIAL",
        "contenu_integral_copie": False,
    }


def creer_archive(dossier, jour, notices):
    return publier_jour(
        dossier, jour, notices, len(notices),
        datetime(2026, 10, 9, 18, tzinfo=timezone.utc),
    )


def test_index_verifie_et_recherche_par_texte(tmp_path):
    source = tmp_path / "sources"
    cible = tmp_path / "index.sqlite3"
    jour1, jour2 = date(2026, 10, 1), date(2026, 9, 30)
    creer_archive(source, jour1, [
        notice("26-100", jour1, "Expertise hydrologique scientifique"),
        notice("26-101", jour1, "Maintenance des véhicules"),
    ])
    creer_archive(source, jour2, [
        notice("26-099", jour2, "Modélisation hydrologique des eaux"),
    ])
    resultat = indexer(source, cible)
    assert resultat["nombre_jours_indexes"] == 2
    assert resultat["nombre_avis_indexes"] == 3
    assert resultat["completude_historique_etablie"] is False
    r = chercher(cible, "hydrologique")
    assert r["total_candidats"] == 2
    assert {x["identifiant"] for x in r["resultats"]} == {"26-100", "26-099"}
    assert r["preuve_de_besoin_scientifique"] is False
    r = chercher(cible, "Modélisation hydrologique", page=1, limite=1)
    assert r["total_candidats"] == 1
    assert r["resultats"][0]["identifiant"] == "26-099"
    assert chercher(cible, "hydrologique", limite=1, page=3)["resultats"] == []


def test_corruption_archive_refusee_sans_detruire_index_anterieur(tmp_path):
    source = tmp_path / "sources"
    cible = tmp_path / "index.sqlite3"
    jour = date(2026, 10, 1)
    creer_archive(source, jour, [notice("26-100", jour, "Analyse des sols")])
    assert indexer(source, cible)["nombre_avis_indexes"] == 1
    p, _ = chemins_jour(source, jour)
    brut = p.read_bytes()
    p.write_bytes(brut[:-1] + bytes([brut[-1] ^ 1]))
    with pytest.raises(ArchiveIncoherente, match="Empreinte"):
        indexer(source, cible)
    assert chercher(cible, "sols")["total_candidats"] == 1


def test_rejet_du_nombre_d_avis_et_de_la_date(tmp_path):
    source = tmp_path / "sources"
    jour = date(2026, 10, 1)
    creer_archive(source, jour, [notice("26-100", jour, "Etude")])
    _, fiche = chemins_jour(source, jour)
    donnees = json.loads(fiche.read_text(encoding="utf-8"))
    donnees["avis_recus"] = 2
    fiche.write_text(json.dumps(donnees), encoding="utf-8")
    with pytest.raises(ArchiveIncoherente, match="Nombre"):
        list(avis_archive(fiche, source))


def test_recherche_refuse_injection_ou_formulaires_vides(tmp_path):
    for requete in ("", " ", "x" * 300, "!!", "a " * 20):
        with pytest.raises(ValueError):
            mots(requete)
    assert mots('sols" OR "secret') == '"sols" AND "or" AND "secret"'
    with pytest.raises(ValueError, match="Index manquant"):
        chercher(tmp_path / "introuvable.sqlite3", "eau")


def test_archive_reelle_publiee_est_verifiable():
    """Vérifier une archive déjà publiée, sans inventer de résultat."""
    racine = Path(__file__).resolve().parents[1] / "institutionnel" / "besoins_publics"
    fiches = sorted((racine / "historique_boamp").glob("20??/??/20??-??-??.json"))
    if not fiches:
        pytest.skip("Aucune journée historique publique disponible dans ce dépôt.")
    jour, archive, sha, notices = avis_archive(fiches[0], racine)
    assert jour == fiches[0].stem
    assert archive.endswith(".jsonl.gz")
    assert len(sha) == 64
    assert len(notices) >= 0
