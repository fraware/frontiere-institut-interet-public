import hashlib
import json
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
MANIFESTE = RACINE / "institutionnel" / "instantanes" / "cog_manifest.json"
STATISTIQUES = RACINE / "institutionnel" / "statistiques_cog.json"
ANOMALIES = RACINE / "institutionnel" / "anomalies_cog.json"
RESOLUTION = RACINE / "institutionnel" / "resolution_territoires_dila_cog.json"


if not MANIFESTE.exists():
    pytest.skip(
        "Le snapshot COG n'est pas encore matérialisé sur cette branche.",
        allow_module_level=True,
    )


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fichier:
        for bloc in iter(lambda: fichier.read(1024 * 1024), b""):
            h.update(bloc)
    return h.hexdigest()


def lire_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def lignes_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as fichier:
        for ligne in fichier:
            if ligne.strip():
                yield json.loads(ligne)


def test_manifeste_et_partitions_sont_integralement_verifiables():
    manifeste = lire_json(MANIFESTE)

    assert manifeste["source_id"] == "insee_cog"
    assert manifeste["millesime"] == "2026"
    assert manifeste["version_transformation"] == "1.0"

    archive = RACINE / "institutionnel" / "archives" / "cog" / manifeste["nom_archive"]
    assert archive.exists()
    assert sha256(archive) == manifeste["sha256_archive"]

    for groupe in ("partitions_territoires", "partitions_relations"):
        total = 0
        for entree in manifeste[groupe]:
            path = RACINE / entree["fichier"]
            assert path.exists()
            assert path.stat().st_size == entree["octets"]
            assert sha256(path) == entree["sha256"]
            assert sum(1 for _ in lignes_jsonl(path)) == entree["nombre"]
            total += entree["nombre"]
        assert total > 0

    for cle in ("evenements_communes", "historique_communes"):
        entree = manifeste[cle]
        path = RACINE / entree["fichier"]
        assert path.exists()
        assert path.stat().st_size == entree["octets"]
        assert sha256(path) == entree["sha256"]
        assert sum(1 for _ in lignes_jsonl(path)) == entree["nombre"]


def test_territoires_et_relations_ont_des_identites_uniques_et_resolues():
    manifeste = lire_json(MANIFESTE)
    ids = set()
    territoires = {}

    for entree in manifeste["partitions_territoires"]:
        for objet in lignes_jsonl(RACINE / entree["fichier"]):
            assert objet["id"] not in ids
            ids.add(objet["id"])
            territoires[objet["id"]] = objet
            assert objet["provenance"][0]["source_id"] == "insee_cog"
            assert objet["source_insee"]

    relation_ids = set()
    for entree in manifeste["partitions_relations"]:
        for relation in lignes_jsonl(RACINE / entree["fichier"]):
            assert relation["id"] not in relation_ids
            relation_ids.add(relation["id"])
            assert relation["source_territoire"] in ids
            assert relation["cible_territoire"] in ids
            assert relation["type_relation"] in {"APPARTIENT_A", "COMMUNE_PARENTE"}

    assert "FRONTIERE-TERR-COG-COM-75056" in territoires
    assert territoires["FRONTIERE-TERR-COG-COM-75056"]["nom_officiel"] == "Paris"


def test_statistiques_coherentes_avec_le_manifeste():
    manifeste = lire_json(MANIFESTE)
    stats = lire_json(STATISTIQUES)
    anomalies = lire_json(ANOMALIES)

    assert stats["nombre_territoires"] == sum(
        x["nombre"] for x in manifeste["partitions_territoires"]
    )
    assert stats["nombre_relations_territoriales"] == sum(
        x["nombre"] for x in manifeste["partitions_relations"]
    )
    assert stats["nombre_evenements_communes"] == manifeste["evenements_communes"]["nombre"]
    assert stats["nombre_lignes_historique_communes"] == manifeste["historique_communes"]["nombre"]
    assert stats["anomalies"] == anomalies["nombre_anomalies"]
    assert stats["integrite"]["extremites_relations_resolues"] is True
    assert stats["integrite"]["communes_actives_dans_historique"] is True


def test_resolution_dila_cog_est_rattachee_aux_deux_snapshots():
    rapport = lire_json(RESOLUTION)

    assert rapport["dependances"]["cog_millesime"] == "2026"
    assert rapport["dependances"]["cog_sha256_archive"] == lire_json(MANIFESTE)[
        "sha256_archive"
    ]
    assert rapport["nombre_references_territoriales"] > 0
    assert rapport["nombre_codes_distincts"] > 0

    resultats = rapport["resultats"]
    assert resultats.get("codes_resolus_courants", 0) > 0

    for entree in rapport["codes"]:
        if entree["statut"] == "RESOLU_COURANT":
            assert entree["territoire_id"].startswith("FRONTIERE-TERR-COG-")
