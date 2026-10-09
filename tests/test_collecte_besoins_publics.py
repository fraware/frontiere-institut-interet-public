"""Les besoins publics sont des annonces et des métadonnées, jamais des contacts privés."""
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from scripts.collecter_besoins_publics import (
    BOAMP, CSP, EchecBesoins, adresse_boamp, notice_boamp,
    notice_ressource_csp, relever_boamp, relever_emplois,
)


def annonce(code="26-12345"):
    return {
        "idweb": code,
        "objet": "Étude de modélisation scientifique",
        "nomacheteur": "Établissement public fictif",
        "dateparution": "2026-10-09",
        "datelimitereponse": "2026-11-10",
        "type_marche": "SERVICES",
        "etat": "INITIAL",
        "url_avis": "https://www.boamp.fr/avis/26-12345",
        "titulaire": "Identité fictive à ne pas reproduire",
        "courriel": "nom@example.org",
    }


def test_notice_boamp_exclut_contacts_et_informations_exterieures():
    n = notice_boamp(annonce())
    assert n["id"] == "26-12345"
    assert n["acheteur"] == "Établissement public fictif"
    assert "titulaire" not in n and "courriel" not in n
    assert n["contenu_integral_copie"] is False
    assert "example.org" not in str(n)
    assert notice_boamp({"idweb": "../fuite"}) is None


def test_adresse_boamp_officielle_filtree_bornee():
    req = urlparse(adresse_boamp("2026-10-02", 3, 100))
    params = parse_qs(req.query)
    assert req.scheme == "https" and req.hostname == "boamp-datadila.opendatasoft.com"
    assert params["where"] == ['dateparution >= "2026-10-02"']
    assert params["offset"] == ["300"]
    assert params["limit"] == ["100"]
    with pytest.raises(EchecBesoins):
        adresse_boamp("2026-10-02", 31, 100)
    with pytest.raises(EchecBesoins):
        adresse_boamp("2026/10/02", 1, 100)


def test_boamp_archive_cumulative_et_declare_la_couverture_partielle():
    appels = []
    def api(url, origine):
        assert origine == BOAMP
        appels.append(url)
        index = int(parse_qs(urlparse(url).query)["offset"][0]) // 2
        return {"total_count": 8, "results": [annonce(f"26-{index*2+i}")
                for i in range(2)]}

    old = {"annonces": [notice_boamp(annonce("25-ancien"))]}
    donnees, bilan = relever_boamp(
        old, obtenir=api, maintenant=datetime(2026, 10, 9, tzinfo=timezone.utc),
        pages=2, taille=2, attendre=lambda s: None,
    )
    assert len(appels) == 2
    assert len(donnees["annonces"]) == 5
    assert bilan["nouveaux_identifiants"] == 4
    assert bilan["recherche_partielle"] is True
    assert bilan["total_annonces_recherche_declare"] == 8
    assert bilan["couverture_exhaustive_du_boamp"] is False


def test_boamp_echec_partiel_conserve_anciens_et_refuse_echec_total():
    def api(url, _origine):
        if parse_qs(urlparse(url).query)["offset"] == ["2"]:
            raise OSError("Simulation de panne")
        return {"total_count": 10, "results": [annonce("26-1"), annonce("26-2")]}
    data, etat = relever_boamp(
        {"annonces": []}, obtenir=api, pages=2, taille=2, attendre=lambda s: None
    )
    assert len(data["annonces"]) == 2
    assert etat["pages_echouees"] == 1
    assert etat["recherche_partielle"] is True
    with pytest.raises(EchecBesoins, match="Aucune page"):
        relever_boamp({"annonces": []},
                      obtenir=lambda *_: (_ for _ in ()).throw(OSError("Panne totale")),
                      pages=1, attendre=lambda s: None)


def test_inventaire_des_offres_ne_recopie_pas_les_lignes_csv():
    def source(url, origine):
        assert url == origine == CSP
        return {
            "license": "lov2",
            "resources": [{
                "id": "12345678-abcd-1234-abcd-123456789abc",
                "title": "offres-datagouv-2026.csv",
                "format": "csv",
                "filesize": 114500000,
                "last_modified": "2026-10-05T00:00:00+00:00",
                "url": "https://static.data.gouv.fr/resources/offres.csv",
                "contact_email": "personne@example.org",
            }],
        }
    catalogue, etat = relever_emplois(obtenir=source)
    assert len(catalogue["ressources"]) == 1
    assert catalogue["fichiers_originaux_telecharges"] == 0
    assert etat["actualisation_des_offres_individuelles_constatee"] is False
    assert "contact_email" not in str(catalogue)
    assert notice_ressource_csp({"id": "../../secret"}) is None


def test_metadonnees_emplois_inaccessibles_sont_refusees():
    with pytest.raises(EchecBesoins):
        relever_emplois(obtenir=lambda *_: {"resources": []})
