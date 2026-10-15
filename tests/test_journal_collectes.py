"""Vérifier que l'ordonnanceur atteste ses passages et expose leurs limites."""
import sqlite3
import threading

import pytest
from fastapi.testclient import TestClient

from app.exploitation_hebergee import (
    catalogue_commandes, executer_avec_journal, ordonnanceur,
)
from app.journal_collectes import JournalCollectes, derniere_activite
from app.recherche_nationale import Chemins, creer_application


def test_etats_distincts_et_derniere_reussite(tmp_path):
    chemin = tmp_path / "passages.sqlite3"
    journal = JournalCollectes(chemin)
    a = journal.commencer("boamp")
    journal.conclure(a, 0)
    b = journal.commencer("boamp")
    journal.conclure(b, 1)
    c = journal.commencer("emplois")
    journal.conclure(c, None)
    d = journal.commencer("decp")
    journal.conclure(d, None, erreur_type="OSError")
    resultat = derniere_activite(chemin)
    assert resultat["etat"] == "accessible"
    assert resultat["sources"]["boamp"]["nombre_echecs_observes"] == 1
    assert resultat["sources"]["boamp"]["derniere_reussite_le"]
    assert resultat["sources"]["boamp"]["dernier_passage"]["etat"] == "echec"
    assert resultat["sources"]["emplois"]["dernier_passage"]["etat"] == "interrompu"
    assert resultat["sources"]["decp"]["dernier_passage"]["erreur_type"] == "OSError"
    assert {p["etat"] for p in resultat["derniers_passages"]} == {
        "reussite", "echec", "interrompu",
    }
    with pytest.raises(ValueError, match="déjà terminée"):
        journal.conclure(a, 0)


def test_l_absence_ne_cree_aucune_base(tmp_path):
    chemin = tmp_path / "absent.sqlite3"
    assert derniere_activite(chemin)["etat"] == "non_configure"
    assert not chemin.exists()
    with pytest.raises(ValueError):
        derniere_activite(chemin, limite=0)


def test_le_journal_survit_a_une_exception_du_collecteur(tmp_path):
    etape = catalogue_commandes(tmp_path)[1][0]
    def echec(_etape, _arret):
        raise OSError("détail qui ne doit pas entrer dans le journal")
    with pytest.raises(OSError):
        executer_avec_journal(tmp_path, etape, threading.Event(), echec)
    activite = derniere_activite(tmp_path / "exploitation/passages.sqlite3")
    dernier = activite["sources"]["boamp"]["dernier_passage"]
    assert dernier["etat"] == "echec"
    assert dernier["erreur_type"] == "OSError"
    assert "détail" not in str(activite)


def test_un_journal_non_accessible_n_interrompt_pas_la_collecte(tmp_path):
    chemin = tmp_path / "exploitation"
    chemin.write_text("empêche la création du dossier", encoding="utf-8")
    etape = catalogue_commandes(tmp_path)[1][0]
    code = executer_avec_journal(
        tmp_path, etape, threading.Event(),
        lambda _etape, _arret: 0,
    )
    assert code == 0


def test_ordonnanceur_journalise_les_quatre_passages(tmp_path):
    arret = threading.Event()
    appels = []
    def faire(etape, _arret):
        appels.append(etape.nom)
        if len(appels) == 4:
            arret.set()
        return 0
    ordonnanceur(tmp_path, arret, initialiser=False, executant=faire)
    etat = derniere_activite(tmp_path / "exploitation/passages.sqlite3")
    assert len(etat["derniers_passages"]) == 4
    assert all(x["etat"] == "reussite" for x in etat["derniers_passages"])


def test_route_collectes_et_secret_herites(tmp_path, monkeypatch):
    chemin = tmp_path / "passages.sqlite3"
    journal = JournalCollectes(chemin)
    identifiant = journal.commencer("emplois")
    journal.conclure(identifiant, 0)
    monkeypatch.setenv("FRONTIERE_JOURNAL_COLLECTES", str(chemin))
    monkeypatch.setenv("FRONTIERE_CONTROLE_ACCES_OBLIGATOIRE", "1")
    jeton = "jeton-de-test-assez-long-pour-les-recherches-privees"
    monkeypatch.setenv("FRONTIERE_JETON_ACCES", jeton)
    client = TestClient(creer_application(Chemins()))
    assert client.get("/collectes").status_code == 401
    resultat = client.get(
        "/collectes", headers={"Authorization": "Bearer " + jeton}
    )
    assert resultat.status_code == 200
    assert resultat.json()["sources"]["emplois"]["derniere_reussite_le"]
    assert client.get("/sante").status_code == 200
