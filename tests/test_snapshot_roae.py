import hashlib
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
INSTITUTIONNEL = RACINE / "institutionnel"


def lire_json(chemin: Path) -> dict:
    return json.loads(chemin.read_text(encoding="utf-8"))


def lire_jsonl(chemin: Path) -> list[dict]:
    return [
        json.loads(ligne)
        for ligne in chemin.read_text(encoding="utf-8").splitlines()
        if ligne.strip()
    ]


def verifier_partition(entree: dict) -> list[dict]:
    chemin = RACINE / entree["fichier"]
    assert chemin.is_file(), entree["fichier"]

    brut = chemin.read_bytes()
    assert hashlib.sha256(brut).hexdigest() == entree["sha256"]

    objets = [
        json.loads(ligne)
        for ligne in brut.decode("utf-8").splitlines()
        if ligne.strip()
    ]
    assert len(objets) == entree["nombre"]
    assert len(brut) == entree["octets"]
    return objets


def test_snapshot_roae_correspond_au_manifeste():
    manifeste = lire_json(INSTITUTIONNEL / "instantanes" / "roae_manifest.json")
    stats = lire_json(INSTITUTIONNEL / "statistiques_roae.json")
    anomalies = lire_json(INSTITUTIONNEL / "anomalies_roae.json")

    entites = []
    for entree in manifeste["partitions_entites"]:
        entites.extend(verifier_partition(entree))

    relations = []
    for entree in manifeste["partitions_relations"]:
        relations.extend(verifier_partition(entree))

    assert len(entites) == manifeste["nombre_services"]
    assert len(entites) == stats["nombre_entites_canoniques"]
    assert len(relations) == manifeste["nombre_relations"]
    assert len(relations) == stats["nombre_relations_hierarchiques"]
    assert (
        anomalies["nombre_anomalies_hierarchiques"]
        == stats["liens_hierarchiques_non_resolus"]
    )


def test_identites_et_relations_roae_sont_coherentes():
    manifeste = lire_json(INSTITUTIONNEL / "instantanes" / "roae_manifest.json")

    entites = []
    for entree in manifeste["partitions_entites"]:
        entites.extend(lire_jsonl(RACINE / entree["fichier"]))

    relations = []
    for entree in manifeste["partitions_relations"]:
        relations.extend(lire_jsonl(RACINE / entree["fichier"]))

    ids = [entite["id"] for entite in entites]
    assert len(ids) == len(set(ids))

    ids_entites = set(ids)
    ids_relations = [relation["id"] for relation in relations]
    assert len(ids_relations) == len(set(ids_relations))

    for relation in relations:
        assert relation["source_entite"] in ids_entites
        assert relation["cible_entite"] in ids_entites
        assert relation["type_relation"] == "DEPEND_DE"
        assert relation["provenance"]


def test_parent_principal_est_justifie_par_un_lien_service_fils():
    manifeste = lire_json(INSTITUTIONNEL / "instantanes" / "roae_manifest.json")
    stats = lire_json(INSTITUTIONNEL / "statistiques_roae.json")

    entites = []
    for entree in manifeste["partitions_entites"]:
        entites.extend(lire_jsonl(RACINE / entree["fichier"]))

    relations = []
    for entree in manifeste["partitions_relations"]:
        relations.extend(lire_jsonl(RACINE / entree["fichier"]))

    liens_directs = {
        (relation["source_entite"], relation["cible_entite"])
        for relation in relations
        if relation.get("qualificatifs", {}).get("type_hierarchie_dila") == "Service Fils"
    }

    avec_parent = 0
    for entite in entites:
        parent = entite.get("parent_id")
        if parent:
            avec_parent += 1
            assert (entite["id"], parent) in liens_directs

    assert avec_parent == stats["hierarchie"]["avec_parent_principal"]
    assert len(entites) - avec_parent == stats["hierarchie"]["sans_parent_principal"]


def test_snapshot_roae_conserve_la_source_et_la_provenance():
    manifeste = lire_json(INSTITUTIONNEL / "instantanes" / "roae_manifest.json")

    for entree in manifeste["partitions_entites"]:
        for entite in lire_jsonl(RACINE / entree["fichier"]):
            assert entite["source_dila"]
            assert entite["provenance"]
            assert entite["provenance"][0]["source_id"] == "dila_roae"
            assert entite["provenance"][0]["empreinte"]
