import importlib.util
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
CHEMIN_SCRIPT = RACINE / "scripts" / "resoudre_territoires_dila_cog.py"

spec = importlib.util.spec_from_file_location("resoudre_territoires_dila_cog", CHEMIN_SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def ecrire_jsonl(path: Path, objets: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in objets),
        encoding="utf-8",
    )


def test_choix_priorise_commune_sur_commune_deleguee():
    candidats = [
        {
            "id": "FRONTIERE-TERR-COG-COMD-01015",
            "type_territoire": "COMMUNE_DELEGUEE",
            "nom_officiel": "Arbignieu",
        },
        {
            "id": "FRONTIERE-TERR-COG-COM-01015",
            "type_territoire": "COMMUNE",
            "nom_officiel": "Arboys en Bugey",
        },
    ]

    statut, territoire = module.choisir_territoire(candidats)

    assert statut == "RESOLU"
    assert territoire["id"] == "FRONTIERE-TERR-COG-COM-01015"


def test_choix_detecte_ambiguite_au_meme_niveau():
    candidats = [
        {
            "id": "FRONTIERE-TERR-COG-COMD-A",
            "type_territoire": "COMMUNE_DELEGUEE",
            "nom_officiel": "A",
        },
        {
            "id": "FRONTIERE-TERR-COG-COMA-B",
            "type_territoire": "COMMUNE_ASSOCIEE",
            "nom_officiel": "B",
        },
    ]

    statut, territoire = module.choisir_territoire(candidats)

    assert statut == "AMBIGU"
    assert len(territoire) == 2


def test_resolution_distingue_courant_historique_et_inconnu(tmp_path):
    territoires = tmp_path / "territoires"
    entites = tmp_path / "entites"
    historique = tmp_path / "historique.jsonl"
    manifeste_cog = tmp_path / "cog.json"
    manifeste_local = tmp_path / "local.json"

    ecrire_jsonl(
        territoires / "part.jsonl",
        [
            {
                "id": "FRONTIERE-TERR-COG-COM-75056",
                "type_territoire": "COMMUNE",
                "code": "75056",
                "nom_officiel": "Paris",
            }
        ],
    )
    ecrire_jsonl(
        entites / "part.jsonl",
        [
            {"id": "INST-1", "territoires": ["75056"]},
            {"id": "INST-2", "territoires": ["14463"]},
            {"id": "INST-3", "territoires": ["99999"]},
            {"id": "INST-4", "territoires": ["75056"]},
        ],
    )
    ecrire_jsonl(
        historique,
        [
            {
                "typecom": "COM",
                "code": "75056",
                "nom": "Paris",
                "valide_depuis": "1943-01-01",
                "valide_jusqua": None,
            },
            {
                "typecom": "COM",
                "code": "14463",
                "nom": "Neuilly-le-Malherbe",
                "valide_depuis": "1943-01-01",
                "valide_jusqua": "1972-04-01",
            },
        ],
    )
    manifeste_cog.write_text(
        json.dumps(
            {
                "millesime": "2026",
                "sha256_archive": "cog-hash",
                "version_transformation": "1.0",
            }
        ),
        encoding="utf-8",
    )
    manifeste_local.write_text(
        json.dumps(
            {
                "sha256_semantique_export": "local-hash",
                "version_transformation": "2.2",
            }
        ),
        encoding="utf-8",
    )

    rapport = module.calculer_resolution(
        dossier_territoires=territoires,
        dossier_entites=entites,
        historique=historique,
        manifeste_cog_path=manifeste_cog,
        manifeste_local_path=manifeste_local,
    )

    assert rapport["nombre_references_territoriales"] == 4
    assert rapport["nombre_codes_distincts"] == 3
    assert rapport["resultats"]["codes_resolus_courants"] == 1
    assert rapport["resultats"]["codes_historiques_seulement"] == 1
    assert rapport["resultats"]["codes_inconnus"] == 1

    par_code = {x["code"]: x for x in rapport["codes"]}
    assert par_code["75056"]["statut"] == "RESOLU_COURANT"
    assert par_code["75056"]["territoire_id"] == "FRONTIERE-TERR-COG-COM-75056"
    assert len(par_code["75056"]["exemples_entites"]) == 2
    assert par_code["14463"]["statut"] == "HISTORIQUE_SEULEMENT"
    assert par_code["99999"]["statut"] == "INCONNU"


def test_empreinte_dependances_change_si_un_snapshot_change():
    cog = {
        "millesime": "2026",
        "sha256_archive": "a",
        "version_transformation": "1.0",
    }
    local = {
        "sha256_semantique_export": "b",
        "version_transformation": "2.2",
    }

    premiere = module.empreinte_dependances(cog, local)
    local["sha256_semantique_export"] = "c"
    seconde = module.empreinte_dependances(cog, local)

    assert premiere != seconde
