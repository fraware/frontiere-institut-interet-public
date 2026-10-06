import importlib.util
import io
import json
import tarfile
import zipfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
CHEMIN_SCRIPT = RACINE / "scripts" / "analyser_annuaire_local.py"

spec = importlib.util.spec_from_file_location("analyse_annuaire_local", CHEMIN_SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def uuid(n: int) -> str:
    return f"00000000-0000-0000-0000-{n:012d}"


def service(identifiant: str, nom: str, **extra):
    base = {
        "id": identifiant,
        "nom": nom,
        "categorie": "SL",
        "type_repertoire": "Annuaire local",
        "type_organisme": "Mairie",
        "pivot": [{"type_service_local": "mairie", "code_insee_commune": ["75056"]}],
        "statut": "active",
        "date_creation": "01/01/2020 00:00:00",
        "date_modification": "06/10/2026 09:00:00",
        "date_diffusion": "06/10/2026 10:00:00",
        "version_type": "Publiable",
        "version_etat_modification": "",
        "version_source": "",
        "adresse": [
            {
                "nom_commune": "Évry-Courcouronnes",
                "longitude": "2.4",
                "latitude": "48.6",
            }
        ],
        "hierarchie": [],
    }
    base.update(extra)
    return base


def make_archive(
    path: Path,
    services: list[dict],
    communes: dict[str, dict],
    *,
    unsafe_tar: bool = False,
):
    json_bytes = json.dumps(services, ensure_ascii=False).encode("utf-8")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in communes.items():
            zf.writestr(name, json.dumps(data, ensure_ascii=False))
    zip_bytes = zip_buffer.getvalue()

    with tarfile.open(path, "w:bz2") as tf:
        info_json = tarfile.TarInfo("2026-10-06_100000-data.gouv_local.json")
        info_json.size = len(json_bytes)
        tf.addfile(info_json, io.BytesIO(json_bytes))

        info_zip = tarfile.TarInfo("2026-10-06_100000-data.gouv.commune.zip")
        info_zip.size = len(zip_bytes)
        tf.addfile(info_zip, io.BytesIO(zip_bytes))

        if unsafe_tar:
            payload = b"x"
            bad = tarfile.TarInfo("../evil.txt")
            bad.size = len(payload)
            tf.addfile(bad, io.BytesIO(payload))


def test_iter_tableau_json_streaming_unicode_et_petits_blocs():
    donnees = [
        service(uuid(1), "Mairie d’Été"),
        service(uuid(2), "Sous-préfecture"),
    ]
    flux = io.BytesIO(json.dumps(donnees, ensure_ascii=False).encode("utf-8"))

    resultat = list(module.iter_tableau_json(flux, taille_bloc=17))

    assert [x["nom"] for x in resultat] == ["Mairie d’Été", "Sous-préfecture"]


def test_iter_tableau_json_refuse_structure_non_tableau():
    flux = io.BytesIO(json.dumps({"services": [service(uuid(1), "A")]}).encode())

    try:
        list(module.iter_tableau_json(flux, taille_bloc=11))
    except module.ErreurAnalyse as exc:
        assert "tableau JSON" in str(exc)
    else:
        raise AssertionError("structure objet acceptée silencieusement")


def test_empreinte_semantique_ignore_uniquement_champs_techniques():
    a = service(uuid(1), "A", date_diffusion="06/10/2026 10:00:00")
    b = service(uuid(1), "A", date_diffusion="07/10/2026 10:00:00")

    assert module.compact_sha256(a) != module.compact_sha256(b)
    assert (
        module.empreinte_semantique_candidate(a)
        == module.empreinte_semantique_candidate(b)
    )


def test_archive_synthetique_mesure_identites_relations_et_competences(tmp_path):
    local_parent = uuid(1)
    local_child = uuid(2)
    roae_only = uuid(3)
    unknown = uuid(4)
    overlap = uuid(5)

    services = [
        service(
            local_parent,
            "Parent local",
            hierarchie=[
                {"type_hierarchie": "Service Fils", "service": {"id": local_child}},
                {"type_hierarchie": "Autre hiérarchie", "service": roae_only},
                {"type_hierarchie": "Autre hiérarchie", "service": unknown},
            ],
        ),
        service(local_child, "Enfant local"),
        service(overlap, "Même organisme", siren="123456789"),
    ]
    communes = {
        "75056.json": {
            "code_insee_commune": "75056",
            "nom": "Paris",
            "type_service_local": [
                {
                    "code_type_service_local": "mairie",
                    "organisme": [local_parent, local_child],
                },
                {"code_type_service_local": "caf", "organisme": overlap},
            ],
        },
        "13055.json": {
            "code_insee_commune": "13055",
            "nom": "Marseille",
            "type_service_local": [],
        },
    }
    archive = tmp_path / "all_latest.tar.bz2"
    make_archive(archive, services, communes)

    roae = {
        roae_only: {
            "id_canonique": "FRONTIERE-X",
            "nom": "ROAE seulement",
            "categorie": "SI",
            "siren": None,
            "siret": None,
            "empreinte_source": "a",
        },
        overlap: {
            "id_canonique": "FRONTIERE-Y",
            "nom": "Même organisme",
            "categorie": "SI",
            "siren": "123456789",
            "siret": None,
            "empreinte_source": "b",
        },
    }
    anomalies = [
        {
            "parent_id_dila": uuid(10),
            "parent_nom": "P",
            "type_hierarchie_dila": "Service Fils",
            "candidats_id": [local_child],
        },
        {
            "parent_id_dila": uuid(11),
            "parent_nom": "Q",
            "type_hierarchie_dila": "Service Fils",
            "candidats_id": [unknown],
        },
    ]

    rapport = module.analyser_archive(archive, roae=roae, anomalies=anomalies)

    assert rapport["guichets"]["nombre_guichets_source"] == 3
    assert rapport["guichets"]["nombre_ids_uniques"] == 3
    assert (
        rapport["guichets"]["croisement_roae"]["nombre_recouvrements_ids_exacts"]
        == 1
    )
    assert rapport["guichets"]["distributions"]["type_service_local"]["mairie"] == 3
    assert rapport["guichets"]["hierarchie"]["liens_local_local"] == 1
    assert rapport["guichets"]["hierarchie"]["liens_local_roae_hors_local"] == 1
    assert rapport["guichets"]["hierarchie"]["liens_non_resolus"] == 1
    assert (
        rapport["resolution_anomalies_roae"][
            "nombre_resolues_exactement_par_un_id_local"
        ]
        == 1
    )
    assert rapport["resolution_anomalies_roae"]["nombre_toujours_absentes"] == 1
    assert rapport["competence_geographique"]["nombre_fichiers_communes"] == 2
    assert (
        rapport["competence_geographique"]["nombre_codes_insee_distincts"]
        == 2
    )
    assert (
        rapport["competence_geographique"]["nombre_associations_competence"]
        == 3
    )


def test_doublon_id_est_explicitement_compte(tmp_path):
    identifiant = uuid(1)
    archive = tmp_path / "all_latest.tar.bz2"
    make_archive(
        archive,
        [service(identifiant, "A"), service(identifiant, "B")],
        {
            "75056.json": {
                "code_insee_commune": "75056",
                "nom": "Paris",
                "type_service_local": [],
            }
        },
    )

    rapport = module.analyser_archive(archive, roae={}, anomalies=[])

    assert rapport["guichets"]["nombre_guichets_source"] == 2
    assert rapport["guichets"]["nombre_ids_uniques"] == 1
    assert rapport["guichets"]["nombre_occurrences_dupliquees"] == 1


def test_tar_refuse_traversee_de_repertoire(tmp_path):
    archive = tmp_path / "all_latest.tar.bz2"
    make_archive(
        archive,
        [service(uuid(1), "A")],
        {
            "75056.json": {
                "code_insee_commune": "75056",
                "nom": "Paris",
                "type_service_local": [],
            }
        },
        unsafe_tar=True,
    )

    try:
        module.analyser_archive(archive, roae={}, anomalies=[])
    except module.ErreurAnalyse as exc:
        assert "Chemin TAR dangereux" in str(exc)
    else:
        raise AssertionError("archive dangereuse acceptée")


def test_zip_refuse_traversee_de_repertoire(tmp_path):
    chemin = tmp_path / "communes.zip"
    with zipfile.ZipFile(chemin, "w") as zf:
        zf.writestr(
            "../75056.json",
            json.dumps({"code_insee_commune": "75056"}),
        )

    try:
        module.analyser_competences_communes(chemin)
    except module.ErreurAnalyse as exc:
        assert "Chemin ZIP dangereux" in str(exc)
    else:
        raise AssertionError("zip dangereux accepté")


def test_anomalie_multi_match_est_a_examiner():
    a, b = uuid(1), uuid(2)
    anomalies = [{"candidats_id": [a, b], "parent_id_dila": uuid(10)}]
    index = {a: {"nom": "A"}, b: {"nom": "B"}}

    resultat = module.resoudre_anomalies_roae(anomalies, index)

    assert resultat["nombre_a_examiner"] == 1
    assert resultat["nombre_resolues_exactement_par_un_id_local"] == 0
