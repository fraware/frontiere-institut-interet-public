import hashlib
import json
from pathlib import Path

import pytest
from typing import Iterator

RACINE = Path(__file__).resolve().parents[1]
INSTITUTIONNEL = RACINE / "institutionnel"
MANIFESTE = INSTITUTIONNEL / "instantanes" / "cog_manifest.json"

# Le snapshot COG est produit par le workflow d’ingestion réel. Avant le premier
# amorçage de main, la CI générale vérifie le code et les tests unitaires, tandis
# que le workflow COG exécute ces contrôles de snapshot après l’ingestion.
pytestmark = pytest.mark.skipif(
    not MANIFESTE.is_file(),
    reason="snapshot COG absent avant amorçage; vérifié dans le workflow d’ingestion",
)


def lire_json(chemin: Path) -> dict:
    return json.loads(chemin.read_text(encoding="utf-8"))


def iter_jsonl(chemin: Path) -> Iterator[dict]:
    with chemin.open("r", encoding="utf-8") as fichier:
        for ligne in fichier:
            if ligne.strip():
                yield json.loads(ligne)


def manifeste() -> dict:
    return lire_json(MANIFESTE)


def verifier_partition(entree: dict) -> int:
    chemin = RACINE / entree["fichier"]
    assert chemin.is_file(), entree["fichier"]
    brut = chemin.read_bytes()
    assert hashlib.sha256(brut).hexdigest() == entree["sha256"]
    assert len(brut) == entree["octets"]
    nombre = sum(1 for _ in iter_jsonl(chemin))
    assert nombre == entree["nombre"]
    return nombre


def iter_territoires() -> Iterator[dict]:
    for entree in manifeste()["partitions_territoires"]:
        yield from iter_jsonl(RACINE / entree["fichier"])


def iter_relations() -> Iterator[dict]:
    for entree in manifeste()["partitions_relations"]:
        yield from iter_jsonl(RACINE / entree["fichier"])


def test_snapshot_cog_correspond_au_manifeste():
    m = manifeste()
    stats = lire_json(INSTITUTIONNEL / "statistiques_cog.json")
    nt = sum(verifier_partition(x) for x in m["partitions_territoires"])
    nr = sum(verifier_partition(x) for x in m["partitions_relations"])
    assert nt == m["nombre_territoires"] == stats["nombre_territoires"]
    assert nr == m["nombre_relations"] == stats["nombre_relations"]
    assert m["millesime"] == "2026"
    assert m["reference_le"] == "2026-01-01"
    assert m["empreinte_dependance_annuaire"]


def test_identites_territoriales_sont_uniques_et_sourcees():
    ids = set()
    types = {}
    for t in iter_territoires():
        assert t["id"] not in ids
        ids.add(t["id"])
        assert t["id"].startswith("FRONTIERE-TERR-COG-")
        assert t["provenance"][0]["source_id"] == "insee_cog"
        assert t["provenance"][0]["empreinte"]
        assert t["source_insee"]
        types[t["type_territoire"]] = types.get(t["type_territoire"], 0) + 1
    assert 30_000 <= types.get("COM", 0) <= 40_000
    assert types.get("DEP", 0) >= 100
    assert types.get("REG", 0) >= 18
    assert types.get("CTCD", 0) == 0
    assert len(ids) >= 35_000


def test_relations_territoriales_pointent_vers_des_noeuds_connus():
    ids = {t["id"] for t in iter_territoires()}
    relations = set()
    for r in iter_relations():
        assert r["id"] not in relations
        relations.add(r["id"])
        assert r["source_territoire"] in ids
        assert r["cible_territoire"] in ids
        assert r["type_relation"] in {"APPARTIENT_A", "PARTIE_DE", "A_POUR_CHEF_LIEU"}
        assert r["provenance"]


def test_resolution_annuaire_est_mesuree_sans_rapprochement_par_nom():
    rapport = lire_json(INSTITUTIONNEL / "resolution_annuaire_cog.json")
    total = rapport["references_codes_insee"]
    assert total > 80_000
    assert rapport["resolues"] + rapport["ambigues"] + rapport["absentes"] == total
    assert rapport["taux_resolution"] is not None
    assert rapport["taux_resolution"] >= 0.95
    assert "aucune résolution par nom" in rapport["doctrine"]


def test_anomalies_cog_sont_coherentes_avec_les_statistiques():
    anomalies = lire_json(INSTITUTIONNEL / "anomalies_cog.json")
    stats = lire_json(INSTITUTIONNEL / "statistiques_cog.json")
    assert anomalies["nombre"] == len(anomalies["anomalies"])
    assert anomalies["nombre"] == stats["anomalies_relations"]