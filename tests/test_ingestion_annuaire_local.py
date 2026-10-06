import importlib.util
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
CHEMIN_SCRIPT = RACINE / "scripts" / "ingerer_annuaire_local.py"

spec = importlib.util.spec_from_file_location("ingerer_annuaire_local", CHEMIN_SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def service_exemple(
    identifiant="11111111-2222-3333-4444-555555555555",
    categorie="SL",
):
    return {
        "id": identifiant,
        "nom": "Mairie d'essai",
        "categorie": categorie,
        "type_organisme": "Mairie",
        "pivot": [
            {
                "type_service_local": "mairie",
                "code_insee_commune": ["75056"],
            }
        ],
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
        "statut_de_diffusion": True,
        "date_creation": "01/01/2020 00:00:00",
        "date_modification": "01/10/2026 00:00:00",
        "plage_ouverture": [
            {"nom_jour_debut": "Lundi", "valeur_heure_debut_1": "09:00"}
        ],
        "hierarchie": [],
    }


def test_filtre_conserve_sl_et_sil():
    enregistrements = [
        service_exemple(categorie="SL"),
        service_exemple(
            "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            categorie="SIL",
        ),
        service_exemple(
            "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
            categorie="SI",
        ),
    ]

    locaux, categories = module.filtrer_services_locaux(enregistrements)

    assert len(locaux) == 2
    assert categories["SL"] == 1
    assert categories["SIL"] == 1
    assert categories["SI"] == 1


def test_canonicalisation_locale_preserve_territoire_et_coordonnees():
    service = service_exemple()
    entite = module.canonicaliser_service(
        service,
        "2026-10-06T12:00:00+00:00",
    )

    assert entite["id"].startswith("FRONTIERE-INST-DILA-LOCAL-")
    assert entite["nom_officiel"] == "Mairie d'essai"
    assert entite["territoires"] == ["75056"]
    assert entite["identifiants"]["siren"] == "123456789"
    assert entite["missions"][0]["nature"] == "PUBLIEE"
    assert any(c["type"] == "ADRESSE" for c in entite["coordonnees"])
    assert entite["donnees_annuaire_local"]["pivot"][0]["type_service_local"] == "mairie"
    assert entite["provenance"][0]["source_id"] == "dila_annuaire_local"


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
    assert (
        seconde["provenance"][0]["collecte_le"]
        == premiere["provenance"][0]["collecte_le"]
    )


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


def test_parent_principal_est_derivable():
    parent = service_exemple()
    enfant_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    enfant = service_exemple(enfant_id)
    parent["hierarchie"] = [
        {"type_hierarchie": "Service Fils", "service": enfant_id}
    ]

    entites = [
        module.canonicaliser_service(
            parent,
            "2026-10-06T12:00:00+00:00",
        ),
        module.canonicaliser_service(
            enfant,
            "2026-10-06T12:00:00+00:00",
        ),
    ]
    relations, _ = module.construire_relations_locales(
        [parent, enfant],
        {parent["id"], enfant_id},
        {},
        "2026-10-06T12:00:00+00:00",
    )
    resultat = module.appliquer_parent_principal(entites, relations)

    enfant_canonique = next(
        e for e in entites if e["id"].endswith(enfant_id.upper())
    )
    assert enfant_canonique["parent_id"].endswith(parent["id"].upper())
    assert resultat["avec_parent_principal"] == 1


def test_chargeur_export_accepte_liste(tmp_path):
    chemin = tmp_path / "export.json"
    chemin.write_text(
        json.dumps([service_exemple()], ensure_ascii=False),
        encoding="utf-8",
    )

    donnees = module.charger_export(chemin)

    assert len(donnees) == 1
    assert donnees[0]["nom"] == "Mairie d'essai"


def test_structures_json_encodees_sont_decodees():
    parent = service_exemple()
    enfant_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    enfant = service_exemple(enfant_id)

    parent["hierarchie"] = json.dumps(
        [{"type_hierarchie": "Service Fils", "service": enfant_id}]
    )
    parent["pivot"] = json.dumps(
        [{"type_service_local": "mairie", "code_insee_commune": ["75056"]}]
    )

    entite = module.canonicaliser_service(
        parent,
        "2026-10-06T12:00:00+00:00",
    )
    relations, anomalies = module.construire_relations_locales(
        [parent, enfant],
        {parent["id"], enfant_id},
        {},
        "2026-10-06T12:00:00+00:00",
    )

    assert entite["territoires"] == ["75056"]
    assert entite["types_service_local"] == ["mairie"]
    assert len(relations) == 1
    assert anomalies == []


def test_empreinte_semantique_est_independante_de_l_ordre():
    a = service_exemple()
    b = service_exemple("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    assert module.empreinte_semantique_export([a, b]) == module.empreinte_semantique_export([b, a])


def test_relation_inchangee_conserve_ses_dates():
    parent = service_exemple()
    enfant_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    enfant = service_exemple(enfant_id)
    parent["hierarchie"] = [
        {"type_hierarchie": "Service Fils", "service": enfant_id}
    ]

    premieres, _ = module.construire_relations_locales(
        [parent, enfant],
        {parent["id"], enfant_id},
        {},
        "2026-10-06T12:00:00+00:00",
    )
    assert len(premieres) == 1
    index = {premieres[0]["id"]: premieres[0]}

    secondes, _ = module.construire_relations_locales(
        [parent, enfant],
        {parent["id"], enfant_id},
        {},
        "2026-10-07T12:00:00+00:00",
        precedentes=index,
    )

    assert secondes[0]["observe_le"] == "2026-10-06T12:00:00+00:00"
    assert (
        secondes[0]["provenance"][0]["collecte_le"]
        == "2026-10-06T12:00:00+00:00"
    )
    assert (
        secondes[0]["qualificatifs"]["representation_source"]
        == parent["hierarchie"][0]
    )


def test_resolution_croisee_conserve_les_deux_preuves(monkeypatch):
    parent_id = "11111111-2222-3333-4444-555555555555"
    enfant_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    anomalie = {
        "type": "LIEN_HIERARCHIQUE_NON_RESOLU",
        "parent_id_dila": parent_id,
        "type_hierarchie_dila": "Service Fils",
        "candidats_id": [enfant_id],
        "representation_source": {
            "type_hierarchie": "Service Fils",
            "service": enfant_id,
        },
    }
    monkeypatch.setattr(module, "charger_anomalies_roae", lambda: [anomalie])

    relations, rapport = module.resoudre_anomalies_roae(
        {enfant_id},
        {parent_id: "FRONTIERE-INST-DILA-PARENT"},
        "2026-10-06T12:00:00+00:00",
        empreintes_locales={enfant_id: "empreinte-locale"},
    )

    assert rapport["resolues_par_annuaire_local"] == 1
    assert rapport["restantes_apres_croisement"] == 0
    assert len(relations) == 1

    relation = relations[0]
    assert relation["qualificatifs"]["representation_source"] == anomalie[
        "representation_source"
    ]
    assert [p["source_id"] for p in relation["provenance"]] == [
        "dila_roae",
        "dila_annuaire_local",
    ]
    assert relation["provenance"][0]["url"] == module.PAGE_SOURCE_ROAE
    assert relation["provenance"][1]["url"] == module.PAGE_SOURCE
    assert relation["provenance"][1]["empreinte"] == "empreinte-locale"


def test_dependance_roae_participe_a_la_detection_d_un_etat_inchange(
    tmp_path,
    monkeypatch,
):
    manifeste_local = tmp_path / "annuaire.json"
    manifeste_local.write_text(
        json.dumps(
            {
                "sha256_semantique_export": "annuaire-hash",
                "version_transformation": module.VERSION_TRANSFORMATION,
                "empreinte_dependance_roae": "roae-hash",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "MANIFESTE", manifeste_local)

    assert module.source_deja_traitee("annuaire-hash", "roae-hash") is True
    assert module.source_deja_traitee("annuaire-hash", "autre-roae") is False


def test_empreinte_dependance_roae_change_avec_la_source_ou_la_transformation(
    tmp_path,
    monkeypatch,
):
    manifeste_roae = tmp_path / "roae.json"
    donnees = {
        "sha256_zip": "source-a",
        "version_transformation": "1.2",
        "nombre_services": 7903,
        "nombre_relations": 8071,
    }
    manifeste_roae.write_text(json.dumps(donnees), encoding="utf-8")
    monkeypatch.setattr(module, "MANIFESTE_ROAE", manifeste_roae)

    premiere = module.empreinte_dependance_roae()
    donnees["version_transformation"] = "1.3"
    manifeste_roae.write_text(json.dumps(donnees), encoding="utf-8")
    seconde = module.empreinte_dependance_roae()

    assert premiere != seconde
