"""Tests sans réseau : huit dossiers, filiation JSONL et absence d'inférence.

Les lignes sont fictives ; le contrôle sur les véritables archives figure
dans la procédure d'intégration.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.constituer_enquetes_institutionnelles import (
    constituer, verifier_cibles, classer_competences, EchecPreuve,
)
from scripts.preparer_relecture_besoins_explicites import candidat, PARTITIONS


def preparer_fixtures(racine: Path, cibles: dict) -> None:
    directory = racine / "institutionnel/besoins_publics/offres_postes"
    directory.mkdir(parents=True)
    by_file: dict[str, list[dict]] = {p: [] for p in PARTITIONS}
    for i, item in enumerate(cibles["items"]):
        nom = item["partition"].rsplit("/", 1)[-1]
        source = {
            "reference": item["reference"],
            "intitule": "Poste public fictif " + str(i),
            "organisme": "Établissement fictif",
            "publication_debut": item["date_publication_archives"],
            "publication_fin": "2026-12-31",
            "date_vacance": "2026-09-01",
            "competences_attendues": None if i % 3 == 0 else
                "Méthodes expérimentales décrites" if i % 3 == 1 else
                "Consulter l'annonce détaillée, objectifs et modalités",
            "metier": "Métier fictif",
            "statut_poste": "Vacant à la publication",
            "champs_tronques": ["competences_attendues"] if i == 2 else [],
            "cle_enregistrement": hashlib.sha256(item["reference"].encode()).hexdigest()
        }
        by_file[nom].append((item, source))
    sha_lots = {}
    for nom, records in by_file.items():
        raw = b""
        for numero, (item, source) in enumerate(records, 1):
            line = (json.dumps(source, ensure_ascii=False, sort_keys=True) + "\n").encode()
            raw += line
            item["ligne"] = numero
            item["sha256_ligne"] = hashlib.sha256(line).hexdigest()
        (directory / nom).write_bytes(raw)
        sha_lots[nom] = hashlib.sha256(raw).hexdigest()
    manifest = {
        "version": "emplois-publics-extraits-v1",
        "empreintes_partitions": sha_lots,
        "offres_distinctes": len(cibles["items"])
    }
    (racine / "institutionnel/besoins_publics/manifest_offres_postes.json").write_text(
        json.dumps(manifest), encoding="utf-8")
    cfg = racine / "evaluation/enquetes_institutionnelles_8_cibles_v1.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps(cibles, ensure_ascii=False), encoding="utf-8")


def cibles_reelles() -> dict:
    return json.loads(Path("evaluation/enquetes_institutionnelles_8_cibles_v1.json")
                      .read_text(encoding="utf-8"))


def test_huit_preuves_sans_besoin_affirme(tmp_path):
    cfg = cibles_reelles()
    preparer_fixtures(tmp_path, cfg)
    r = constituer(tmp_path)
    assert r["references_examinees"] == 8
    assert r["partitions_integralement_verifiees"] == 16
    assert r["variantes_lues"] == 8
    assert r["episodes_de_deficit_de_capacite_confirmes"] == 0
    assert r["entretiens_realises"] == 0
    assert r["recrutements_actuels_confirmes"] == 0
    assert r["validations_independantes_realisees"] == 0
    assert sum(r["compteurs_champ_competences"].values()) == 8
    assert all(x["besoin_non_satisfait"] == "non_etabli"
               and x["verification_humaine"] == "a_realiser"
               and x["recrutement_pourvu"] == "inconnu"
               and x["competences_champ_source"]["citation_publiee"] is False
               for x in r["dossiers"])
    assert r == constituer(tmp_path)


def test_rejeter_une_preuve_de_ligne_modifiee(tmp_path):
    cfg = cibles_reelles()
    preparer_fixtures(tmp_path, cfg)
    cible = cfg["items"][0]
    fichier = tmp_path / cible["partition"]
    fichier.write_bytes(fichier.read_bytes().replace(b"fictif", b"fIctif", 1))
    with pytest.raises(EchecPreuve, match="Empreinte de ligne"):
        constituer(tmp_path)


def test_refuser_un_lot_modifie_meme_non_selectionne(tmp_path):
    cfg = cibles_reelles()
    preparer_fixtures(tmp_path, cfg)
    fichier = tmp_path / "institutionnel/besoins_publics/offres_postes/lot_00.jsonl"
    fichier.write_bytes(fichier.read_bytes() + b'{"reference":"offre-invasive"}\n')
    with pytest.raises(EchecPreuve, match="Partition source altérée"):
        constituer(tmp_path)


@pytest.mark.parametrize("alt", [
    lambda c: c.update({"besoins_non_satisfaits_confirmes": 1}),
    lambda c: c.update({"contacts_institutionnels_realises": 1}),
    lambda c: c["items"][0]["preuve_web"].update({"contrat_pourvu": "oui"}),
    lambda c: c["items"][0]["preuve_web"].update({"statut_recrutement_actuel": "vacant"}),
    lambda c: c["items"][0]["preuve_web"].update({"url": "https://exemple.invalid/perso"}),
    lambda c: c["items"][0].update({"ligne": 0}),
    lambda c: c["items"][0].update({"sha256_ligne": "modifie"}),
    lambda c: c["items"][0].update({"reference": c["items"][1]["reference"]}),
    lambda c: c["items"].pop()
])
def test_refuser_une_conclusion_excessive_ou_une_identite_ambigue(alt):
    cfg = deepcopy(cibles_reelles())
    alt(cfg)
    with pytest.raises((EchecPreuve, KeyError)):
        verifier_cibles(cfg)


def test_absence_de_champ_competences_differe_d_un_champ_filtre():
    source = {
        "reference": "REF-1",
        "intitule": "Intitulé",
        "organisme": "Organisme",
        "publication_debut": "2026-10-15",
        "metier": "Recherche",
        "champs_tronques": [],
        "cle_enregistrement": "c" * 64,
        "competences_attendues": "a" * 350,
    }
    line = (json.dumps(source) + "\n").encode()
    projection = candidat(source, "f.jsonl", 1, line)
    assert classer_competences(source, projection)["statut_champ"] == (
        "champ_trop_long_ou_filtre")
    source["competences_attendues"] = ""
    assert classer_competences(source, projection)["statut_champ"] == "absent"
    source["champs_tronques"] = ["competences_attendues"]
    assert classer_competences(source, projection)["statut_champ"] == "tronque"
