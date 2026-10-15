"""Périmètre explicite BOAMP, emplois publics, DECP pour l'exploitation active."""
from pathlib import Path

import yaml

from app.etat_exploitation import MESURES, TABLES_NECESSAIRES
from app.exploitation_hebergee import catalogue_commandes
from app.journal_collectes import SOURCES as JOURNAL_SOURCES
from app.recherche_nationale import Chemins, SOURCES as RECHERCHE_SOURCES
from scripts.amorcer_deploiement import SERVICES as COMPOSE_SERVICES
from scripts.sauvegarder_bases import SOURCES as SAUVEGARDE_SOURCES

RACINE = Path(__file__).resolve().parents[1]


def test_les_trois_corpus_sont_seuls_actifs():
    attendus = {"boamp", "emplois", "decp"}
    assert set(RECHERCHE_SOURCES) == attendus
    assert set(SAUVEGARDE_SOURCES) == attendus
    assert set(MESURES) == attendus
    assert set(TABLES_NECESSAIRES) == attendus
    assert set(Chemins.__dataclass_fields__) == attendus


def test_ordonnanceur_ne_lance_aucun_flux_europeen(tmp_path):
    amorcage, cycles = catalogue_commandes(tmp_path)
    assert [e.nom for e in amorcage] == [
        "amorcage_boamp", "amorcage_emplois", "amorcage_decp",
    ]
    assert [e.nom for e in cycles] == [
        "boamp", "emplois", "decp", "decp_consolides",
    ]
    assert len(COMPOSE_SERVICES) == 5
    assert len(JOURNAL_SOURCES) == 7
    assert "collecte-ted" not in COMPOSE_SERVICES


def test_configuration_docker_ignore_les_anciens_services_et_volumes():
    document = yaml.safe_load(
        (RACINE / "compose.collecte.yml").read_text(encoding="utf-8")
    )
    assert set(document["services"]) == {
        "collecte-boamp", "collecte-emplois",
        "collecte-decp", "collecte-decp-consolides",
        "consultation", "sauvegarde",
    }
    assert set(document["volumes"]) == {
        "stockage-frontiere-boamp",
        "stockage-frontiere-emplois",
        "stockage-frontiere-decp",
    }
    consultation = document["services"]["consultation"]
    assert set(consultation["environment"]) == {
        "FRONTIERE_BOAMP_DB", "FRONTIERE_EMPLOIS_DB",
        "FRONTIERE_DECP_DB",
    }
    assert len(consultation["volumes"]) == 3
    assert len(document["services"]["sauvegarde"]["volumes"]) == 5


def test_render_est_associe_au_projet_de_l_utilisateur():
    doc = yaml.safe_load((RACINE / "render.yaml").read_text(encoding="utf-8"))
    assert "services" not in doc
    assert len(doc["projects"]) == 1
    projet = doc["projects"][0]
    assert projet["name"] == "Frontiere"
    environnement = projet["environments"][0]
    assert environnement["name"] == "Production"
    assert len(environnement["services"]) == 1
    variables = {
        v["key"] for v in environnement["services"][0]["envVars"]
    }
    assert "FRONTIERE_TED_DB" not in variables
    assert variables >= {
        "FRONTIERE_BOAMP_DB", "FRONTIERE_EMPLOIS_DB",
        "FRONTIERE_DECP_DB", "FRONTIERE_JETON_ACCES",
    }


def test_modules_de_collecte_abandonnes_non_present_dans_image():
    for nom in (
        "collecteur_ted_continu.py",
        "rattrapage_ted.py",
    ):
        assert not (RACINE / "app" / nom).exists()
    assert not (RACINE / "scripts/sonder_ted_reelle.py").exists()
    assert not (RACINE / ".github/workflows/contrat-public-ted.yml").exists()
