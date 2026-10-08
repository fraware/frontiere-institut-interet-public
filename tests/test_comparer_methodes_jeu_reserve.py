import copy

import pytest

from scripts.comparer_methodes_jeu_reserve import comparer


def rapports():
    sorties = []
    for nom, f1 in [("analyste", 0.5), ("assistant_generaliste", 0.6), ("frontiere", 0.7)]:
        sorties.append({
            "version_schema": "resultats-jeu-reserve-v1",
            "methode": nom,
            "version_methode": "1",
            "empreinte_sha256_reponses": nom,
            "empreinte_sha256_references": "meme-reference",
            "empreinte_sha256_questions": "a" * 64,
            "nombre_cas": 2,
            "cas": [
                {
                    "code": code,
                    "voies": {"mesure_harmonique": f1},
                    "formes_ressource": {"mesure_harmonique": None if code == "H02" else f1},
                    "minutes_analyste": 2,
                    "minutes_verification": 1,
                    "duree_secondes": None if code == "H02" else 30,
                    "nombre_preuves": 1,
                }
                for code in ("H01", "H02")
            ],
        })
    return sorties


def test_comparaison_appariee_et_donnees_manquantes():
    sortie = comparer(rapports())
    assert sortie["nombre_cas"] == 2
    assert len(sortie["methodes"]) == 3
    assert sortie["methodes"][0]["minutes_humaines_totales"] == 6
    assert sortie["methodes"][0]["temps_ecoule_total_secondes"] is None
    assert sortie["ecarts"][0]["nombre_paires"] == 2
    assert sortie["ecarts"][1]["nombre_paires"] == 1
    assert len(sortie["ecarts"]) == 6
    assert sortie["ecarts"][4]["reference"] == "assistant_generaliste"


def test_refuse_des_references_differentes():
    sources = rapports()
    sources[1]["empreinte_sha256_references"] = "autre"
    with pytest.raises(ValueError):
        comparer(sources)


def test_refuse_des_cas_non_apparies():
    sources = rapports()
    sources[1]["cas"][1]["code"] = "H03"
    with pytest.raises(ValueError):
        comparer(sources)


def test_refuse_les_methodes_dupliquees():
    sources = rapports()
    sources[2]["methode"] = "assistant_generaliste"
    with pytest.raises(ValueError):
        comparer(sources)


def test_refuse_questions_differentes_meme_si_codes_et_references_identiques():
    sources = rapports()
    sources[2]["empreinte_sha256_questions"] = "b" * 64
    with pytest.raises(ValueError, match="questions différents"):
        comparer(sources)


def test_refuse_empreinte_des_questions_absente_ou_malformee():
    sources = rapports()
    del sources[1]["empreinte_sha256_questions"]
    with pytest.raises(ValueError, match="questions"):
        comparer(sources)
    sources = rapports()
    sources[0]["empreinte_sha256_questions"] = "indetermine"
    with pytest.raises(ValueError, match="questions"):
        comparer(sources)


def test_conserve_l_empreinte_des_questions_dans_le_bilan():
    sortie = comparer(rapports())
    assert sortie["empreinte_sha256_questions"] == "a" * 64
