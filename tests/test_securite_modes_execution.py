"""Le prototype sans authentification ne doit pas démarrer en production."""
import pytest
from fastapi.testclient import TestClient

from app.main import app, settings, verifier_mode_execution


@pytest.mark.parametrize("nom", ["production", "prod", "staging", "preproduction", "", "inconnu"])
def test_refus_environment_institutionnel_sans_controle_d_acces(nom):
    with pytest.raises(RuntimeError, match="authentification"):
        verifier_mode_execution(nom)


@pytest.mark.parametrize("nom", ["development", "test", "testing"])
def test_modes_experimentaux_autorises_localement(nom):
    verifier_mode_execution(nom)


def test_cycle_de_vie_refuse_vraiment_le_mode_production(monkeypatch):
    monkeypatch.setattr(settings, "env", "production")
    with pytest.raises(RuntimeError, match="Démarrage refusé"):
        with TestClient(app):
            pass


def test_cycle_de_vie_autorise_test_apres_retablissement(monkeypatch):
    monkeypatch.setattr(settings, "env", "test")
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
