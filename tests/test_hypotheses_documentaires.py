"""Tests des hypothèses entre avis BOAMP et TED, sans lien juridique inféré."""
import sqlite3

from fastapi.testclient import TestClient

from app.hypotheses_documentaires import mesure, rapprocher
from app.recherche_nationale import Chemins, creer_application


def corpus(tmp_path):
    boamp = tmp_path / "boamp.sqlite3"
    ted = tmp_path / "ted.sqlite3"
    with sqlite3.connect(boamp) as conn:
        conn.executescript("""
            CREATE TABLE captures_boamp(observe_le TEXT);
            CREATE TABLE avis_boamp(
                identifiant TEXT, objet TEXT, acheteur TEXT, date_parution TEXT,
                avis TEXT, empreinte TEXT
            );
            INSERT INTO avis_boamp VALUES (
                'B2026-1',
                'Fourniture équipements scientifiques informatiques spécialisés',
                'Université de Paris', '2026-10-12',
                'https://www.boamp.fr/avis/B2026-1', 'preuve-boamp'
            );
            INSERT INTO avis_boamp VALUES (
                'B2026-2',
                'Étude statistique appliquée à la navigation informatique',
                'Université de Paris', '2026-10-11',
                'https://www.boamp.fr/avis/B2026-2', 'preuve-secondaire'
            );
        """)
    with sqlite3.connect(ted) as conn:
        conn.executescript("""
            CREATE TABLE captures_ted(observe_le TEXT);
            CREATE TABLE avis_ted(
                numero TEXT,titre TEXT,acheteur TEXT,date_publication TEXT,
                source_url TEXT,codes_cpv TEXT,empreinte_courante TEXT
            );
            INSERT INTO avis_ted VALUES (
                '12345-2026',
                'Étude équipements scientifiques informatiques spécialisés',
                'Universite de Paris','2026-10-16',
                'https://ted.europa.eu/fr/notice/-/detail/12345-2026',
                '73000000','preuve-ted'
            );
            INSERT INTO avis_ted VALUES (
                '12346-2026',
                'Étude équipements scientifiques informatiques spécialisés',
                'Université de Marseille','2026-10-16',
                'https://ted.europa.eu/fr/notice/-/detail/12346-2026',
                '73000000','preuve-ted-autre'
            );
        """)
    return Chemins(boamp=boamp, ted=ted)


def test_hypothese_tracee_et_qualification_constante(tmp_path):
    resultat = rapprocher(corpus(tmp_path), "informati")
    assert resultat["qualification"] == "hypotheses_uniquement"
    assert resultat["liens_contractuels_etablis"] == 0
    assert resultat["propositions_identifiees"] == 1
    candidat = resultat["resultats"][0]
    assert candidat["qualification"] == "hypothese_documentaire"
    assert candidat["meme_procedure_etablie"] is False
    assert candidat["identite_institutionnelle_etablie"] is False
    assert candidat["preuves"]["ecart_dates_publication_jours"] == 4
    assert candidat["preuves"]["similarite_jaccard_titres"] >= 0.65
    assert candidat["avis_boamp"]["identifiant"] == "B2026-1"
    assert candidat["avis_ted"]["identifiant"] == "12345-2026"
    assert candidat["avis_boamp"]["empreinte_version"] == "preuve-boamp"


def test_homonyme_et_titre_court_refuses():
    b = {
        "source": "boamp", "identifiant": "B-1",
        "titre": "Services informatiques", "organisme": "Ville de Paris",
        "date_publication": "2026-10-12", "url_document": None,
    }
    t = {
        "source": "ted", "identifiant": "T-1",
        "titre": "Services informatiques", "organisme": "Ville de Paris",
        "date_publication": "2026-10-13", "url_document": None,
    }
    assert mesure(b, t) is None  # Trop peu de termes discriminants
    b["titre"] = "Équipements scientifiques informatiques spécialisés"
    t["titre"] = "Equipements scientifiques informatiques specialises"
    t["organisme"] = "Ville de Lyon"
    assert mesure(b, t) is None
    t["organisme"] = "Ville de Paris"
    t["date_publication"] = "2025-01-01"
    assert mesure(b, t) is None


def test_corpus_absent_est_signale_sans_creer_de_lien():
    resultat = rapprocher(Chemins(), "équipements")
    assert resultat["resultats"] == []
    assert resultat["sources"] == {
        "boamp": "non_configure",
        "ted": "non_configure",
    }


def test_api_restitue_les_pieces_et_garde_l_acces_prive(tmp_path, monkeypatch):
    monkeypatch.setenv("FRONTIERE_CONTROLE_ACCES_OBLIGATOIRE", "1")
    token = "secret-de-consultation-frontiere-de-test-au-moins-32"
    monkeypatch.setenv("FRONTIERE_JETON_ACCES", token)
    client = TestClient(creer_application(corpus(tmp_path)))
    assert client.get(
        "/hypotheses/boamp-ted", params={"q": "informati"}
    ).status_code == 401
    resultat = client.get(
        "/hypotheses/boamp-ted", params={"q": "informati"},
        headers={"Authorization": "Bearer " + token},
    )
    assert resultat.status_code == 200
    assert resultat.json()["propositions_identifiees"] == 1
    assert resultat.json()["resultats"][0]["qualification"] == "hypothese_documentaire"
    assert client.get(
        "/hypotheses/boamp-ted", params={"q": "info", "limite": 60},
        headers={"Authorization": "Bearer " + token},
    ).status_code == 422
