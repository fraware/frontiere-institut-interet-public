"""Protection des chiffres DECP contre les relevés modifiés sans bilan actualisé."""
from copy import deepcopy

import pytest

from scripts.verifier_coherence_bilan_decp import (
    BilanDECPPerime, INDICATEURS, comparer, verifier,
)


def test_reconstitution_du_bilan_decp_reel_est_identique_aux_archives():
    resultat = verifier()
    assert resultat["statut"] == "coherent_avec_les_deux_releves_archives"
    assert resultat["fichiers_documentaires"] >= 2
    assert resultat["identites_distinctes"] >= 1
    assert resultat["couverture_nationale_exhaustive_demontree"] is False
    assert resultat["besoins_ouverts_demontres"] == 0


def test_changement_de_ressource_sans_recalcul_interdit_de_publier_le_bilan():
    bilan = {cle: 1 for cle in INDICATEURS}
    bilan["empreintes_releves_publies"] = {
        "aife": "a" * 64,
        "dgfip": "b" * 64,
    }
    comparer(deepcopy(bilan), bilan)
    change = deepcopy(bilan)
    change["empreintes_releves_publies"]["dgfip"] = "c" * 64
    with pytest.raises(BilanDECPPerime, match="empreintes_releves_publies"):
        comparer(bilan, change)


def test_comptage_altere_est_detecte_meme_si_empreintes_inchangees():
    bilan = {cle: 1 for cle in INDICATEURS}
    modifie = deepcopy(bilan)
    modifie["identites_distinctes_par_siret_et_id_marche"] = 2
    with pytest.raises(BilanDECPPerime, match="identites_distinctes"):
        comparer(bilan, modifie)


def test_champ_manquant_et_type_bool_entier_sont_interdits():
    bilan = {cle: 1 for cle in INDICATEURS}
    invalide = deepcopy(bilan)
    del invalide["sources"]
    with pytest.raises(BilanDECPPerime, match="sources"):
        comparer(invalide, bilan)
    invalide = deepcopy(bilan)
    invalide["besoins_encore_ouverts_demontres"] = False
    with pytest.raises(BilanDECPPerime, match="besoins_encore_ouverts_demontres"):
        comparer(invalide, bilan)
