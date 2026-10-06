import importlib.util
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
CHEMIN_SCRIPT = RACINE / "scripts" / "rechercher_competence_geographique.py"

spec = importlib.util.spec_from_file_location(
    "rechercher_competence_geographique",
    CHEMIN_SCRIPT,
)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_where_accepte_commune_et_type():
    where = module.construire_where("75056", "mairie")
    assert 'code_insee_commune="75056"' in where
    assert 'code_type_service_local="mairie"' in where


def test_where_refuse_requete_non_bornee():
    try:
        module.construire_where(None, None)
    except ValueError as exc:
        assert "commune" in str(exc).lower()
    else:
        raise AssertionError("Une requête non bornée doit être refusée.")


def test_normaliser_ids_accepte_json_et_liste():
    valeur = '["a", "b"]'
    assert module.normaliser_ids(valeur) == ["a", "b"]
    assert module.normaliser_ids(["a", "b"]) == ["a", "b"]


def test_resolution_utilise_le_graphe_canonique(monkeypatch):
    local = {
        "abc": {
            "id": "FRONTIERE-INST-DILA-LOCAL-ABC",
            "nom_officiel": "Mairie test",
            "type_institutionnel": "Service local — mairie",
        }
    }

    def faux_index(dossier, cle):
        if cle == "dila_local_id":
            return local
        return {}

    monkeypatch.setattr(module, "charger_index", faux_index)

    resultats = module.resoudre(
        [
            {
                "code_insee_commune": "75056",
                "nom_commune": "Paris",
                "code_type_service_local": "mairie",
                "id_service_local": '["abc"]',
            }
        ]
    )

    assert resultats[0]["organismes"][0]["resolu"] is True
    assert resultats[0]["organismes"][0]["nom"] == "Mairie test"
