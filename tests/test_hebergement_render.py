"""Le Blueprint par défaut ne doit engager aucune dépense d'hébergement."""
from pathlib import Path
import yaml

RACINE = Path(__file__).resolve().parents[1]


def services_production():
    document = yaml.safe_load((RACINE / "render.yaml").read_text(encoding="utf-8"))
    assert "services" not in document
    assert len(document["projects"]) == 1
    projet = document["projects"][0]
    assert projet["name"] == "Frontiere"
    assert len(projet["environments"]) == 1
    environnement = projet["environments"][0]
    assert environnement["name"] == "Production"
    return environnement["services"]


def test_blueprint_gratuit_sans_calcul_facture_ni_disque():
    services = services_production()
    assert len(services) == 1
    service = services[0]
    assert service["type"] == "web"
    assert service["runtime"] == "static"
    assert service["name"] == "frontiere-observatoire-public"
    assert service["staticPublishPath"] == "./site_frontiere"
    assert service["buildCommand"] == "node scripts/construire_index_statique.mjs"
    assert service["envVars"] == [{"key": "SKIP_INSTALL_DEPS", "value": "true"}]
    assert service["autoDeployTrigger"] == "off"
    assert service["previews"]["generation"] == "off"

    # Interdire toute réintroduction implicite de la configuration payante.
    for cle in (
        "plan", "disk", "numInstances", "region", "dockerfilePath",
        "dockerContext", "healthCheckPath", "maxShutdownDelaySeconds",
        "startCommand", "preDeployCommand",
    ):
        assert cle not in service, f"Paramètre incompatible avec l'option gratuite : {cle}"


def test_presentation_ne_pretend_pas_collecter_des_donnees():
    page = (RACINE / "site_frontiere/index.html").read_text(encoding="utf-8")
    assert "lang=\"fr\"" in page
    assert "BOAMP" in page
    assert "Emplois publics" in page or "emplois publics" in page
    assert "DECP" in page
    assert "ne collecte pas de données en continu" in page
    assert "temps réel" in page
    assert "TED" not in page


def test_version_node_identique_aux_controles_d_index():
    version = (RACINE / ".node-version").read_text(encoding="utf-8").strip()
    assert version.startswith("22.")
    assert version.count(".") == 2
