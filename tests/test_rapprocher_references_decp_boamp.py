"""Contrôles hors réseau des rapprochements DECP et BOAMP par références."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import pytest

from scripts.collecter_notices_pilotes_boamp import adresse, qualifier
from scripts.rapprocher_references_decp_boamp import (
    RapprochementInvalide, extraire_reference, produire, reference_normalisee,
)

AIFE_ID = "db50f1f1-9fe5-4f9e-93dd-d273617d4a26"
XML_ID = "118544f1-b022-43d4-b8e0-3856f66a8b1d"
SIRET = "21750001630066"
CLE = "M2026ABC123"


def contrat(ref=CLE, siret=SIRET):
    return {
        "acheteur_siret": siret, "id_marche": ref,
        "objet": "Étude de traitement du signal",
        "code_cpv": "73100000-3", "nature": "Marché",
        "date_notification": "2026-10-10",
        "date_publication_declaree": "2026-10-12",
        "montant_euros_ht_declare": 80000,
        "offres_recues_declarees": 2,
        "marche_innovant_declare": None,
        "besoin_encore_ouvert_demontre": False,
        "preuve_de_premiere_contribution": False,
    }


def sources(tmp_path, lignes_aife=None, lignes_dgfip=None):
    if lignes_aife is None:
        lignes_aife = [contrat()]
    if lignes_dgfip is None:
        lignes_dgfip = []
    aife = {
        "version": "decp-fichier-json-v1",
        "source_catalogue": "aife_api_decp",
        "page_catalogue": "https://www.data.gouv.fr/datasets/api-decp",
        "sha256_fichier_brut": "a"*64, "ressource_id": AIFE_ID,
        "releve_le": "2026-10-13T11:00:00+00:00",
        "extraits_plafonnes": False,
        "releves": {"marches_uniques_valides": len(lignes_aife)},
        "marches_extraits": lignes_aife,
    }
    dgfip = {
        "version": "lot-decp-dgfip-xml-v1",
        "source_catalogue": "dgfip_pes_marche",
        "page_catalogue": (
            "https://www.data.gouv.fr/datasets/"
            "donnees-essentielles-de-la-commande-publique-transmises-via-le-pes-marche-depuis-2024"
        ),
        "controle_le": "2026-10-13T11:00:00+00:00",
        "fichiers": [{
            "id": XML_ID, "empreinte_sha256": "b"*64,
            "extraits_plafonnes": False,
            "releves": {"marches_uniques_valides": len(lignes_dgfip)},
            "marches_extraits": lignes_dgfip,
        }],
    }
    a, d = tmp_path/"aife.json", tmp_path/"dgfip.json"
    a.write_text(json.dumps(aife), encoding="utf-8")
    d.write_text(json.dumps(dgfip), encoding="utf-8")
    return a, d


def captures(tmp_path, references):
    """Construire des réponses conformes au manifeste des captures pilotes."""
    dossier = tmp_path / "captures"
    dossier.mkdir()
    fiches = []
    for i, (identifiant, reference) in enumerate(references):
        notice = {
            "idweb": identifiant, "nature": "ATTRIBUTION",
            "etat": "INITIAL", "dateparution": "2026-10-12",
            "nomacheteur": "Organisme public",
            "donnees": json.dumps({"EFORMS": {"ContractAwardNotice": {
                "cac:ProcurementProject": {"cbc:ID": reference},
            }}}) if reference is not None else "{}",
        }
        brut = json.dumps({"total_count": 1, "results": [notice]}).encode()
        (dossier / f"{identifiant}.json").write_bytes(brut)
        fiches.append({
            "identifiant": identifiant,
            "date_pilote_attendue": "2026-10-12",
            "source_officielle_interrogee": adresse(identifiant),
            "fichier_reponse": f"{identifiant}.json",
            "octets_reponse": len(brut),
            "sha256_reponse_http": hashlib.sha256(brut).hexdigest(),
            **qualifier(brut, identifiant, "2026-10-12"),
        })
    (dossier/"rapport.json").write_text(json.dumps({
        "version": "captures-notices-primaires-boamp-v1",
        "nombre_cas": len(fiches),
        "nombre_notices_retrouvees": len(fiches),
        "cas": fiches,
    }), encoding="utf-8")
    return dossier


def test_concordance_par_reference_est_uniquement_une_piste(tmp_path):
    a,d = sources(tmp_path)
    c = captures(tmp_path, [("26-30147", "M-2026-ABC123")])
    resultat = produire(a, d, [c])
    assert resultat["nombre_references_communes"] == 1
    assert resultat["nombre_pistes_avec_un_marche"] == 1
    assert resultat["correspondances_contractuelles_verifiees"] == 0
    piste = resultat["pistes"][0]
    assert piste["classement"] == "reference_commune_non_suffisante"
    assert piste["avis_boamp"][0]["chemin_reference"].endswith(
        "/cac:ProcurementProject/cbc:ID"
    )
    assert piste["identites_decp"][0]["acheteur_siret"] == SIRET
    assert piste["identite_contractuelle_verifiee"] is False


def test_plusieurs_avis_d_une_procedure_ne_creent_pas_deux_marches(tmp_path):
    a,d = sources(tmp_path)
    c = captures(tmp_path, [
        ("26-30147", CLE),
        ("26-30148", CLE),
    ])
    resultat = produire(a,d,[c])
    assert resultat["nombre_references_communes"] == 1
    assert resultat["pistes"][0]["nombre_avis"] == 2
    assert resultat["pistes"][0]["nombre_marches_distincts"] == 1


def test_identifiant_identique_de_deux_acheteurs_est_ambigu(tmp_path):
    a,d = sources(tmp_path, lignes_dgfip=[
        contrat(siret="12345678901234"),
    ])
    c = captures(tmp_path, [("26-30147", CLE)])
    resultat = produire(a,d,[c])
    assert resultat["nombre_pistes_ambigues"] == 1
    assert resultat["pistes"][0]["nombre_marches_distincts"] == 2
    assert resultat["correspondances_contractuelles_verifiees"] == 0


def test_contenu_similaire_sans_identifiant_egal_ne_suffit_pas(tmp_path):
    a,d = sources(tmp_path)
    c = captures(tmp_path,[("26-30147", "DIFFERENT12345")])
    resultat = produire(a,d,[c])
    assert resultat["nombre_references_communes"] == 0


def test_references_courtes_et_formulaires_inconnus_sont_ignores(tmp_path):
    assert reference_normalisee("M-1") is None
    assert reference_normalisee("M - 2026-ABC123") == "M2026ABC123"
    assert extraire_reference({"donnees": json.dumps({
        "FNSimple": {"cac:ProcurementProject": {"cbc:ID": CLE}},
    })})[0] is None
    a,d = sources(tmp_path)
    c = captures(tmp_path,[("26-30147", None)])
    resultat = produire(a,d,[c])
    assert resultat["nombre_references_communes"] == 0
    assert resultat["entrees"]["avis_non_interpretes"]["format_non_interprete"] == 1


def test_archive_alteree_refusee(tmp_path):
    a,d = sources(tmp_path)
    c = captures(tmp_path,[("26-30147",CLE)])
    (c/"26-30147.json").write_text("{}")
    with pytest.raises(ValueError,match="Empreinte|taille"):
        produire(a,d,[c])


def test_releve_partiel_refuse(tmp_path):
    a,d = sources(tmp_path)
    c = captures(tmp_path,[("26-30147",CLE)])
    rapport=json.loads(a.read_text())
    rapport["extraits_plafonnes"] = True
    a.write_text(json.dumps(rapport))
    with pytest.raises(ValueError,match="incomplet"):
        produire(a,d,[c])


def test_meme_marche_dans_deux_sources_ne_compte_qu_une_identite(tmp_path):
    a,d = sources(tmp_path,lignes_dgfip=[deepcopy(contrat())])
    c = captures(tmp_path,[("26-30147",CLE)])
    resultat=produire(a,d,[c])
    assert resultat["pistes"][0]["nombre_marches_distincts"] == 1
    assert resultat["pistes"][0]["identites_decp"][0]["versions_observees"] == 2
