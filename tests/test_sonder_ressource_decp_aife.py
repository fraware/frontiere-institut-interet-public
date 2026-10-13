"""Contrôles sans réseau de la sonde officielle AIFE."""
import json
from pathlib import Path

import pytest

from scripts.sonder_ressource_decp_aife import (
    SondeDECPInvalide, choisir_ressource, executer,
    _url_officielle, PLAFOND_OCTETS,
)

RID = "db50f1f1-9fe5-4f9e-93dd-d273617d4a26"
URL = "https://static.data.gouv.fr/resources/api-decp/test.json"


def etat():
    return {
        "version": "decp-metadonnees-v1",
        "catalogues": [{
            "source_id": "aife_api_decp",
            "ressources_recentes": [
                {"id": RID, "format": "json", "titre": "essai.json",
                 "taille_octets_declaree": 50},
            ],
        }],
    }


def fiche():
    return {
        "resources": [
            {"id": RID, "format": "json", "title": "essai.json",
             "filesize": 50, "url": URL},
        ],
    }


def test_choix_resource_id_strictement_repris_du_registre():
    selection = choisir_ressource(etat(), fiche())
    assert selection["id"] == RID
    assert selection["url"] == URL


def test_ressource_inattendue_ou_origine_exterieure_refusee():
    err = fiche()
    err["resources"][0]["url"] = "https://attacker.invalid/truc.json"
    with pytest.raises(SondeDECPInvalide):
        choisir_ressource(etat(), err)
    err = fiche()
    err["resources"][0]["id"] = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    with pytest.raises(SondeDECPInvalide):
        choisir_ressource(etat(), err)
    for url in ("http://static.data.gouv.fr/file", "https://localhost/file",
                "https://user:pass@static.data.gouv.fr/file",
                "https://static.data.gouv.fr.evil.invalid/file"):
        with pytest.raises(SondeDECPInvalide):
            _url_officielle(url)


def test_limite_de_fichier_prise_en_compte():
    etat_test = etat()
    etat_test["catalogues"][0]["ressources_recentes"][0][
        "taille_octets_declaree"
    ] = PLAFOND_OCTETS + 1
    distant = fiche()
    distant["resources"][0]["filesize"] = PLAFOND_OCTETS + 1
    with pytest.raises(SondeDECPInvalide):
        choisir_ressource(etat_test, distant)


def test_preuve_de_taille_avec_fichier_recu(tmp_path):
    contenu = json.dumps({
        "marches": [{
            "id": "PILOTE", "acheteur": {"id": "21750001630066"},
            "objet": "Contrat de recherche scientifique", "codeCPV": "73100000-3",
            "dateNotification": "2026-10-11",
        }]
    }).encode("utf-8")
    state = etat()
    state["catalogues"][0]["ressources_recentes"][0]["taille_octets_declaree"] = len(contenu)
    metadata = fiche()
    metadata["resources"][0]["filesize"] = len(contenu)

    def recuperation(resource, chemin):
        assert resource["url"] == URL
        chemin.write_bytes(contenu)
        return len(contenu)

    resultat = executer(state, metadata, recuperer=recuperation)
    assert resultat["releves"]["marches_uniques_valides"] == 1
    assert resultat["type_essai"] == "sonde_reelle_bornee_non_exhaustive"
    assert resultat["telechargement_integral_du_catalogue"] is False
    assert resultat["page_catalogue"] == "https://www.data.gouv.fr/datasets/api-decp"


def test_taille_declaree_et_taille_effective_divergentes():
    def recuperation(resource, chemin):
        chemin.write_bytes(b"{}")
        return 2
    with pytest.raises(SondeDECPInvalide):
        executer(etat(), fiche(), recuperer=recuperation)
