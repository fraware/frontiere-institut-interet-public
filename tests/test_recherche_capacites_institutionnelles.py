"""Essais synthétiques du moteur documentaire local, sans sollicitation réseau."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.rechercher_capacites_institutionnelles import (
    VERSION_INDEX,
    construire_index,
    correspondances,
    fichiers_sources,
    faits_publies,
    normaliser,
    ouvrir_index,
    preparer_entite,
    chercher,
    termes_recherche,
    verifier_sources,
)


def organisme(
    identifiant: str, nom: str, *,
    mission: str | None = None, etat: str = "ACTIF",
    famille: str = "organisation_administrative_etat",
    nature: str = "PUBLIEE",
    capacite: str | None = None,
):
    return {
        "id": f"FRONTIERE-INST-{identifiant}",
        "nom_officiel": nom,
        "etat": etat,
        "famille": famille,
        "type_institutionnel": "Service d'essai",
        "observe_le": "2026-10-08",
        "aliases": [],
        "missions": (
            [{"texte": mission, "source_id": "dila_roae", "nature": nature}]
            if mission else []
        ),
        "capacites": (
            [{"texte": capacite, "source_id": "dila_roae", "nature": "PUBLIEE"}]
            if capacite else []
        ),
        "provenance": [{
            "source_id": "dila_roae",
            "url": "https://www.data.gouv.fr/datasets/donnees-de-test/",
            "collecte_le": "2026-10-08",
            "identifiant_source": identifiant,
            "empreinte": "0" * 64,
        }],
    }


def construire_fichiers(tmp_path: Path):
    repertoire = tmp_path / "entites"
    shard = repertoire / "roae"
    shard.mkdir(parents=True)
    groupes = [
        organisme("A", "Service des analyses", mission="Analyse les eaux par chimie analytique."),
        organisme("B", "Laboratoire de chimie analytique", mission="Accueille les visiteurs."),
        organisme("C", "Service documentaire", mission="Chimie analytique avancée.", nature="ANALYTIQUE"),
        organisme("D", "Ancienne unité", mission="Chimie analytique des eaux.", etat="SUPPRIME"),
        organisme("E", "Institut des mesures", capacite="Spectrométrie de masse."),
    ]
    p = shard / "roae_00.jsonl"
    p.write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in groupes),
        encoding="utf-8",
    )
    return repertoire, p, groupes


def test_termes_francais_normalises_et_requete_sure():
    assert normaliser("Œuvres, chimie ANALYTIQUE et spectrométrie") == [
        "oeuvres", "chimie", "analytique", "et", "spectrometrie",
    ]
    assert termes_recherche("Compétences en chimie analytique") == ["chimie", "analytique"]
    assert termes_recherche('"chimie" OR 1=1') == ["chimie", "or", "1"]
    assert correspondances("chimie analytique", ["analytique", "eaux"]) == ["analytique"]
    with pytest.raises(ValueError, match="distinctif"):
        termes_recherche("de la recherche publique")
    with pytest.raises(ValueError, match="maximum"):
        termes_recherche("alpha beta gamma delta epsilon zeta eta theta iota kappa lambda")


def test_mission_analytique_et_capacite_sans_source_ne_sont_pas_indexees():
    e = organisme("F", "Laboratoire témoin", mission="Analyse nucléaire", nature="ANALYTIQUE")
    e["capacites"].append({"texte": "Spectrométrie", "nature": "PUBLIEE"})
    assert faits_publies(e, "missions") == []
    assert faits_publies(e, "capacites") == []
    assert preparer_entite(e, "fictif")["mission_index"] == ""


def test_recherche_distingue_mission_nom_et_disponibilite(tmp_path):
    repertoire, _, _ = construire_fichiers(tmp_path)
    index = tmp_path / "index.sqlite3"
    rapport = construire_index(repertoire, index)
    assert rapport["version_schema"] == VERSION_INDEX
    assert rapport["nombre_entites"] == 5
    assert rapport["nombre_missions_publiees"] == 3
    assert rapport["nombre_capacites_explicitement_publiees"] == 1
    with ouvrir_index(index) as db:
        assert verifier_sources(db, repertoire)["conforme"]
        bilan = chercher(db, "compétences en chimie analytique", limite=10)
    trouves = bilan["correspondances_aux_missions_ou_capacites_publiees"]
    noms = bilan["correspondances_de_nom_uniquement"]
    assert [x["identifiant"] for x in trouves] == ["FRONTIERE-INST-A"]
    assert [x["identifiant"] for x in noms] == ["FRONTIERE-INST-B"]
    assert "FRONTIERE-INST-C" not in str(bilan)
    assert "FRONTIERE-INST-D" not in str(bilan)
    assert trouves[0]["type_correspondance"] == "mission_publiee"
    assert trouves[0]["mots_retrouves_dans_les_missions"] == ["chimie", "analytique"]
    assert trouves[0]["passages_publies"][0]["texte"] == "Analyse les eaux par chimie analytique."
    assert trouves[0]["provenance_notice"][0]["source_id"] == "dila_roae"
    assert trouves[0]["disponibilite"] == "INCONNUE"
    assert trouves[0]["mobilisabilite"] == "NON_ETABLIE"
    assert bilan["empreinte_sha256_sources_indexees"] == rapport["empreinte_sha256_sources"]


def test_capacite_publiee_n_est_pas_pretendue_mobilisable(tmp_path):
    repertoire, _, _ = construire_fichiers(tmp_path)
    index = tmp_path / "index.sqlite3"
    construire_index(repertoire, index)
    with ouvrir_index(index) as db:
        resultats = chercher(db, "spectrométrie de masse")
        filtres = chercher(db, "spectrométrie de masse", famille="administration_territoriale")
    assert [x["identifiant"] for x in resultats["correspondances_aux_missions_ou_capacites_publiees"]] == [
        "FRONTIERE-INST-E"
    ]
    r = resultats["correspondances_aux_missions_ou_capacites_publiees"][0]
    assert r["type_correspondance"] == "capacite_publiee"
    assert r["mobilisabilite"] == "NON_ETABLIE"
    assert filtres["correspondances_aux_missions_ou_capacites_publiees"] == []


def test_index_perime_et_hash_des_sources_detectes(tmp_path):
    repertoire, chemin, _ = construire_fichiers(tmp_path)
    index = tmp_path / "index.sqlite3"
    construire_index(repertoire, index)
    with ouvrir_index(index) as db:
        assert verifier_sources(db, repertoire)["conforme"]
    chemin.write_text(chemin.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with ouvrir_index(index) as db:
        control = verifier_sources(db, repertoire)
    assert control["conforme"] is False
    assert control["fichiers_modifies"] == ["roae/roae_00.jsonl"]
    construire_index(repertoire, index)
    (repertoire / "roae" / "roae_01.jsonl").write_text("", encoding="utf-8")
    with ouvrir_index(index) as db:
        control = verifier_sources(db, repertoire)
    assert control["fichiers_ajoutes"] == ["roae/roae_01.jsonl"]


def test_collision_identifiant_abandonne_reconstruction_sans_detruire_ancien_index(tmp_path):
    repertoire, _, groupes = construire_fichiers(tmp_path)
    index = tmp_path / "index.sqlite3"
    construire_index(repertoire, index)
    anciennes_donnees = index.read_bytes()
    p = repertoire / "roae" / "roae_01.jsonl"
    p.write_text(json.dumps(copy.deepcopy(groupes[0])) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="dupliqué"):
        construire_index(repertoire, index)
    assert index.read_bytes() == anciennes_donnees


def test_rejet_entree_sans_provenance_et_lecture_non_mutante(tmp_path):
    repertoire, p, groupes = construire_fichiers(tmp_path)
    index = tmp_path / "index.sqlite3"
    e = copy.deepcopy(groupes[0])
    e["provenance"] = []
    p.write_text(json.dumps(e) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="provenance"):
        construire_index(repertoire, index)
    assert not index.exists()


def test_validation_parametres_et_absence_de_sources(tmp_path):
    with pytest.raises(ValueError, match="Aucun fichier"):
        fichiers_sources(tmp_path)
    repertoire, _, _ = construire_fichiers(tmp_path)
    index = tmp_path / "index.sqlite3"
    construire_index(repertoire, index)
    with ouvrir_index(index) as db:
        with pytest.raises(ValueError, match="limite"):
            chercher(db, "chimie", limite=0)
        with pytest.raises(ValueError, match="Famille"):
            chercher(db, "chimie", famille="' OR 1=1")


def test_echantillons_reels_des_deux_familles_sont_indexables(tmp_path):
    """Vérifie la compatibilité des schémas JSONL sans indexer tout le corpus."""
    original = Path(__file__).resolve().parents[1] / "institutionnel" / "entites"
    synthese = tmp_path / "extraits"
    pourcentage = 0
    for categorie in ("roae", "locales"):
        fragments = sorted((original / categorie).glob("*.jsonl"))
        assert fragments, f"Absence des notices de la famille {categorie}."
        entree = fragments[0]
        with entree.open("rb") as f:
            lignes = []
            for ligne in f:
                if ligne.strip():
                    lignes.append(ligne)
                if len(lignes) == 2:
                    break
        assert len(lignes) == 2
        sortie = synthese / categorie
        sortie.mkdir(parents=True)
        (sortie / entree.name).write_bytes(b"".join(lignes))
        pourcentage += len(lignes)
    index = tmp_path / "echantillon.sqlite3"
    resultat = construire_index(synthese, index)
    assert resultat["nombre_entites"] == pourcentage == 4
    with ouvrir_index(index) as db:
        assert verifier_sources(db, synthese)["conforme"]
        assert db.execute("SELECT COUNT(*) FROM organismes").fetchone()[0] == 4
