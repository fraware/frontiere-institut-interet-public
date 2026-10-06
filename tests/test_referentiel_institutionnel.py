import json
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def charger(nom: str) -> dict:
    return json.loads((RACINE / "institutionnel" / nom).read_text(encoding="utf-8"))


def test_registre_sources_unique_et_sourcees():
    registre = charger("sources_v1.json")
    sources = registre["sources"]
    ids = [source["id"] for source in sources]

    assert len(ids) == len(set(ids))
    assert len(sources) >= 10

    for source in sources:
        assert source["nom"].strip()
        assert source["criticite"] in {"critique", "haute", "moyenne", "basse"}
        assert source["cadence_attendue"].strip()
        assert source.get("metadata_url") or source.get("page_url")
        assert source["familles"]
        assert source["usage"]


def test_sources_critiques_couvrent_le_socle():
    registre = charger("sources_v1.json")
    critiques = {source["id"] for source in registre["sources"] if source["criticite"] == "critique"}

    assert {
        "dila_roae",
        "dila_annuaire_local",
        "insee_cog",
        "dgcl_banatic",
        "dila_jorf",
        "dila_protocole_gouvernement",
    }.issubset(critiques)


def test_matrice_couverture_reference_des_sources_existantes():
    registre = charger("sources_v1.json")
    couverture = charger("couverture_cible_v1.json")
    ids_sources = {source["id"] for source in registre["sources"]}

    assert len(couverture["familles"]) >= 12

    for famille in couverture["familles"]:
        assert famille["id"].strip()
        assert famille["objectif"].strip()
        assert famille["sources"]
        assert set(famille["sources"]).issubset(ids_sources)


def test_schema_entite_impose_provenance_et_temporalite():
    schema = charger("schema_entite_v1.json")

    assert {"id", "nom_officiel", "famille", "etat", "provenance", "observe_le"}.issubset(
        set(schema["required"])
    )
    assert schema["properties"]["provenance"]["minItems"] == 1
    assert "valide_depuis" in schema["properties"]
    assert "valide_jusqua" in schema["properties"]


def test_schema_relation_couvre_les_relations_essentielles():
    schema = charger("schema_relation_v1.json")
    valeurs = set(schema["properties"]["type_relation"]["enum"])

    assert {
        "DEPEND_DE",
        "TUTELLE_DE",
        "COMPETENT_SUR",
        "SUCCEDE_A",
        "DETIENT_CAPACITE",
        "MOBILISABLE_PAR",
    }.issubset(valeurs)
