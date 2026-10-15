"""Tester la configuration Render et les invariants de l'instance mono-disque."""
from pathlib import Path
import yaml

RACINE = Path(__file__).resolve().parents[1]


def configuration():
    return yaml.safe_load((RACINE / "render.yaml").read_text(encoding="utf-8"))


def test_blueprint_render_et_disque_persistant_unique():
    services = configuration()["services"]
    assert len(services) == 1
    service = services[0]
    assert service["type"] == "web"
    assert service["runtime"] == "docker"
    assert service["region"] == "frankfurt"
    assert service["plan"] != "free"
    assert service["plan"] == "1c-2g"
    assert service["numInstances"] == 1
    assert service["dockerfilePath"] == "./infra/Dockerfile.hebergement"
    assert service["dockerContext"] == "."
    assert service["healthCheckPath"] == "/sante"
    assert service["disk"] == {
        "name": "frontiere-donnees",
        "mountPath": "/var/lib/frontiere",
        "sizeGB": 50,
    }
    assert 30 <= service["maxShutdownDelaySeconds"] <= 300


def test_chemins_des_trois_bases_sur_le_disque_unique():
    env = {
        x["key"]: x["value"]
        for x in configuration()["services"][0]["envVars"]
        if "value" in x
    }
    assert env["FRONTIERE_DONNEES"] == "/var/lib/frontiere"
    assert env["FRONTIERE_COLLECTE_ACTIVE"] == "1"
    assert env["FRONTIERE_AMORCAGE_AUTO"] == "1"
    assert env["FRONTIERE_CONTROLE_ACCES_OBLIGATOIRE"] == "1"
    jeton = next(
        x for x in configuration()["services"][0]["envVars"]
        if x["key"] == "FRONTIERE_JETON_ACCES"
    )
    assert jeton == {"key": "FRONTIERE_JETON_ACCES", "sync": False}
    chemins = [
        env["FRONTIERE_BOAMP_DB"],
        env["FRONTIERE_EMPLOIS_DB"],
        env["FRONTIERE_DECP_DB"],
    ]
    assert len(set(chemins)) == 3
    assert all(p.startswith("/var/lib/frontiere/") for p in chemins)


def test_image_contient_archives_initiales_et_modules_du_service():
    image = (RACINE / "infra/Dockerfile.hebergement").read_text(encoding="utf-8")
    script = (RACINE / "infra/demarrer_hebergement.sh").read_text(encoding="utf-8")
    assert "COPY app/" in image
    assert "COPY scripts/" in image
    assert "COPY institutionnel/besoins_publics/" in image
    assert "COPY institutionnel/decp/" in image
    assert "gosu" in image and "gosu frontiere:frontiere" in script
    assert "python -m app.exploitation_hebergee" in script
    assert "chown frontiere:frontiere" in script
