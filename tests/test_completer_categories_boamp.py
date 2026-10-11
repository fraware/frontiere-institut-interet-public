"""Essais des compléments BOAMP historiques à dates et empreintes constantes."""
from datetime import date, datetime, timezone
import gzip
import json
from urllib.parse import parse_qs, urlparse

import pytest

from scripts.collecter_besoins_publics import notice_boamp
from scripts.collecter_historique_boamp import publier_jour, chemins_jour
from scripts.completer_categories_boamp import (
    executer, chemins, verifier_complement, lire_categories, CategoriesIncompletes,
)


def record(id, jour, objet, categorie):
    return {
        "idweb": id, "dateparution": jour, "objet": objet,
        "nomacheteur": "Laboratoire public fictif",
        "type_marche": categorie, "etat": "INITIAL",
        "url_avis": f"https://www.boamp.fr/pages/avis/?q=idweb:{id}",
    }


def jour_initial(tmp_path):
    jour = "2026-10-01"
    t0 = datetime(2026, 10, 8, tzinfo=timezone.utc)
    initial = [
        record("26-10", jour, "Instrumentation", ["FOURNITURES"]),
        record("26-11", jour, "Analyse", ["SERVICES"]),
    ]
    publier_jour(
        tmp_path, date.fromisoformat(jour),
        [notice_boamp(n) for n in initial], len(initial), t0,
    )
    return jour, initial


def serve_api(jour, donnees):
    def requete(url, origine):
        q = parse_qs(urlparse(url).query)
        assert q["select"] == ["idweb,dateparution,type_marche"]
        assert jour in q["where"][0]
        start = int(q["offset"][0])
        end = start + int(q["limit"][0])
        return {"total_count": len(donnees), "results": donnees[start:end]}
    return requete


def test_enrichissement_identifiants_changes_et_immutabilite(tmp_path):
    jour, originaux = jour_initial(tmp_path)
    archive_originale, fiche = chemins_jour(tmp_path, date.fromisoformat(jour))
    avant = archive_originale.read_bytes()
    # Un identifiant a disparu de la source ; un nouvel avis y apparaît.
    source = [
        record("26-10", jour, "Instrumentation", ["FOURNITURES"]),
        record("26-12", jour, "Nouvel objet", ["SERVICES"]),
    ]
    instant = datetime(2026, 10, 11, tzinfo=timezone.utc)
    bilan = executer(tmp_path, instant=instant, obtenir=serve_api(jour, source),
                     patienter=lambda _: None, jours_par_execution=1)
    assert bilan["jours_nouveaux"] == 1
    assert bilan["complements"][0]["categories_renseignees"] == 1
    assert bilan["complements"][0]["absents_source"] == 1
    assert archive_originale.read_bytes() == avant
    paquet, manifeste = chemins(tmp_path, jour)
    assert paquet.is_file() and manifeste.is_file()
    infos = verifier_complement(tmp_path, fiche)
    assert infos["archive_originale_sha256_gzip"] == json.loads(
        fiche.read_text(encoding="utf-8")
    )["sha256_archive_gzip"]
    assert infos["nombre_identifiants_ajoutes_depuis_initial"] == 1
    assert infos["nombre_identifiants_absents_depuis_initial"] == 1
    contenu = [json.loads(l) for l in gzip.decompress(paquet.read_bytes()).splitlines()]
    assert contenu == [
        {"categorie_marche": "FOURNITURES", "id": "26-10",
         "present_dans_releve_complementaire": True},
        {"categorie_marche": None, "id": "26-11",
         "present_dans_releve_complementaire": False},
    ]
    assert not infos["photographie_initiale_modifiee"]
    assert not infos["date_origine_de_la_categorie_etablie"]

    def interdit(*args):
        raise AssertionError("Aucune relecture d'un complément déjà vérifié.")
    suite = executer(tmp_path, instant=instant, obtenir=interdit,
                     patienter=lambda _: None, jours_par_execution=1)
    assert suite["jours_nouveaux"] == 0
    paquet.write_bytes("fichier altéré".encode("utf-8"))
    with pytest.raises(CategoriesIncompletes, match="Empreinte|Taille"):
        executer(tmp_path, instant=instant, obtenir=interdit,
                 patienter=lambda _: None, jours_par_execution=1)
    assert archive_originale.read_bytes() == avant


def test_type_categorie_ambigu_et_page_complete(tmp_path):
    jour, _ = jour_initial(tmp_path)
    val = [record("26-10", jour, "A", ["SERVICES", "FOURNITURES"]),
           record("26-11", jour, "B", ["SERVICES"])]
    nouvelles, compte = lire_categories(date.fromisoformat(jour),
                                       obtenir=serve_api(jour, val),
                                       patienter=lambda _: None)
    assert compte == 2
    assert nouvelles == {"26-10": None, "26-11": "SERVICES"}


@pytest.mark.parametrize("genre", ["total_instable", "date_invalide", "identifiant_double"])
def test_interruption_par_source_non_exhaustive(tmp_path, genre):
    jour, _ = jour_initial(tmp_path)
    def api(url, source):
        q = parse_qs(urlparse(url).query)
        offset = int(q["offset"][0])
        if genre == "total_instable":
            return {"total_count": 101 if offset else 102,
                    "results": [record(f"26-{i}", jour, "A", ["SERVICES"])
                                for i in range(offset, min(102, offset + 100))]}
        if genre == "date_invalide":
            return {"total_count": 1, "results": [
                record("26-10", "2025-09-10", "A", ["SERVICES"]),
            ]}
        return {"total_count": 2, "results": [
            record("26-10", jour, "A", ["SERVICES"]),
            record("26-10", jour, "A", ["SERVICES"]),
        ]}
    with pytest.raises(CategoriesIncompletes):
        executer(tmp_path, instant=datetime(2026, 10, 11, tzinfo=timezone.utc),
                 obtenir=api, patienter=lambda _: None, jours_par_execution=1)
    assert not (tmp_path / "etat_categories_boamp.json").exists()
    assert not list((tmp_path / "categories_boamp").glob("**/*.jsonl.gz"))
