"""Essais du collecteur BOAMP connecté à la base, sans réseau."""
from datetime import datetime, timedelta, timezone
import json

import pytest

from app.collecteur_boamp_continu import FICHIER, _ancien_releve, cycle
from app.plateforme_boamp import StockageBOAMP


def date_utc(heure=0):
    return datetime(2026, 10, 14, heure, 0, tzinfo=timezone.utc)


def api_avec_objet(objet):
    def obtenir(url, _origine):
        return {"total_count": 2, "results": [
            {"idweb": "26-1", "objet": objet, "nomacheteur": "Institut public",
             "dateparution": "2026-10-14", "datelimitereponse": "2026-11-01",
             "type_marche": ["SERVICES"], "etat": "INITIAL",
             "url_avis": "https://www.boamp.fr/avis/26-1"},
            {"idweb": "26-2", "objet": "Analyse des données",
             "nomacheteur": "Ministère fictif",
             "dateparution": "2026-10-14", "datelimitereponse": "2026-11-02",
             "type_marche": ["SERVICES"], "etat": "INITIAL",
             "url_avis": "https://www.boamp.fr/avis/26-2"},
        ]}
    return obtenir


def test_collecte_en_ligne_simulee_puis_reprise(tmp_path):
    base = StockageBOAMP("sqlite:///" + str(tmp_path / "avis.db"))
    dossier = tmp_path / "captures"
    premier = cycle(base, dossier, maintenant=date_utc(),
                    obtenir=api_avec_objet("Calcul avancé"), attendre=lambda _: None)
    assert premier["nouvelle_capture"] is True
    assert premier["recherche_partielle"] is False
    assert premier["avis_en_base"] == 2
    assert (dossier / FICHIER).is_file()
    second = cycle(base, dossier, maintenant=date_utc(1),
                   obtenir=api_avec_objet("Calcul avancé"), attendre=lambda _: None)
    assert second["nouvelle_capture"] is False
    assert base.etat()["versions_distinctes"] == 2
    troisieme = cycle(base, dossier, maintenant=date_utc(2),
                     obtenir=api_avec_objet("Calcul renouvelé"), attendre=lambda _: None)
    assert troisieme["nouvelle_capture"] is True
    assert base.etat()["avis_distincts"] == 2
    assert base.etat()["versions_distinctes"] == 3
    assert base.rechercher("renouvelé")[0]["identifiant"] == "26-1"
    assert not base.rechercher("avancé")


def test_panne_source_ne_detruit_pas_l_historique(tmp_path):
    base = StockageBOAMP("sqlite:///" + str(tmp_path / "avis.db"))
    dossier = tmp_path / "captures"
    cycle(base, dossier, maintenant=date_utc(),
          obtenir=api_avec_objet("Science"), attendre=lambda _: None)
    avant = (dossier / FICHIER).read_bytes()
    def panne(*_):
        raise OSError("Indisponibilité simulée")
    with pytest.raises(ValueError, match="Aucune page BOAMP"):
        cycle(base, dossier, maintenant=date_utc(1),
              obtenir=panne, attendre=lambda _: None)
    assert (dossier / FICHIER).read_bytes() == avant
    assert base.etat()["avis_distincts"] == 2


def test_source_partielle_indique_sa_couverture(tmp_path):
    base = StockageBOAMP("sqlite:///" + str(tmp_path / "avis.db"))
    def api(_url, _origine):
        return {"total_count": 200, "results": [
            {"idweb": f"26-{i}", "objet": "Capacité technique",
             "nomacheteur": "Organisme",
             "dateparution": "2026-10-14", "type_marche": ["SERVICES"]}
            for i in range(100)
        ]}
    resultat = cycle(base, tmp_path / "captures", maintenant=date_utc(),
                     pages=1, obtenir=api, attendre=lambda _: None)
    assert resultat["recherche_partielle"] is True
    assert resultat["avis_en_base"] == 100


def test_releve_ancien_ne_recharge_pas_toutes_les_annees(tmp_path):
    dossier = tmp_path / "captures"
    dossier.mkdir()
    snapshot = {"version": "boamp-direct-persistant-v1", "releve": {
        "annonces": [
            {"id": "ancien", "date_parution": "2026-09-01"},
            {"id": "recent", "date_parution": "2026-10-14"},
        ]}, "rapport": {}}
    (dossier / FICHIER).write_text(json.dumps(snapshot), encoding="utf-8")
    ancien = _ancien_releve(dossier / FICHIER, date_utc())
    assert [x["id"] for x in ancien["annonces"]] == ["recent"]
