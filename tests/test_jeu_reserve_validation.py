import pytest
from scripts.verifier_reponses_jeu_reserve import verifier_reponses

def exemple():
    q = {"cas": [{"code": "H01"}]}
    r = {"version_schema": "reponses-jeu-reserve-v1", "methode": "analyste", "version_methode": "1", "cas": [{"code": "H01", "voies": ["mobilité"], "formes_ressource": ["équipe"], "ressources": [], "urls_preuves": [], "duree_secondes": 60, "minutes_analyste": 1, "minutes_verification": 0, "notes": ""}]}
    return q, r

def test_valide():
    q, r = exemple()
    verifier_reponses(q, r)

@pytest.mark.parametrize("champ,valeur", [("minutes_analyste", True), ("minutes_verification", -1), ("duree_secondes", float("nan")), ("voies", [1]), ("notes", 3)])
def test_invalide(champ, valeur):
    q, r = exemple()
    r["cas"][0][champ] = valeur
    with pytest.raises(ValueError):
        verifier_reponses(q, r)

def test_code_manquant():
    q, r = exemple()
    r["cas"] = []
    with pytest.raises(ValueError):
        verifier_reponses(q, r)
