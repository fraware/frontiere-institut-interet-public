"""Tests synthétiques du moteur national : intégrité, versions, recherche et atomicité."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from scripts.indexer_recrutements_nationaux_sqlite import (
    IndexRecrutementsInvalide, construire, rechercher, bilan,
    verifier_manifeste, version_exacte
)
from scripts.preparer_relecture_besoins_explicites import PARTITIONS


def variante(reference: str, titre: str, date_pub: str | None,
             *, employeur: str = "Université publique", specialisation: str = "") -> dict:
    d = {
        "reference": reference,
        "intitule": titre,
        "organisme": None,
        "employeur": employeur,
        "publication_debut": date_pub,
        "premiere_publication": "2026-08-01",
        "date_vacance": "2026-09-01",
        "publication_fin": "2026-12-01",
        "metier": "Ingénierie",
        "specialisation": specialisation,
        "competences_attendues": "Contact contact@example.fr",
        "champs_tronques": [],
    }
    d["cle_enregistrement"] = hashlib.sha256(json.dumps(
        d, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    return d


def source_fictive(racine: Path, lignes: list[dict]) -> None:
    dossier = racine / "institutionnel/besoins_publics"
    lots = dossier / "offres_postes"
    lots.mkdir(parents=True, exist_ok=True)
    donnees = {nom: [] for nom in PARTITIONS}
    for d in lignes:
        first = hashlib.sha256(d["reference"].encode("utf-8")).hexdigest()[0]
        fichier = f"lot_{int(first, 16):02x}.jsonl"
        donnees[fichier].append(d)
    empreintes = {}
    for nom in PARTITIONS:
        raw = b"".join((json.dumps(x, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")) + "\n").encode("utf-8")
                       for x in donnees[nom])
        (lots / nom).write_bytes(raw)
        empreintes[nom] = hashlib.sha256(raw).hexdigest()
    refs = {x["reference"] for x in lignes}
    nversions = {r: sum(1 for x in lignes if x["reference"] == r) for r in refs}
    manifest = {
        "version": "emplois-publics-extraits-v1",
        "offres_distinctes": len(lignes),
        "references_distinctes": len(refs),
        "references_avec_plusieurs_variantes": sum(n > 1 for n in nversions.values()),
        "variantes_supplementaires_de_reference": len(lignes) - len(refs),
        "sha256_csv": "b" * 64,
        "empreintes_partitions": empreintes,
    }
    (dossier / "manifest_offres_postes.json").write_text(
        json.dumps(manifest, sort_keys=True), encoding="utf-8")


def corpus() -> list[dict]:
    return [
        variante("OFFRE-042", "Ingénieur quantique", "2026-09-12",
                 specialisation="Physique appliquée"),
        variante("OFFRE-042", "Ingénieur quantique senior", "2026-10-12",
                 specialisation="Physique appliquée"),
        variante("OFFRE-051", "Statisticien épidémiologie", "12/09/2026",
                 employeur="Hôpital public", specialisation="Données médicales"),
        variante("OFFRE-062", "Agent secrétariat", "2026-09-14",
                 employeur="Administration publique"),
        variante("OFFRE-073", "Technicien cyber sécurité", None,
                 employeur="Ministère public", specialisation="Sécurité informatique"),
        variante("OFFRE-084", "Envoyer à contact@example.fr", "2026-09-10",
                 employeur="Établissement fictif"),
    ]


def test_integralite_nationale_des_variantes_et_index_fts5(tmp_path):
    racine = tmp_path / "depot"
    source_fictive(racine, corpus())
    base = tmp_path / "index.sqlite3"
    r = construire(racine, base)
    assert r["variantes_indexees"] == 6
    assert r["references_distinctes"] == 5
    assert r["references_multivariantes"] == 1
    assert r["partitions_verifiees"] == 16
    assert r["couverture_nationale_demontree"] is False
    assert not r["recrutements_actuels_confirmes"]
    assert bilan(base)["references_distinctes"] == 5

    quantique = rechercher(base, expression="quantique")
    assert len(quantique["resultats"]) == 1
    q = quantique["resultats"][0]
    assert q["reference"] == "OFFRE-042"
    assert q["titre"] == "Ingénieur quantique senior"
    assert q["variantes_correspondantes"] == 2
    assert q["variantes_archivees"] == 2
    assert q["date_index"] == "2026-10-12"
    assert q["nature_date"] == "publication_debut"
    assert len(q["sha256_ligne"]) == 64
    assert q["chemin_source"].startswith("institutionnel/besoins_publics/offres_postes/")
    assert q["ligne_source"] >= 1
    assert rechercher(base, expression="epidemiologie")["resultats"][0][
        "reference"] == "OFFRE-051"
    assert rechercher(base, expression="quantique", depuis="2026-10-01")[
        "resultats"][0]["variantes_correspondantes"] == 1
    assert rechercher(base, expression="quantique", jusqua="2026-08-01")[
        "resultats"] == []
    assert rechercher(base, reference="OFFRE-042")["resultats"][0][
        "variantes_archivees"] == 2
    assert rechercher(base, expression="quantique", reference="OFFRE-062")[
        "resultats"] == []
    assert rechercher(base, expression="cyber")["resultats"][0][
        "nature_date"] == "premiere_publication"
    assert rechercher(base, reference="OFFRE-084")["resultats"][0]["titre"] == ""
    assert rechercher(base, expression="contact@example.fr")["resultats"] == []


def test_operateurs_de_recherche_resten_toutes_litteraux(tmp_path):
    racine = tmp_path / "depot"
    source_fictive(racine, corpus())
    base = tmp_path / "index.db"
    construire(racine, base)
    assert rechercher(base, expression='quantique" OR secrétariat')["resultats"] == []
    assert rechercher(base, expression="quantique")["resultats"][0][
        "reference"] == "OFFRE-042"
    assert rechercher(base, expression="ingénieur quantique")["resultats"][0][
        "reference"] == "OFFRE-042"
    assert rechercher(base, expression="quantique", limite=1, decalage=1)[
        "resultats"] == []
    with pytest.raises(IndexRecrutementsInvalide):
        rechercher(base, expression=" ")
    with pytest.raises(IndexRecrutementsInvalide):
        rechercher(base, expression="quantique", limite=0)
    with pytest.raises(IndexRecrutementsInvalide):
        rechercher(base, expression="quantique", decalage=10001)
    with pytest.raises(IndexRecrutementsInvalide):
        rechercher(base, reference="OFFRE-042", depuis="2026-10-02",
                  jusqua="2026-09-01")
    with pytest.raises(IndexRecrutementsInvalide):
        rechercher(base, expression="quantique", depuis="2026-02-30")
    with pytest.raises(IndexRecrutementsInvalide):
        rechercher(base, expression="quantique; DROP TABLE offres")
    assert bilan(base)["variantes_indexees"] == 6


def test_rejet_inconditionnel_de_toute_corruption_de_variantes(tmp_path):
    racine = tmp_path / "depot"
    doc = corpus()
    source_fictive(racine, doc)
    base = tmp_path / "index.db"
    construire(racine, base)
    ancien = base.read_bytes()
    # Modifier une ligne du corpus et recalculer l'empreinte du lot
    # ne suffit pas à fabriquer une variante valable : sa clé canonique
    # doit encore correspondre à son contenu.
    faux = deepcopy(doc)
    faux[0]["intitule"] = "Texte falsifié"
    source_fictive(racine, faux)
    with pytest.raises(IndexRecrutementsInvalide, match="Document invalide"):
        construire(racine, base, remplacer=True)
    assert base.read_bytes() == ancien
    assert rechercher(base, expression="quantique")["resultats"]


def test_un_lot_modifie_sans_manifeste_empeche_la_publication(tmp_path):
    racine = tmp_path / "depot"
    source_fictive(racine, corpus())
    path = racine / "institutionnel/besoins_publics/offres_postes/lot_00.jsonl"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(IndexRecrutementsInvalide, match="Ligne source"):
        construire(racine, tmp_path / "index.sqlite3")
    assert not (tmp_path / "index.sqlite3").exists()


def test_mauvaise_partition_memes_hachages_sources_refuses(tmp_path):
    racine = tmp_path / "depot"
    lignes = corpus()
    source_fictive(racine, lignes)
    path = racine / "institutionnel/besoins_publics/manifest_offres_postes.json"
    m = json.loads(path.read_text(encoding="utf-8"))
    ancienne = next(x for x in PARTITIONS if
                    (racine / "institutionnel/besoins_publics/offres_postes" / x)
                    .read_bytes())
    autre = next(x for x in PARTITIONS if x != ancienne)
    dossier = racine / "institutionnel/besoins_publics/offres_postes"
    d = (dossier / ancienne).read_bytes()
    (dossier / ancienne).write_bytes(b"")
    (dossier / autre).write_bytes((dossier / autre).read_bytes() + d)
    for nom in PARTITIONS:
        m["empreintes_partitions"][nom] = hashlib.sha256(
            (dossier / nom).read_bytes()).hexdigest()
    path.write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(IndexRecrutementsInvalide, match="mauvaise partition"):
        construire(racine, tmp_path / "base.sqlite3")


def test_manifeste_non_coherent_rejete(tmp_path):
    racine = tmp_path / "depot"
    source_fictive(racine, corpus())
    path = racine / "institutionnel/besoins_publics/manifest_offres_postes.json"
    m = json.loads(path.read_text(encoding="utf-8"))
    m["offres_distinctes"] = 9
    with pytest.raises(IndexRecrutementsInvalide):
        verifier_manifeste(json.dumps(m).encode())
    m["offres_distinctes"] = 6
    m["references_avec_plusieurs_variantes"] = 3
    path.write_text(json.dumps(m))
    with pytest.raises(IndexRecrutementsInvalide, match="Nombre de références"):
        construire(racine, tmp_path / "index.sqlite3")


def test_dossier_source_et_chemin_de_base_separes(tmp_path):
    racine = tmp_path / "depot"
    source_fictive(racine, corpus())
    with pytest.raises(IndexRecrutementsInvalide, match="hors du dépôt"):
        construire(racine, racine / "index.sqlite3")
    with pytest.raises(IndexRecrutementsInvalide):
        rechercher(tmp_path / "absent.sqlite3", expression="quantique")
