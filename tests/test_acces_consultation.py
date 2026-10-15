"""Contrôles HTTP du jeton privé de consultation chez un hébergeur."""
from fastapi.testclient import TestClient

from app.recherche_nationale import Chemins, creer_application

SECRET = "jeton-frontiere-de-test-valide-sur-32-caracteres-avec-suffixe"


def test_configuration_render_sans_secret_refuse_toutes_les_donnees(monkeypatch):
    monkeypatch.setenv("FRONTIERE_CONTROLE_ACCES_OBLIGATOIRE", "1")
    monkeypatch.delenv("FRONTIERE_JETON_ACCES", raising=False)
    client = TestClient(creer_application(Chemins()))
    assert client.get("/sante").status_code == 200
    assert "sources" not in client.get("/sante").json()
    for route in ("/sources", "/exploitation", "/pret", "/docs", "/openapi.json"):
        r = client.get(route)
        assert r.status_code == 503
        assert "non configuré" in r.json()["detail"]
    assert client.get("/recherche", params={"q": "physique"}).status_code == 503


def test_secret_valide_bloque_anonyme_et_autorise_jeton_correct(monkeypatch):
    monkeypatch.setenv("FRONTIERE_CONTROLE_ACCES_OBLIGATOIRE", "1")
    monkeypatch.setenv("FRONTIERE_JETON_ACCES", SECRET)
    client = TestClient(creer_application(Chemins()))
    resultat = client.get("/sources")
    assert resultat.status_code == 401
    assert resultat.headers["www-authenticate"] == "Bearer"
    assert client.get(
        "/sources", headers={"Authorization": "Bearer jeton-incorrect"}
    ).status_code == 401
    attendu = {"Authorization": "Bearer " + SECRET}
    assert client.get("/sources", headers=attendu).status_code == 200
    assert client.get("/exploitation", headers=attendu).status_code == 200
    assert client.get("/recherche", params={"q": "physique"},
                      headers=attendu).status_code == 200
    assert client.get("/docs", headers=attendu).status_code == 200
    assert client.get("/openapi.json", headers=attendu).status_code == 200
    assert client.get("/pret", headers=attendu).status_code == 503
    assert SECRET not in str(client.get("/sante").json())
    assert "sources" not in client.get("/sante").json()


def test_jetons_insuffisants_et_non_ascii_refuses(monkeypatch):
    monkeypatch.setenv("FRONTIERE_CONTROLE_ACCES_OBLIGATOIRE", "1")
    for secret in ("court", "é" * 40):
        monkeypatch.setenv("FRONTIERE_JETON_ACCES", secret)
        client = TestClient(creer_application(Chemins()))
        assert client.get("/sources").status_code == 503
        assert client.get("/sante").status_code == 200


def test_sans_option_hebergee_usage_local_reste_compatible(monkeypatch):
    monkeypatch.delenv("FRONTIERE_CONTROLE_ACCES_OBLIGATOIRE", raising=False)
    monkeypatch.delenv("FRONTIERE_JETON_ACCES", raising=False)
    client = TestClient(creer_application(Chemins()))
    assert client.get("/sources").status_code == 200
    assert "sources" in client.get("/sante").json()
    assert client.get("/recherche", params={"q": "boamp"}).status_code == 200
