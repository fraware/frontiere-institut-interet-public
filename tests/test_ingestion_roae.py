import importlib.util
import io
import json
import zipfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
CHEMIN_SCRIPT = RACINE / "scripts" / "ingerer_roae.py"

spec = importlib.util.spec_from_file_location("ingerer_roae", CHEMIN_SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def service_exemple():
    return {
        "id": "11111111-2222-3333-4444-555555555555",
        "nom": "Direction d'essai",
        "categorie": "SI",
        "type_organisme": "Direction d'administration centrale",
        "sigle": "DE",
        "siren": "123456789",
        "siret": "12345678900012",
        "mission": "Conduit une mission publique d'essai.",
        "adresse_courriel": "contact@example.gouv.fr",
        "telephone": [{"valeur": "01 23 45 67 89", "description": ""}],
        "site_internet": [{"libelle": "Site", "valeur": "https://example.gouv.fr"}],
        "texte_reference": [
            {"libelle": "Décret d'essai", "valeur": "https://www.legifrance.gouv.fr/"}
        ],
        "affectation_personne": [
            {
                "personne": {
                    "nom": "DUPONT",
                    "prenom": "Camille",
                    "civilite": "",
                    "grade": "administratrice de l'État",
                    "texte_reference": [],
                    "adresse_courriel": [],
                },
                "fonction": "Directrice",
                "telephone": "",
            }
        ],
        "hierarchie": [],
        "statut_de_diffusion": True,
        "date_creation": "01/01/2020 00:00:00",
        "date_modification": "01/10/2026 00:00:00",
    }


def test_canonicalisation_preserve_identite_mission_et_source():
    service = service_exemple()
    entite = module.canonicaliser_service(service, "2026-10-06T12:00:00+00:00")

    assert entite["id"] == "FRONTIERE-INST-DILA-11111111-2222-3333-4444-555555555555"
    assert entite["nom_officiel"] == "Direction d'essai"
    assert entite["identifiants"]["siren"] == "123456789"
    assert entite["missions"][0]["nature"] == "PUBLIEE"
    assert entite["responsables"][0]["fonction"] == "Directrice"
    assert entite["source_dila"] == service
    assert entite["provenance"][0]["source_id"] == "dila_roae"
    assert entite["provenance"][0]["empreinte"]


def test_hierarchie_est_orientee_enfant_vers_parent():
    parent = service_exemple()
    enfant = {
        **service_exemple(),
        "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "nom": "Sous-direction d'essai",
    }
    parent["hierarchie"] = [
        {
            "type_hierarchie": "Hiérarchie",
            "service": {"id": enfant["id"], "nom": enfant["nom"]},
        }
    ]

    relations, anomalies = module.relations_hierarchie(
        [parent, enfant], "2026-10-06T12:00:00+00:00"
    )

    assert anomalies == []
    assert len(relations) == 1
    assert relations[0]["source_entite"].endswith(enfant["id"].upper())
    assert relations[0]["cible_entite"].endswith(parent["id"].upper())
    assert relations[0]["type_relation"] == "DEPEND_DE"


def test_chargeur_accepte_zip_avec_liste_json():
    donnees = [service_exemple()]
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as archive:
        archive.writestr("dila_test.json", json.dumps(donnees, ensure_ascii=False))

    services, nom = module.charger_services_depuis_zip(tampon.getvalue())

    assert nom == "dila_test.json"
    assert services[0]["nom"] == "Direction d'essai"


def test_id_canonique_est_stable():
    brut = "11111111-2222-3333-4444-555555555555"
    assert module.id_canonique(brut) == module.id_canonique(brut)


def test_entite_inchangee_conserve_date_observation():
    service = service_exemple()
    premiere = module.canonicaliser_service(
        service,
        "2026-10-06T12:00:00+00:00",
    )
    seconde = module.canonicaliser_service(
        service,
        "2026-10-07T12:00:00+00:00",
        precedent=premiere,
    )

    assert seconde["observe_le"] == premiere["observe_le"]
    assert seconde["provenance"][0]["collecte_le"] == premiere["provenance"][0]["collecte_le"]


def test_parent_principal_provient_du_lien_service_fils():
    parent = service_exemple()
    enfant = {
        **service_exemple(),
        "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "nom": "Sous-direction d'essai",
    }
    parent["hierarchie"] = [
        {
            "type_hierarchie": "Service Fils",
            "service": enfant["id"],
        }
    ]

    entites = [
        module.canonicaliser_service(parent, "2026-10-06T12:00:00+00:00"),
        module.canonicaliser_service(enfant, "2026-10-06T12:00:00+00:00"),
    ]
    relations, anomalies = module.relations_hierarchie(
        [parent, enfant], "2026-10-06T12:00:00+00:00"
    )
    resultat = module.appliquer_parent_principal(entites, relations)

    enfant_canonique = next(e for e in entites if e["nom_officiel"] == "Sous-direction d'essai")
    assert anomalies == []
    assert enfant_canonique["parent_id"].endswith(parent["id"].upper())
    assert resultat["avec_parent_principal"] == 1
