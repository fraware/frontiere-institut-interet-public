"""Essais des comparaisons dynamiques d'effectifs entre manifestes et index."""
from copy import deepcopy

import pytest

from scripts.verifier_bilans_index_ci import BilanIncompatible, comparer


def objets():
    csp = {
        "version": "emplois-publics-extraits-v1",
        "offres_distinctes": 5, "references_distinctes": 3,
        "references_avec_plusieurs_variantes": 1,
        "empreintes_partitions": {f"lot_{i:02x}.jsonl": "a" * 64 for i in range(16)},
    }
    boamp = {"version": "avis-boamp-v1", "annonces": [{"id": "26-1"}, {"id": "26-2"}]}
    decp = {
        "version": "index-unifie-decp-v1",
        "identites_distinctes_par_siret_et_id_marche": 2,
        "variantes_documentaires_distinctes": 3,
        "attestations_documentaires": 4, "fichiers_documentaires": 2,
    }
    r = {
        "version": "frontiere-index-integral-recrutements-v1",
        "variantes_indexees": 5, "references_distinctes": 3,
        "references_multivariantes": 1, "partitions_verifiees": 16,
        "couverture_nationale_demontree": False,
        "recrutements_actuels_confirmes": 0,
    }
    c = {
        "version": "frontiere-commande-publique-integrale-v1",
        "avis_boamp": 2, "marches_identites": 2,
        "marches_variantes": 3, "marches_attestations": 4,
        "fichiers_decp": 2, "liaisons_boamp_decp_prouvees": 0,
        "couverture_nationale_demontree": False,
    }
    return r, c, csp, boamp, decp


def test_bilans_conformes_aux_sources():
    assert comparer(*objets())["recrutements"]["variantes_indexees"] == 5


def test_actualisation_coordonnée_ne_depend_pas_de_constantes():
    r, c, csp, boamp, decp = deepcopy(objets())
    csp["offres_distinctes"] = 6
    csp["references_distinctes"] = 4
    r["variantes_indexees"] = 6
    r["references_distinctes"] = 4
    boamp["annonces"].append({"id": "26-3"})
    c["avis_boamp"] = 3
    decp["fichiers_documentaires"] = 3
    c["fichiers_decp"] = 3
    assert comparer(r, c, csp, boamp, decp)["commande_publique"]["avis_boamp"] == 3


@pytest.mark.parametrize("index,cle", [
    (0, "variantes_indexees"), (0, "references_distinctes"),
    (1, "avis_boamp"), (1, "marches_attestations"),
])
def test_rejette_compteur_divergent(index, cle):
    args = list(objets())
    args[index][cle] += 1
    with pytest.raises(BilanIncompatible, match="divergence"):
        comparer(*args)


def test_rejette_types_non_entiers():
    args = list(objets())
    args[0]["variantes_indexees"] = True
    with pytest.raises(BilanIncompatible):
        comparer(*args)


def test_rejette_inference_non_etablie():
    args = list(objets())
    args[1]["liaisons_boamp_decp_prouvees"] = 1
    with pytest.raises(BilanIncompatible, match="Conclusions"):
        comparer(*args)


def test_rejette_manifeste_incomplet():
    args = list(objets())
    args[2]["empreintes_partitions"].pop("lot_0f.jsonl")
    with pytest.raises(BilanIncompatible, match="seize partitions"):
        comparer(*args)
