"""Vérifications hors réseau de l'ingestion JSON DECP en flux."""
from __future__ import annotations

from io import StringIO
import json

import pytest

from scripts.ingerer_fichier_decp_json import (
    DocumentDECPInvalide, MAX_FICHIER_OCTETS,
    iterer_marches, iterer_documents, normaliser_marche, traiter_fichier,
)

RESSOURCE = "db50f1f1-9fe5-4f9e-93dd-d273617d4a26"


def marche(id="M-2026-001", acheteur="21750001630066", **autres):
    return {
        "id": id, "acheteur": {"id": acheteur}, "objet": "Prestation scientifique",
        "codeCPV": "73100000-3", "nature": "Marché",
        "dateNotification": "2026-10-11",
        "datePublicationDonnees": "2026-10-13", "montant": 135000.0,
        "_type": "Marché", **autres,
    }


@pytest.mark.parametrize("enveloppe", [
    lambda m: {"marches": [m]},
    lambda m: {"marches": {"marche": [m]}},
    lambda m: [m],
])
def test_trois_enveloppes_documentaires(enveloppe):
    doc = json.dumps(enveloppe(marche()), ensure_ascii=False)
    resultat = list(iterer_marches(StringIO(doc)))
    assert len(resultat) == 1
    assert resultat[0]["id"] == "M-2026-001"


def test_plusieurs_notices_avec_petits_blocs(monkeypatch):
    import scripts.ingerer_fichier_decp_json as module
    monkeypatch.setattr(module, "BLOC_CARACTERES", 13)
    don = {"marches": {"marche": [marche(id=f"marche-{i}") for i in range(85)]}}
    lu = list(iterer_marches(StringIO(json.dumps(don, ensure_ascii=False))))
    assert len(lu) == 85
    assert lu[0]["id"] == "marche-0"
    assert lu[-1]["id"] == "marche-84"


def test_document_mal_forme_ou_tronque_refuse():
    with pytest.raises(DocumentDECPInvalide):
        list(iterer_marches(StringIO('{"marches":[{"id":"M"},]}')))
    with pytest.raises(DocumentDECPInvalide):
        list(iterer_marches(StringIO('{"marches":[{"id":"M"}]')))
    with pytest.raises(DocumentDECPInvalide):
        list(iterer_marches(StringIO('{"marches":[],"libre":1}')))


def test_provenance_et_formes_des_identifiants():
    ligne = normaliser_marche(marche())
    assert ligne["acheteur_siret"] == "21750001630066"
    assert ligne["code_cpv"] == "73100000-3"
    assert not ligne["besoin_encore_ouvert_demontre"]
    assert not ligne["preuve_de_premiere_contribution"]
    with pytest.raises(DocumentDECPInvalide):
        normaliser_marche(marche(acheteur="999"))
    with pytest.raises(DocumentDECPInvalide):
        normaliser_marche(marche(dateNotification="invalide"))


def test_montants_na_n_et_domaine_cpv_refuses():
    for v in (float("nan"), float("inf"), True, -10):
        with pytest.raises(DocumentDECPInvalide):
            normaliser_marche(marche(montant=v))
    with pytest.raises(DocumentDECPInvalide):
        normaliser_marche(marche(codeCPV="code-libre"))
    with pytest.raises(DocumentDECPInvalide):
        normaliser_marche({"id": "X", "acheteur": {"id": "21750001630066"},
                          "objet": "Concession", "_type": "Concession"})


def test_bilan_dedoublonne_et_distingue_versions(tmp_path):
    fichier = tmp_path / "aife-decp.json"
    conflit = marche()
    conflit["objet"] = "Prestation scientifique modifiée"
    donnees = [
        marche(), marche(), conflit,
        marche(acheteur="12345678901234"),
        marche(id="autre"), {"id": "X", "objet": "sans acheteur"},
    ]
    fichier.write_text(json.dumps({"marches": {"marche": donnees}}), encoding="utf-8")
    resultat = traiter_fichier(
        fichier, source_id="aife_api_decp", ressource_id=RESSOURCE,
        limite_extraits=2,
    )
    stats = resultat["releves"]
    assert stats["notices_lues"] == 6
    assert stats["marches_uniques_valides"] == 3
    assert stats["doublons_exacts_dans_fichier"] == 1
    assert stats["conflits_de_versions_dans_fichier"] == 1
    assert stats["notices_rejetees"] == 1
    assert len(resultat["marches_extraits"]) == 2
    assert resultat["extraits_plafonnes"] is True
    assert resultat["categories_cpv_prefixe_2"] == {"73": 3}
    assert len(resultat["sha256_fichier_brut"]) == 64
    assert not resultat["lien_boamp_demontre"]


def test_refus_sans_generation_de_bilan(tmp_path):
    fic = tmp_path / "wrong.json"
    fic.write_text('{"autre": []}', encoding="utf-8")
    with pytest.raises(DocumentDECPInvalide):
        traiter_fichier(fic, source_id="aife_api_decp", ressource_id=RESSOURCE)
    fic.write_text('{"marches": []}', encoding="utf-8")
    with pytest.raises(DocumentDECPInvalide):
        traiter_fichier(fic, source_id="source_non_prise_en_charge", ressource_id=RESSOURCE)


def test_taille_fichier_limitee(tmp_path):
    fic = tmp_path / "very_big.json"
    with fic.open("wb") as f:
        f.truncate(MAX_FICHIER_OCTETS + 1)
    with pytest.raises(DocumentDECPInvalide):
        traiter_fichier(fic, source_id="aife_api_decp", ressource_id=RESSOURCE)


def test_schema_pas_confondue_avec_validation_reglementaire(tmp_path):
    fic = tmp_path / "exemple.json"
    fic.write_text(
        json.dumps({"marches": [marche()]}), encoding="utf-8"
    )
    d = traiter_fichier(fic, source_id="aife_api_decp", ressource_id=RESSOURCE)
    assert not d["conformite_complete_au_schema_reglementaire_verifiee"]
    assert d["releves"]["notices_lues"] == 1
    assert d["releves"]["marches_uniques_valides"] == 1



@pytest.mark.parametrize("ordre", ["marche_d_abord", "concession_d_abord"])
def test_structure_reelle_aife_marche_et_contrat_concession(ordre, tmp_path):
    """Deux collections explicitement présentes, ordre indifférent."""
    marches = [marche(id="SCI-001"), marche(id="SCI-002")]
    concessions = [{"id": "C-001", "objet": "Concession hors périmètre"}]
    sous = (
        {"marche": marches, "contrat-concession": concessions}
        if ordre == "marche_d_abord"
        else {"contrat-concession": concessions, "marche": marches}
    )
    fichier = tmp_path / "reel-compatible.json"
    fichier.write_text(json.dumps({"marches": sous}, ensure_ascii=False), encoding="utf-8")
    with fichier.open(encoding="utf-8") as flux:
        categories = [categorie for categorie, _ in iterer_documents(flux)]
    assert sorted(categories) == ["contrat-concession", "marche", "marche"]
    avec = traiter_fichier(fichier, source_id="aife_api_decp", ressource_id=RESSOURCE)
    assert avec["releves"]["objets_documentaires_lus"] == 3
    assert avec["releves"]["notices_lues"] == 2
    assert avec["releves"]["concessions_non_normalisees"] == 1
    assert avec["releves"]["marches_uniques_valides"] == 2
    assert all(x["id_marche"].startswith("SCI-") for x in avec["marches_extraits"])


def test_champs_inconnus_dans_enveloppe_rejetes():
    payload = {
        "marches": {
            "marche": [marche()],
            "information_inconnue": [{"sensible": "information non examinée"}],
        }
    }
    with pytest.raises(DocumentDECPInvalide):
        list(iterer_documents(StringIO(json.dumps(payload))))


def test_concession_seule_refusee_sans_collection_de_marches():
    with pytest.raises(DocumentDECPInvalide):
        list(iterer_documents(
            StringIO('{"marches":{"contrat-concession":[{"id":"C"}]}}')
        ))


def test_collection_repetee_refusee():
    brut = '{"marches":{"marche":[],"marche":[]}}'
    with pytest.raises(DocumentDECPInvalide):
        list(iterer_documents(StringIO(brut)))


def test_plafond_explicite_grand_fichier_et_limite_par_defaut():
    donnees = {"marches": {"marche": [
        marche(id=f"marche-grande-{i}") for i in range(5)
    ], "contrat-concession": [{"id": "CONCESSION"}]}}
    texte = json.dumps(donnees, ensure_ascii=False)
    normal = list(iterer_documents(StringIO(texte)))
    assert len(normal) == 6
    with pytest.raises(DocumentDECPInvalide, match="plafond"):
        list(iterer_documents(StringIO(texte), plafond_notices=5))
    etendu = list(iterer_documents(StringIO(texte), plafond_notices=7))
    assert len(etendu) == 6
    assert etendu[-1][0] == "contrat-concession"


@pytest.mark.parametrize("plafond", [0, -5, True, 200001, "100", None])
def test_plafond_explicite_hors_contrat_refuse(plafond):
    with pytest.raises(DocumentDECPInvalide, match="Plafond"):
        list(iterer_documents(StringIO("[]"), plafond_notices=plafond))
