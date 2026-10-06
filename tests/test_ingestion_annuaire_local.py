import importlib.util
import io
import json
import tarfile
import zipfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
CHEMIN_SCRIPT = RACINE / "scripts" / "ingerer_annuaire_local.py"

spec = importlib.util.spec_from_file_location("ingerer_annuaire_local", CHEMIN_SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def service_exemple(identifiant="11111111-2222-3333-4444-555555555555"):
    return {
        "id": identifiant,
        "nom": "Mairie d'essai",
        "categorie": "SL",
        "type_organisme": "Mairie",
        "type_service_local": "mairie",
        "pivot": "mairie",
        "code_insee_commune": ["75056"],
        "adresse": [
            {
                "numero_voie": "1 place d'essai",
                "code_postal": "75000",
                "nom_commune": "Paris",
            }
        ],
        "telephone": [{"valeur": "01 23 45 67 89"}],
        "site_internet": [{"valeur": "https://example.gouv.fr"}],
        "adresse_courriel": ["contact@example.gouv.fr"],
        "mission": "Accueille les usagers.",
        "siren": "123456789",
        "siret": "12345678900012",
        "statut": "active",
        "statut_de_diffusion": True,
        "date_creation": "01/01/2020 00:00:00",
        "date_modification": "01/10/2026 00:00:00",
        "plage_ouverture": [{"nom_jour_debut": "Lundi", "valeur_heure_debut_1": "09:00"}],
        "hierarchie": [],
    }


def test_canonicalisation_locale_preserve_territoire_et_coordonnees():
    service = service_exemple()
    entite = module.canonicaliser_service(service, "2026-10-06T12:00:00+00:00")

    assert entite["id"].startswith("FRONTIERE-INST-DILA-LOCAL-")
    assert entite["nom_officiel"] == "Mairie d'essai"
    assert entite["territoires"] == ["75056"]
    assert entite["identifiants"]["siren"] == "123456789"
    assert entite["missions"][0]["nature"] == "PUBLIEE"
    assert any(c["type"] == "ADRESSE" for c in entite["coordonnees"])
    assert entite["donnees_annuaire_local"]["pivot"] == "mairie"
    assert entite["provenance"][0]["source_id"] == "dila_annuaire_local"


def test_entite_inchangee_conserve_date_observation():
    service = service_exemple()
    premiere = module.canonicaliser_service(service, "2026-10-06T12:00:00+00:00")
    seconde = module.canonicaliser_service(
        service,
        "2026-10-07T12:00:00+00:00",
        precedent=premiere,
    )

    assert seconde["observe_le"] == premiere["observe_le"]
    assert seconde["provenance"][0]["collecte_le"] == premiere["provenance"][0]["collecte_le"]


def test_hierarchie_locale_orientee_enfant_vers_parent():
    parent = service_exemple()
    enfant_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    enfant = service_exemple(enfant_id)
    enfant["nom"] = "Annexe d'essai"
    parent["hierarchie"] = [
        {"type_hierarchie": "Service Fils", "service": enfant_id}
    ]

    relations, anomalies = module.construire_relations_locales(
        [parent, enfant],
        {parent["id"], enfant_id},
        {},
        "2026-10-06T12:00:00+00:00",
    )

    assert anomalies == []
    assert len(relations) == 1
    assert relations[0]["source_entite"].endswith(enfant_id.upper())
    assert relations[0]["cible_entite"].endswith(parent["id"].upper())
    assert relations[0]["type_relation"] == "DEPEND_DE"


def test_competence_commune_resout_un_guichet_local():
    local_id = "11111111-2222-3333-4444-555555555555"
    donnees = {
        "code_insee_commune": "75056",
        "nom": "Paris",
        "type_service_local": [
            {
                "code_type_service_local": "mairie",
                "organisme": [local_id],
            }
        ],
    }

    record, anomalies, resolus, non_resolus = module.canonicaliser_competence_commune(
        donnees,
        {local_id},
        {},
    )

    assert record["code_insee_commune"] == "75056"
    assert record["types_service_local"][0]["organismes"][0].endswith(local_id.upper())
    assert anomalies == []
    assert resolus == 1
    assert non_resolus == 0


def test_extraction_archive_identifie_json_et_zip(tmp_path):
    json_bytes = json.dumps([service_exemple()], ensure_ascii=False).encode("utf-8")

    competence = io.BytesIO()
    with zipfile.ZipFile(competence, "w") as z:
        z.writestr(
            "75056.json",
            json.dumps(
                {
                    "code_insee_commune": "75056",
                    "nom": "Paris",
                    "type_service_local": [],
                }
            ),
        )

    archive_path = tmp_path / "all_latest.tar.bz2"
    with tarfile.open(archive_path, "w:bz2") as tar:
        info_json = tarfile.TarInfo("2026-10-06-data.gouv_local.json")
        info_json.size = len(json_bytes)
        tar.addfile(info_json, io.BytesIO(json_bytes))

        zip_bytes = competence.getvalue()
        info_zip = tarfile.TarInfo("2026-10-06-data.gouv.commune.zip")
        info_zip.size = len(zip_bytes)
        tar.addfile(info_zip, io.BytesIO(zip_bytes))

    main_json, competence_zip, details = module.extraire_archive(archive_path, tmp_path / "x")

    assert main_json.exists()
    assert competence_zip.exists()
    assert details["membre_json"].endswith(".json")
    assert details["membre_competence"].endswith(".zip")
