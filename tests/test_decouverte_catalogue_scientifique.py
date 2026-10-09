"""Découverte du catalogue scientifique : tests sans réseau ni données individuelles."""
from urllib.parse import parse_qs, urlparse

import pytest

from scripts.decouvrir_catalogue_scientifique import (
    EchecCatalogue, executer, notice, url_page,
)


def fiche(identifiant="fr-esr-exemple"):
    return {"dataset": {
        "dataset_id": identifiant,
        "metas": {"default": {
            "title": "Unités de recherche publiques",
            "license": "Licence Ouverte",
            "modified": "2026-10-09",
        }},
        "fields": [{"name": "non_collecte", "sample": "Donnée privée fictive"}],
    }}


def test_notice_ne_conserve_que_les_metadonnees():
    n = notice(fiche())
    assert n["id"] == "fr-esr-exemple"
    assert n["titre"] == "Unités de recherche publiques"
    assert n["page"].startswith("https://data.enseignementsup-recherche.gouv.fr/")
    assert "fields" not in n
    assert "non_collecte" not in str(n)
    assert n["donnees_brutes_copiees"] is False


def test_consultation_paginee_du_catalogue():
    adresse = url_page(50, 50)
    assert parse_qs(urlparse(adresse).query) == {"offset": ["50"], "limit": ["50"]}
    assert urlparse(adresse).hostname == "mesr.opendatasoft.com"
    with pytest.raises(EchecCatalogue):
        url_page(-1, 50)


def test_un_cycle_complet_masque_les_contenus_bruts():
    def api(url):
        off = int(parse_qs(urlparse(url).query)["offset"][0])
        return {"total_count": 3, "datasets": [fiche("esr-1"), fiche("esr-2"), fiche("esr-3")][off:off + 3]}

    res, etat = executer(
        {"notices": []}, obtenir=api, attente=lambda x: None,
        instant="2026-10-09T18:00:00+00:00", pages=3, taille=3,
    )
    assert etat["exhaustivite_constatee"] is True
    assert etat["pages_reussies"] == 1
    assert etat["nouvelles_notices"] == 3
    assert etat["donnees_brutes_copiees"] is False
    assert len(res["notices"]) == 3


def test_erreur_conserve_les_anciennes_notices():
    sauvegarde = {"notices": [notice(fiche("esr-deja-suivi"))]}
    def api(url):
        raise OSError("Panne artificielle")

    resultat, etat = executer(sauvegarde, obtenir=api, attente=lambda x: None)
    assert etat["pages_reussies"] == 0
    assert etat["pages_echouees"] == 1
    assert len(resultat["notices"]) == 1
    assert resultat["notices"][0]["id"] == "esr-deja-suivi"
    assert etat["exhaustivite_constatee"] is False


def test_identifiant_ou_notice_incorrecte_refusee():
    assert notice(fiche("../../autre")) is None
    assert notice({"dataset": {"dataset_id": "okay"}})["id"] == "okay"



def test_echec_total_affiche_la_cause_sans_modifier_les_notices(monkeypatch, tmp_path, capsys):
    import sys
    import scripts.decouvrir_catalogue_scientifique as col

    sortie = tmp_path / "catalogue_mesr.json"
    etat = tmp_path / "catalogue_mesr_etat.json"
    sortie.write_text('{"notices":[{"id":"ancienne-notice"}]}', encoding="utf-8")
    avant = sortie.read_bytes()

    monkeypatch.setattr(col, "SORTIE", sortie)
    monkeypatch.setattr(col, "ETAT", etat)
    monkeypatch.setattr(
        col, "executer",
        lambda ancien: (
            ancien,
            {"pages_reussies": 0, "erreurs": [{"page": 1, "motif": "HTTP_403"}]},
        ),
    )
    monkeypatch.setattr(sys, "argv", ["decouvrir_catalogue_scientifique.py"])
    with pytest.raises(SystemExit) as e:
        col.main()
    assert e.value.code == 1
    assert "HTTP_403" in capsys.readouterr().err
    assert sortie.read_bytes() == avant
    assert not etat.exists()
