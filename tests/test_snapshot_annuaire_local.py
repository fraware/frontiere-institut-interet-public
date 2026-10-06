import hashlib
import json
from pathlib import Path
from typing import Iterator

RACINE = Path(__file__).resolve().parents[1]
INSTITUTIONNEL = RACINE / "institutionnel"


def lire_json(chemin: Path) -> dict:
    return json.loads(chemin.read_text(encoding="utf-8"))


def iter_jsonl(chemin: Path) -> Iterator[dict]:
    with chemin.open("r", encoding="utf-8") as fichier:
        for ligne in fichier:
            if ligne.strip():
                yield json.loads(ligne)


def verifier_partition(entree: dict) -> int:
    chemin = RACINE / entree["fichier"]
    assert chemin.is_file(), entree["fichier"]

    brut = chemin.read_bytes()
    assert hashlib.sha256(brut).hexdigest() == entree["sha256"]
    assert len(brut) == entree["octets"]

    nombre = sum(1 for _ in iter_jsonl(chemin))
    assert nombre == entree["nombre"]
    return nombre


def manifeste_local() -> dict:
    return lire_json(
        INSTITUTIONNEL / "instantanes" / "annuaire_local_manifest.json"
    )


def manifeste_roae() -> dict:
    return lire_json(INSTITUTIONNEL / "instantanes" / "roae_manifest.json")


def iter_entites_locales() -> Iterator[dict]:
    for entree in manifeste_local()["partitions_entites"]:
        yield from iter_jsonl(RACINE / entree["fichier"])


def iter_relations_locales() -> Iterator[dict]:
    for entree in manifeste_local()["partitions_relations"]:
        yield from iter_jsonl(RACINE / entree["fichier"])


def iter_entites_roae() -> Iterator[dict]:
    for entree in manifeste_roae()["partitions_entites"]:
        yield from iter_jsonl(RACINE / entree["fichier"])


def test_snapshot_local_correspond_au_manifeste():
    manifeste = manifeste_local()
    stats = lire_json(INSTITUTIONNEL / "statistiques_annuaire_local.json")

    nombre_entites = sum(
        verifier_partition(entree) for entree in manifeste["partitions_entites"]
    )
    nombre_relations = sum(
        verifier_partition(entree) for entree in manifeste["partitions_relations"]
    )

    assert nombre_entites == manifeste["nombre_services_locaux"]
    assert nombre_entites == stats["nombre_entites_canoniques"]
    assert nombre_relations == manifeste["nombre_relations"]
    assert nombre_relations == stats["nombre_relations_hierarchiques"]

    assert (
        stats["categories_export"]["SL"] + stats["categories_export"]["SIL"]
        == nombre_entites
    )
    assert (
        stats["categories_export"]["SI"]
        + stats["categories_export"]["SL"]
        + stats["categories_export"]["SIL"]
        == stats["nombre_enregistrements_export_complet"]
    )


def test_snapshot_local_complete_le_roae_sans_chevauchement_d_identifiants():
    stats = lire_json(INSTITUTIONNEL / "statistiques_annuaire_local.json")

    ids_dila_roae = {
        entite["identifiants"]["dila_id"]
        for entite in iter_entites_roae()
        if (entite.get("identifiants") or {}).get("dila_id")
    }
    ids_dila_local = {
        entite["identifiants"]["dila_local_id"]
        for entite in iter_entites_locales()
        if (entite.get("identifiants") or {}).get("dila_local_id")
    }

    assert len(ids_dila_local) == stats["nombre_entites_canoniques"]
    assert ids_dila_local.isdisjoint(ids_dila_roae)
    assert len(ids_dila_roae) == stats["categories_export"]["SI"]
    assert (
        len(ids_dila_roae) + len(ids_dila_local)
        == stats["nombre_enregistrements_export_complet"]
    )


def test_relations_locales_pointent_vers_des_entites_connues():
    ids = {entite["id"] for entite in iter_entites_roae()}
    ids.update(entite["id"] for entite in iter_entites_locales())

    ids_relations = set()
    nombre_relations = 0
    for relation in iter_relations_locales():
        nombre_relations += 1
        assert relation["id"] not in ids_relations
        ids_relations.add(relation["id"])
        assert relation["source_entite"] in ids
        assert relation["cible_entite"] in ids
        assert relation["type_relation"] == "DEPEND_DE"
        assert relation["provenance"]

    stats = lire_json(INSTITUTIONNEL / "statistiques_annuaire_local.json")
    assert nombre_relations == stats["nombre_relations_hierarchiques"]


def test_parent_principal_local_est_justifie_par_service_fils():
    liens_directs = {
        (relation["source_entite"], relation["cible_entite"])
        for relation in iter_relations_locales()
        if relation.get("qualificatifs", {}).get("type_hierarchie_dila")
        == "Service Fils"
    }

    avec_parent = 0
    nombre_entites = 0
    for entite in iter_entites_locales():
        nombre_entites += 1
        parent = entite.get("parent_id")
        if parent:
            avec_parent += 1
            assert (entite["id"], parent) in liens_directs

    stats = lire_json(INSTITUTIONNEL / "statistiques_annuaire_local.json")
    assert avec_parent == stats["hierarchie"]["avec_parent_principal"]
    assert nombre_entites - avec_parent == stats["hierarchie"]["sans_parent_principal"]


def test_toutes_les_anomalies_roae_sont_resolues_par_le_flux_local():
    rapport = lire_json(INSTITUTIONNEL / "resolution_roae_local.json")
    anomalies_roae = lire_json(INSTITUTIONNEL / "anomalies_roae.json")

    assert (
        rapport["anomalies_roae_initiales"]
        == anomalies_roae["nombre_anomalies_hierarchiques"]
    )
    assert (
        rapport["resolues_par_annuaire_local"]
        + rapport["restantes_apres_croisement"]
        == rapport["anomalies_roae_initiales"]
    )
    assert rapport["restantes_apres_croisement"] == 0


def test_provenance_locale_et_territoires_sont_conserves():
    nombre = 0
    avec_territoire = 0

    for entite in iter_entites_locales():
        nombre += 1
        assert entite["provenance"]
        assert entite["provenance"][0]["source_id"] == "dila_annuaire_local"
        assert entite["provenance"][0]["empreinte"]
        assert (entite.get("identifiants") or {}).get("dila_local_id")
        if entite.get("territoires"):
            avec_territoire += 1

    stats = lire_json(INSTITUTIONNEL / "statistiques_annuaire_local.json")
    assert nombre == stats["nombre_entites_canoniques"]
    assert avec_territoire == stats["couverture"]["avec_territoire_direct"]
    assert avec_territoire >= 85000
