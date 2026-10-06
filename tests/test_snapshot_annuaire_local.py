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
        for ligne in chemin.read_text(encoding="utf-8").split("\n")
        if ligne.strip()
    ]


def verifier_partition(entree: dict) -> list[dict]:
    chemin = RACINE / entree["fichier"]
    assert chemin.is_file(), entree["fichier"]

    brut = chemin.read_bytes()
    assert hashlib.sha256(brut).hexdigest() == entree["sha256"]
    assert len(brut) == entree["octets"]

    objets = [
        json.loads(ligne)
        for ligne in brut.decode("utf-8").split("\n")
        if ligne.strip()
    ]
    assert len(objets) == entree["nombre"]
    return objets


def charger_roae() -> list[dict]:
    manifeste = lire_json(INSTITUTIONNEL / "instantanes" / "roae_manifest.json")
    entites = []
    for entree in manifeste["partitions_entites"]:
        entites.extend(lire_jsonl(RACINE / entree["fichier"]))
    return entites


def charger_local() -> tuple[dict, dict, list[dict], list[dict]]:
    manifeste = lire_json(
        INSTITUTIONNEL / "instantanes" / "annuaire_local_manifest.json"
    )
    stats = lire_json(INSTITUTIONNEL / "statistiques_annuaire_local.json")

    entites = []
    for entree in manifeste["partitions_entites"]:
        entites.extend(verifier_partition(entree))

    relations = []
    for entree in manifeste["partitions_relations"]:
        relations.extend(verifier_partition(entree))

    return manifeste, stats, entites, relations


def test_snapshot_local_correspond_au_manifeste():
    manifeste, stats, entites, relations = charger_local()

    assert len(entites) == manifeste["nombre_services_locaux"]
    assert len(entites) == stats["nombre_entites_canoniques"]
    assert len(relations) == manifeste["nombre_relations"]
    assert len(relations) == stats["nombre_relations_hierarchiques"]

    assert (
        stats["categories_export"]["SL"] + stats["categories_export"]["SIL"]
        == len(entites)
    )
    assert (
        stats["categories_export"]["SI"]
        + stats["categories_export"]["SL"]
        + stats["categories_export"]["SIL"]
        == stats["nombre_enregistrements_export_complet"]
    )


def test_snapshot_local_complete_le_roae_sans_chevauchement_d_identifiants():
    _, stats, entites, _ = charger_local()
    roae = charger_roae()

    ids_dila_roae = {
        entite["identifiants"]["dila_id"]
        for entite in roae
        if (entite.get("identifiants") or {}).get("dila_id")
    }
    ids_dila_local = {
        entite["identifiants"]["dila_local_id"]
        for entite in entites
        if (entite.get("identifiants") or {}).get("dila_local_id")
    }

    assert len(ids_dila_local) == len(entites)
    assert ids_dila_local.isdisjoint(ids_dila_roae)
    assert len(roae) == stats["categories_export"]["SI"]
    assert len(roae) + len(entites) == stats["nombre_enregistrements_export_complet"]


def test_relations_locales_pointent_vers_des_entites_connues():
    _, _, entites, relations = charger_local()
    roae = charger_roae()

    ids = {entite["id"] for entite in entites}
    ids.update(entite["id"] for entite in roae)

    ids_relations = [relation["id"] for relation in relations]
    assert len(ids_relations) == len(set(ids_relations))

    for relation in relations:
        assert relation["source_entite"] in ids
        assert relation["cible_entite"] in ids
        assert relation["type_relation"] == "DEPEND_DE"
        assert relation["provenance"]


def test_parent_principal_local_est_justifie_par_service_fils():
    _, stats, entites, relations = charger_local()

    liens_directs = {
        (relation["source_entite"], relation["cible_entite"])
        for relation in relations
        if relation.get("qualificatifs", {}).get("type_hierarchie_dila")
        == "Service Fils"
    }

    avec_parent = 0
    for entite in entites:
        parent = entite.get("parent_id")
        if parent:
            avec_parent += 1
            assert (entite["id"], parent) in liens_directs

    assert avec_parent == stats["hierarchie"]["avec_parent_principal"]
    assert len(entites) - avec_parent == stats["hierarchie"]["sans_parent_principal"]


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
    _, _, entites, _ = charger_local()

    for entite in entites:
        assert entite["provenance"]
        assert entite["provenance"][0]["source_id"] == "dila_annuaire_local"
        assert entite["provenance"][0]["empreinte"]
        assert (entite.get("identifiants") or {}).get("dila_local_id")

    assert sum(bool(entite.get("territoires")) for entite in entites) >= 85000
