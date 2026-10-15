"""Tests de recherche fédérée, sans service réseau ni jeux de données externes."""
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient

from app.recherche_nationale import (
    Chemins, creer_application, etat, rechercher,
)


def base(path: Path, instructions: str):
    with sqlite3.connect(path) as conn:
        conn.executescript(instructions)
    return path


def sources(tmp_path) -> Chemins:
    boamp = base(tmp_path / "boamp.db", """
        CREATE TABLE avis_boamp(
          identifiant TEXT,objet TEXT,acheteur TEXT,date_parution TEXT,
          avis TEXT,empreinte TEXT
        );
        CREATE TABLE captures_boamp(observe_le TEXT);
        INSERT INTO avis_boamp VALUES
        ('26-100','Informatique des laboratoires','Institut national','2026-10-14',
         'https://www.boamp.fr/avis/26-100','sha-boamp');
        INSERT INTO captures_boamp VALUES ('2026-10-14T12:00:00+00:00');
    """)
    emplois = base(tmp_path / "emplois.db", """
        CREATE TABLE versions_emplois_publics(
          reference TEXT,intitule TEXT,organisme TEXT,employeur TEXT,
          metier TEXT,competences TEXT,empreinte TEXT
        );
        CREATE TABLE apparitions_emplois_publics(
          source_id TEXT,sha256_csv TEXT,empreinte TEXT
        );
        CREATE TABLE captures_emplois_publics(
          source_id TEXT,sha256_csv TEXT,observe_le TEXT
        );
        INSERT INTO versions_emplois_publics VALUES
          ('O-123','Ingénieur informatique','Ministère','Ministère',
           'Ingénieur','Traitement statistique','sha-job-a');
        INSERT INTO versions_emplois_publics VALUES
          ('O-123','Ingénieur ancien','Ministère','Ministère',
           'Ingénieur','informatique','sha-job-old');
        INSERT INTO apparitions_emplois_publics VALUES
          ('jeu','nouveau','sha-job-a');
        INSERT INTO apparitions_emplois_publics VALUES
          ('jeu','ancien','sha-job-old');
        INSERT INTO captures_emplois_publics VALUES
          ('jeu','ancien','2026-09-01T00:00:00Z');
        INSERT INTO captures_emplois_publics VALUES
          ('jeu','nouveau','2026-10-14T00:00:00Z');
    """)
    decp = base(tmp_path / "decp.db", """
        CREATE TABLE versions(
          acheteur_siret TEXT,id_marche TEXT,objet TEXT,code_cpv TEXT,
          date_publication_declaree TEXT,montant_euros_ht REAL,empreinte_version TEXT
        );
        CREATE TABLE attestations(observe_le TEXT);
        CREATE VIRTUAL TABLE recherche_marches USING fts5(cle UNINDEXED,objet);
        INSERT INTO versions VALUES
          ('21750001630066','CONTRAT-1','Services informatiques',
           '72000000-5','2026-10-13',95000.0,'sha-decp');
        INSERT INTO recherche_marches VALUES
          ('21750001630066' || char(31) || 'CONTRAT-1' || char(31) || 'sha-decp',
           'Services informatiques');
        INSERT INTO attestations VALUES ('2026-10-14T04:00:00Z');
    """)
    return Chemins(boamp=boamp, emplois=emplois, decp=decp)


def test_trois_sources_recherchees_independamment(tmp_path):
    resultats = rechercher(sources(tmp_path), "informati", limite=10)
    assert {x["source"] for x in resultats["resultats"]} == {
        "boamp", "emplois", "decp"
    }
    assert resultats["nombre_retourne"] == 3
    assert all(v == "accessible" for v in resultats["sources"].values())
    contrats = [x for x in resultats["resultats"] if x["source"] == "decp"]
    assert contrats[0]["montant_euros_ht"] == 95000
    assert contrats[0]["url_document"] is None
    assert contrats[0]["nature"] == "marché attribué"
    emplois = [x for x in resultats["resultats"] if x["source"] == "emplois"]
    assert emplois[0]["identifiant"] == "O-123"
    assert emplois[0]["date_publication"] is None
    assert emplois[0]["url_document"] is None


def test_troncature_limites_et_filtre_sur_source(tmp_path):
    chemins = sources(tmp_path)
    reponse = rechercher(chemins, "informati", limite=2)
    assert reponse["nombre_retourne"] == 2
    assert reponse["troncature_par_limite"] is True
    seul = rechercher(chemins, "informati", sources=("emplois",))
    assert len(seul["resultats"]) == 1
    assert seul["resultats"][0]["source"] == "emplois"
    assert list(seul["sources"]) == ["emplois"]


def test_absence_de_fichier_et_schema_incompatible(tmp_path):
    configuration = Chemins(
        emplois=tmp_path / "absent.db",
        boamp=base(tmp_path / "incorrect.db", "CREATE TABLE inconnu(x INTEGER);"),
    )
    resultat = rechercher(configuration, "physique")
    assert resultat["resultats"] == []
    assert resultat["sources"]["emplois"] == "non_configure"
    assert resultat["sources"]["boamp"] == "schema_incompatible"
    suivi = etat(configuration)
    assert suivi["decp"]["etat"] == "non_configure"
    assert suivi["boamp"]["etat"] == "schema_incompatible"


def test_les_bases_sont_en_lecture_seule(tmp_path):
    c = sources(tmp_path)
    avant = (tmp_path / "decp.db").read_bytes()
    rechercher(c, "informati")
    assert (tmp_path / "decp.db").read_bytes() == avant


def test_api_et_codes_de_validation(tmp_path):
    client = TestClient(creer_application(sources(tmp_path)))
    r = client.get("/recherche", params={"q": "informati", "limite": 10})
    assert r.status_code == 200
    assert r.json()["nombre_retourne"] == 3
    r = client.get("/recherche", params={"q": "informati", "source": "emplois"})
    assert r.status_code == 200
    assert r.json()["resultats"][0]["source"] == "emplois"
    assert client.get("/recherche", params={"q": "informati", "source": "inconnue"}).status_code == 422
    assert client.get("/recherche", params={"q": "informati", "limite": 101}).status_code == 422
    statut = client.get("/sante").json()
    assert statut["sources"]["emplois"]["etat"] == "accessible"
    assert "derniere_observation" in client.get("/sources").json()["boamp"]


def test_les_jokers_sql_sont_traites_comme_texte(tmp_path):
    c = sources(tmp_path)
    assert rechercher(c, "%")["resultats"] == []
    assert rechercher(c, "_")["resultats"] == []
