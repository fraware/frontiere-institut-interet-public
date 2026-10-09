"""Tester l'identification de nouvelles origines sans visite de domaine."""
import pytest

from scripts.inventorier_domaines_sources import (
    extraire_domaine, inventorier,
)


def test_domaines_par_site_et_jeu_distinct():
    donnees = {"candidats": [
        {"id": "jeu-1", "ressources": [
            {"url": "https://donnees.institution.gouv.fr/fichier/a.csv"},
            {"url": "https://donnees.institution.gouv.fr/fichier/b.csv"},
            {"url": "https://static.data.gouv.fr/resource/c.csv"},
        ]},
        {"id": "jeu-2", "ressources": [
            {"url": "https://donnees.institution.gouv.fr/fichier/c.csv"},
        ]},
    ]}
    sources = {"sources": [{"page_url": "https://static.data.gouv.fr/datasets/jeu/"}]}
    output = inventorier(donnees, sources, instant="2026-10-09T18:00:00Z")
    assert output["nombre_domaines_distincts"] == 2
    assert output["nombre_domaines_hors_registre"] == 1
    assert output["nouvelle_source_automatiquement_aspiree"] is False
    item = next(x for x in output["domaines"] if x["domaine"] == "donnees.institution.gouv.fr")
    assert item["nombre_jeux_distincts"] == 2
    assert item["nombre_references_ressources"] == 3
    assert item["connexion_automatique_autorisee"] is False


@pytest.mark.parametrize("url", [
    "file:///etc/passwd", "http://localhost/test", "http://127.0.0.1/a",
    "http://user:password@public.example.fr/secret",
    "https://site.local/data", "https://192.168.1.12/page",
])
def test_adresses_non_publiques_rejetees(url):
    assert extraire_domaine(url) is None


def test_entree_vide_est_un_inventaire_vide_pas_une_preuve_de_couverture():
    result = inventorier({"candidats": []}, {"sources": []}, instant="2026-10-09")
    assert result["nombre_domaines_distincts"] == 0
    assert result["nouvelle_source_automatiquement_aspiree"] is False
