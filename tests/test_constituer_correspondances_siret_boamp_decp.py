"""Tests de projection des preuves ; aucune réponse de source synthétique
n'est présentée comme un résultat réel sur les marchés français.
"""
from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.constituer_correspondances_siret_boamp_decp import (
    CorrespondanceInvalide, construire_correspondances,
)

H = "a" * 64
SIRET = "21590271900016"


def dossier(i: int, *, exact: bool = True) -> dict:
    return {
        "avis_boamp": f"26-{10000 + i}",
        "siret_chiffres_sans_schema_boamp": (
            SIRET if i == 1 else f"{10000000000000 + i:014d}"),
        "date_parution": "2026-09-15",
        "empreinte_avis_boamp": H,
        "sha256_reponse_api": H,
        "preuve_siret_dans_boamp":
            "/results/0/donnees/EFORMS/ContractNotice/cac:ContractingParty/"
            "cac:Party/cac:PartyLegalEntity/cbc:CompanyID",
        "preuve_etablissement_exact_api": "/results/0/etablissements/0/siret",
        "presence_etablissement_exact_api": exact,
        "role_contractant_juridiquement_confirme": False,
        "identite_contrat_decp_etablie": False,
    }


def corpus() -> dict:
    avis = [dossier(i) for i in range(1, 18)]
    # Deux notices du même établissement, sans les assimiler à un même marché.
    avis[-1]["siret_chiffres_sans_schema_boamp"] = SIRET
    avis[-1]["presence_etablissement_exact_api"] = False
    return {
        "version": "chaines-documentaires-acheteurs-17-avis-v1",
        "sha256_audit_boamp": H,
        "sha256_rapport_administratif": H,
        "liaisons_contractuelles_decp_prouvees": 0,
        "validations_juridiques_du_role_acheteur": 0,
        "nombre_siret_distincts": 16,
        "mesures": {"avis": 17},
        "dossiers": avis,
    }


def produire(rapport=None, comptes=None):
    return construire_correspondances(
        rapport if rapport is not None else corpus(),
        comptes if comptes is not None else {SIRET: 4},
        {"aife": H, "dgfip": H},
    )


def test_seuls_etablissements_exacts_ont_un_rapprochement_decp():
    resultat = produire()
    assert resultat["nombre_avis"] == 17
    assert resultat["nombre_siret_boamp_distincts"] == 16
    assert resultat["nombre_avis_avec_etablissement_exact_api"] == 16
    assert resultat["nombre_avis_avec_siret_egal_a_un_acheteur_decp"] == 1
    premier = resultat["observations"][0]
    assert premier["siret_etablissement_exact_dans_api"] is True
    assert premier["marches_decp_identites_meme_siret"] == 4
    assert premier["rapprochement_acheteur_documentaire"] is True
    assert premier["identite_contrat_decp_demonstree"] is False
    dernier = resultat["observations"][-1]
    assert dernier["siret_etablissement_exact_dans_api"] is False
    assert dernier["marches_decp_identites_meme_siret"] == 0
    assert dernier["rapprochement_acheteur_documentaire"] is False
    assert resultat["role_acheteur_juridiquement_etabli"] is False


@pytest.mark.parametrize("modification", [
    lambda r: r.update({"liaisons_contractuelles_decp_prouvees": 1}),
    lambda r: r.update({"validations_juridiques_du_role_acheteur": 1}),
    lambda r: r.update({"sha256_audit_boamp": "incorrect"}),
    lambda r: r["dossiers"][1].update({"avis_boamp": "26-10001"}),
    lambda r: r["dossiers"][0].update({"empreinte_avis_boamp": "incorrect"}),
    lambda r: r["dossiers"][0].update({"preuve_siret_dans_boamp": "/fournisseur"}),
    lambda r: r["dossiers"][0].update({"presence_etablissement_exact_api": "oui"}),
    lambda r: r["dossiers"][0].update({"role_contractant_juridiquement_confirme": True}),
    lambda r: r["dossiers"][0].update({"identite_contrat_decp_etablie": True}),
    lambda r: r["dossiers"][0].update({"date_parution": "demain"}),
])
def test_refus_des_sources_incorrectes_ou_des_conclusions_excessives(modification):
    rapport = deepcopy(corpus())
    modification(rapport)
    with pytest.raises(CorrespondanceInvalide):
        produire(rapport)


def test_refuser_un_decompte_contractuel_sans_cle_exacte():
    with pytest.raises(CorrespondanceInvalide):
        produire(comptes={"Acheteur approximatif": 4})
    with pytest.raises(CorrespondanceInvalide):
        produire(comptes={SIRET: -1})


def test_resultat_deterministe_et_ordre_des_avis():
    rapport = corpus()
    avant = produire(rapport)
    rapport["dossiers"].reverse()
    apres = produire(rapport)
    assert avant == apres
    assert [x["avis_boamp"] for x in avant["observations"]] == sorted(
        x["avis_boamp"] for x in avant["observations"])
