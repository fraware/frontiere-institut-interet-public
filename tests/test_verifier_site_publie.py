"""Contrôles synthétiques des fichiers réellement servis par un site statique."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.verifier_site_publie import EchecPublication, controler_publication

COMMIT = "a" * 40


def octets(obj) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def site_fictif(racine: Path):
    """Trois sources, une partition par source et même révision Git."""
    lignes = [
        {"source": "boamp", "id": "26-1", "date": "2026-10-14", "titre": "Radar"},
        {"source": "emplois", "id": "EMP-2", "date": "2026-10-13", "titre": "Ingénieur"},
        {"source": "decp", "id": "12345678901234/M", "date": "2026-10-12", "titre": "Marché"},
    ]
    principal = {
        "portee": "echantillon_documentaire_non_exhaustif",
        "recherche_temps_reel": False,
        "revision_sources": COMMIT,
        "documents": lignes,
        "sources": {s: {"retenus": 1} for s in ("boamp", "emplois", "decp")},
    }
    manifeste = {
        "portee": "extrait_etendu_non_exhaustif",
        "mise_a_jour_temps_reel": False,
        "revision_sources": COMMIT,
        "selection": {
            "couverture_nationale_etablie": False,
            "sources": [
                {"source": s, "documents_indexes": 1}
                for s in ("boamp", "emplois", "decp")
            ]
        },
        "partitions": [],
    }
    distant = {
        "recherche-index.json": octets(principal),
        "metadonnees-index.json": octets({"revision_sources": COMMIT}),
    }
    for d in lignes:
        nom = f"part-{d['source']}-2026-001.json"
        brut = octets([{**d, "qualification": {"nature": "document"}}])
        distant["partitions/" + nom] = brut
        manifeste["partitions"].append({
            "fichier": nom,
            "source": d["source"],
            "annee": "2026",
            "documents": 1,
            "octets": len(brut),
            "sha256": hashlib.sha256(brut).hexdigest(),
        })
    distant["partitions/manifeste.json"] = octets(manifeste)
    for nom in ("recherche-index.json", "partitions/manifeste.json"):
        p = racine / "site_frontiere" / nom
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(distant[nom])

    def lire(chemin, limite):
        raw = distant[chemin]
        assert len(raw) <= limite
        return raw
    return distant, lire


def test_site_actuel_et_controle_integral(tmp_path):
    _, lire = site_fictif(tmp_path)
    bilan = controler_publication(lire, attendu=COMMIT, racine=tmp_path)
    assert bilan["statut"] == "a_jour_et_concordant"
    assert bilan["integrite_publique_verifiee"] is True
    assert bilan["partitions_lues"] == 3
    assert bilan["sources"]["decp"]["partitions"] == 1


def test_site_sur_revision_distincte_est_valide_mais_non_actuel(tmp_path):
    _, lire = site_fictif(tmp_path)
    bilan = controler_publication(lire, attendu="b" * 40, racine=tmp_path)
    assert bilan["statut"] == "revision_distincte"
    assert bilan["integrite_publique_verifiee"] is True
    assert bilan["site_a_jour"] is False


def test_refus_partition_dont_les_octets_ont_change(tmp_path):
    distant, lire = site_fictif(tmp_path)
    distant["partitions/part-boamp-2026-001.json"] += b" "
    with pytest.raises(EchecPublication, match="Partition distante divergente"):
        controler_publication(lire, attendu=COMMIT, racine=tmp_path)


def test_refus_deux_manifestes_de_revisions_differentes(tmp_path):
    distant, lire = site_fictif(tmp_path)
    distant["metadonnees-index.json"] = octets({"revision_sources": "b" * 40})
    with pytest.raises(EchecPublication, match="Révision contradictoire"):
        controler_publication(lire, attendu=COMMIT, racine=tmp_path)


def test_refus_meme_revision_avec_octets_incompatibles(tmp_path):
    _, lire = site_fictif(tmp_path)
    p = tmp_path / "site_frontiere/recherche-index.json"
    p.write_bytes(p.read_bytes() + b" ")
    with pytest.raises(EchecPublication, match="octets publiés divergents"):
        controler_publication(lire, attendu=COMMIT, racine=tmp_path)


def test_site_sans_attestation_de_revision_ne_dit_pas_actuel(tmp_path):
    distant, lire = site_fictif(tmp_path)
    for chemin in ("recherche-index.json", "partitions/manifeste.json",
                   "metadonnees-index.json"):
        objet = json.loads(distant[chemin])
        objet["revision_sources"] = None
        distant[chemin] = octets(objet)
    bilan = controler_publication(lire, attendu=COMMIT, racine=tmp_path)
    assert bilan["statut"] == "revision_non_verifiable"
    assert bilan["site_a_jour"] is False

def test_entree_module_python_chargeable_depuis_racine():
    racine = Path(__file__).resolve().parents[1]
    resultat = subprocess.run(
        [sys.executable, "-m", "scripts.verifier_site_publie", "--help"],
        cwd=racine, check=False, capture_output=True, text=True, timeout=15,
    )
    assert resultat.returncode == 0, resultat.stderr
    assert "--rapport" in resultat.stdout
