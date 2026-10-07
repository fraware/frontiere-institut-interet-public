import csv
import importlib.util
import io
import json
import zipfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
CHEMIN_SCRIPT = RACINE / "scripts" / "ingerer_cog.py"

spec = importlib.util.spec_from_file_location("ingerer_cog", CHEMIN_SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def ecrire_csv(zf: zipfile.ZipFile, nom: str, lignes: list[dict[str, str]]) -> None:
    if not lignes:
        raise AssertionError("Le test doit fournir au moins une ligne.")
    flux = io.StringIO(newline="")
    writer = csv.DictWriter(flux, fieldnames=list(lignes[0]))
    writer.writeheader()
    writer.writerows(lignes)
    zf.writestr(nom, flux.getvalue().encode("utf-8"))


def jeux_minimaux() -> dict[str, list[dict[str, str]]]:
    return {
        "regions": [
            {
                "REG": "11",
                "CHEFLIEU": "75056",
                "TNCC": "1",
                "NCC": "ILE DE FRANCE",
                "NCCENR": "Île-de-France",
                "LIBELLE": "Île-de-France",
            }
        ],
        "departements": [
            {
                "DEP": "75",
                "REG": "11",
                "CHEFLIEU": "75056",
                "TNCC": "1",
                "NCC": "PARIS",
                "NCCENR": "Paris",
                "LIBELLE": "Paris",
            }
        ],
        "ctcd": [
            {
                "CTCD": "75C",
                "REG": "11",
                "CHEFLIEU": "75056",
                "TNCC": "1",
                "NCC": "PARIS",
                "NCCENR": "Paris",
                "LIBELLE": "Paris",
            }
        ],
        "arrondissements": [
            {
                "ARR": "751",
                "DEP": "75",
                "REG": "11",
                "CHEFLIEU": "75056",
                "TNCC": "1",
                "NCC": "PARIS",
                "NCCENR": "Paris",
                "LIBELLE": "Paris",
            }
        ],
        "cantons": [
            {
                "CAN": "7599",
                "DEP": "75",
                "REG": "11",
                "COMPCT": "1",
                "BURCENTRAL": "75056",
                "TNCC": "1",
                "NCC": "PARIS",
                "NCCENR": "Paris",
                "LIBELLE": "Paris",
                "TYPECT": "1",
            }
        ],
        "communes": [
            {
                "TYPECOM": "COM",
                "COM": "75056",
                "REG": "11",
                "DEP": "75",
                "CTCD": "75C",
                "ARR": "751",
                "TNCC": "1",
                "NCC": "PARIS",
                "NCCENR": "Paris",
                "LIBELLE": "Paris",
                "CAN": "7599",
                "COMPARENT": "",
            },
            {
                "TYPECOM": "ARM",
                "COM": "75101",
                "REG": "11",
                "DEP": "75",
                "CTCD": "75C",
                "ARR": "751",
                "TNCC": "1",
                "NCC": "PARIS 1ER ARRONDISSEMENT",
                "NCCENR": "Paris 1er Arrondissement",
                "LIBELLE": "Paris 1er Arrondissement",
                "CAN": "7599",
                "COMPARENT": "75056",
            },
        ],
        "mouvements_communes": [
            {
                "MOD": "10",
                "DATE_EFF": "1968-01-01",
                "TYPECOM_AV": "COM",
                "COM_AV": "75056",
                "TNCC_AV": "1",
                "NCC_AV": "PARIS",
                "NCCENR_AV": "Paris",
                "LIBELLE_AV": "Paris",
                "TYPECOM_AP": "COM",
                "COM_AP": "75056",
                "TNCC_AP": "1",
                "NCC_AP": "PARIS",
                "NCCENR_AP": "Paris",
                "LIBELLE_AP": "Paris",
            }
        ],
        "historique_communes": [
            {
                "TYPECOM": "COM",
                "COM": "75056",
                "TNCC": "1",
                "NCC": "PARIS",
                "NCCENR": "Paris",
                "LIBELLE": "Paris",
                "DATE_DEBUT": "1943-01-01",
                "DATE_FIN": "",
            }
        ],
        "comer": [
            {
                "COMER": "987",
                "TNCC": "0",
                "NCC": "POLYNESIE FRANCAISE",
                "NCCENR": "Polynésie française",
                "LIBELLE": "Polynésie française",
            }
        ],
        "communes_comer": [
            {
                "COM_COMER": "98735",
                "TNCC": "0",
                "NCC": "TAHITI",
                "NCCENR": "Tahiti",
                "LIBELLE": "Tahiti",
                "NATURE_ZONAGE": "COM",
                "COMER": "987",
                "LIBELLE_COMER": "Polynésie française",
            }
        ],
    }


def creer_archive(path: Path, donnees: dict[str, list[dict[str, str]]]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for cle, nom in module.FICHIERS_REQUIS.items():
            ecrire_csv(zf, nom, donnees[cle])


def test_construction_du_graphe_territorial_et_parent_de_commune():
    donnees = jeux_minimaux()
    territoires, anomalies, stats = module.construire_territoires(
        donnees,
        "2026-10-06T12:00:00+00:00",
        {},
    )

    ids = {t["id"]: t for t in territoires}
    paris = ids["FRONTIERE-TERR-COG-COM-75056"]
    premier = ids["FRONTIERE-TERR-COG-ARM-75101"]

    assert stats["par_type"]["COMMUNE"] == 1
    assert stats["par_type"]["ARRONDISSEMENT_MUNICIPAL"] == 1
    assert stats["par_type"]["COLLECTIVITE_OUTRE_MER"] == 1
    assert stats["par_type"]["ZONAGE_OUTRE_MER"] == 1
    assert not anomalies

    assert any(
        p["territoire_id"] == "FRONTIERE-TERR-COG-DEP-75"
        for p in paris["parents"]
    )
    assert any(
        p["type_relation"] == "COMMUNE_PARENTE"
        and p["territoire_id"] == "FRONTIERE-TERR-COG-COM-75056"
        for p in premier["parents"]
    )


def test_codes_identiques_de_commune_et_commune_deleguee_restent_distincts():
    donnees = jeux_minimaux()
    commune = dict(donnees["communes"][0])
    commune["COM"] = "01015"
    commune["DEP"] = "01"
    commune["REG"] = "84"
    commune["CTCD"] = ""
    commune["ARR"] = ""
    commune["CAN"] = ""
    commune["LIBELLE"] = "Arboys en Bugey"

    deleguee = dict(commune)
    deleguee["TYPECOM"] = "COMD"
    deleguee["LIBELLE"] = "Arbignieu"
    deleguee["COMPARENT"] = "01015"

    donnees["communes"] = [commune, deleguee]
    donnees["regions"] = [
        {
            "REG": "84",
            "CHEFLIEU": "69123",
            "TNCC": "0",
            "NCC": "AUVERGNE RHONE ALPES",
            "NCCENR": "Auvergne-Rhône-Alpes",
            "LIBELLE": "Auvergne-Rhône-Alpes",
        }
    ]
    donnees["departements"] = [
        {
            "DEP": "01",
            "REG": "84",
            "CHEFLIEU": "01053",
            "TNCC": "2",
            "NCC": "AIN",
            "NCCENR": "Ain",
            "LIBELLE": "Ain",
        }
    ]
    donnees["ctcd"] = []
    donnees["arrondissements"] = []
    donnees["cantons"] = []

    territoires, _, _ = module.construire_territoires(
        donnees,
        "2026-10-06T12:00:00+00:00",
        {},
    )
    ids = {t["id"] for t in territoires}

    assert "FRONTIERE-TERR-COG-COM-01015" in ids
    assert "FRONTIERE-TERR-COG-COMD-01015" in ids


def test_territoire_inchange_conserve_observation_et_collecte():
    donnees = jeux_minimaux()
    premiers, _, _ = module.construire_territoires(
        donnees,
        "2026-10-06T12:00:00+00:00",
        {},
    )
    index = {t["id"]: t for t in premiers}

    seconds, _, _ = module.construire_territoires(
        donnees,
        "2026-10-07T12:00:00+00:00",
        index,
    )
    paris = {t["id"]: t for t in seconds}["FRONTIERE-TERR-COG-COM-75056"]

    assert paris["observe_le"] == "2026-10-06T12:00:00+00:00"
    assert paris["provenance"][0]["collecte_le"] == "2026-10-06T12:00:00+00:00"


def test_relation_inchangee_conserve_sa_temporalite():
    donnees = jeux_minimaux()
    territoires, _, _ = module.construire_territoires(
        donnees,
        "2026-10-06T12:00:00+00:00",
        {},
    )
    premieres = module.construire_relations_territoriales(
        territoires,
        "2026-10-06T12:00:00+00:00",
        {},
    )
    index = {r["id"]: r for r in premieres}

    secondes = module.construire_relations_territoriales(
        territoires,
        "2026-10-07T12:00:00+00:00",
        index,
    )

    assert secondes
    assert all(r["observe_le"] == "2026-10-06T12:00:00+00:00" for r in secondes)


def test_evenements_stables_si_l_ordre_change():
    lignes = jeux_minimaux()["mouvements_communes"]
    autre = dict(lignes[0])
    autre["DATE_EFF"] = "1970-01-01"
    autre["COM_AV"] = "75001"

    a = module.construire_evenements(
        [lignes[0], autre],
        "2026-10-06T12:00:00+00:00",
    )
    b = module.construire_evenements(
        [autre, lignes[0]],
        "2026-10-07T12:00:00+00:00",
    )

    assert {x["id"] for x in a} == {x["id"] for x in b}


def test_parent_absent_reste_une_anomalie_explicite():
    donnees = jeux_minimaux()
    donnees["communes"][1]["COMPARENT"] = "99999"

    territoires, anomalies, _ = module.construire_territoires(
        donnees,
        "2026-10-06T12:00:00+00:00",
        {},
    )

    assert territoires
    assert any(
        a["type"] == "COMMUNE_PARENTE_ABSENTE"
        and a["comparent"] == "99999"
        for a in anomalies
    )


def test_archive_synthetique_est_lue_et_validee(tmp_path):
    donnees = jeux_minimaux()
    archive = tmp_path / "cog.zip"
    creer_archive(archive, donnees)

    with zipfile.ZipFile(archive) as zf:
        chargees = {}
        for cle, nom in module.FICHIERS_REQUIS.items():
            chargees[cle], meta = module.lire_csv_zip(zf, nom)
            assert meta["nombre_lignes"] == len(donnees[cle])

    module.verifier_colonnes(chargees)


def test_archive_refuse_traversee_de_repertoire(tmp_path):
    archive = tmp_path / "cog.zip"
    donnees = jeux_minimaux()
    with zipfile.ZipFile(archive, "w") as zf:
        for cle, nom in module.FICHIERS_REQUIS.items():
            cible = "../" + nom if cle == "communes" else nom
            ecrire_csv(zf, cible, donnees[cle])

    with zipfile.ZipFile(archive) as zf:
        try:
            module.lire_csv_zip(zf, module.FICHIERS_REQUIS["communes"])
        except module.ErreurCOG as exc:
            assert "dangereux" in str(exc)
        else:
            raise AssertionError("Chemin ZIP dangereux accepté")


def test_integrite_exige_toutes_les_extremites():
    territoires = [
        {
            "id": "FRONTIERE-TERR-COG-REG-11",
            "type_territoire": "REGION",
            "code": "11",
        }
    ]
    relations = [
        {
            "source_territoire": "FRONTIERE-TERR-COG-REG-11",
            "cible_territoire": "FRONTIERE-TERR-COG-DEP-75",
        }
    ]

    try:
        module.analyser_integrite(territoires, relations, [])
    except module.ErreurCOG as exc:
        assert "Cible" in str(exc)
    else:
        raise AssertionError("Relation orpheline acceptée")
