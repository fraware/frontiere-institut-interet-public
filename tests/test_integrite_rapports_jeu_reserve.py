import json
import pytest
from scripts.comparer_methodes_jeu_reserve import charger


def exemple():
    return {
        "version_schema": "resultats-jeu-reserve-v1",
        "methode": "analyste",
        "version_methode": "1",
        "nombre_cas": 1,
        "empreinte_sha256_reponses": "a" * 64,
        "empreinte_sha256_references": "b" * 64,
        "empreinte_sha256_gel_reponses": "c" * 64,
        "cas": [{
            "code": "H01",
            "voies": {"precision": 1, "rappel": 1, "mesure_harmonique": 1},
            "formes_ressource": {"precision": 0, "rappel": 0, "mesure_harmonique": 0},
            "minutes_analyste": 2,
            "minutes_verification": 1,
            "duree_secondes": 60,
            "nombre_preuves": 1,
        }],
        "voies_precision_moyenne": 1,
        "voies_rappel_moyen": 1,
        "voies_mesure_harmonique_moyenne": 1,
        "formes_precision_moyenne": 0,
        "formes_rappel_moyen": 0,
        "formes_mesure_harmonique_moyenne": 0,
        "minutes_humaines_totales": 3,
        "nombre_total_preuves": 1,
    }


def essayer(tmp_path, rapport):
    fichier = tmp_path / "rapport.json"
    fichier.write_text(json.dumps(rapport), encoding="utf-8")
    return charger(fichier)


def test_rapport_coherent(tmp_path):
    assert essayer(tmp_path, exemple())["nombre_cas"] == 1


def test_rejette_total_humain_incorrect(tmp_path):
    rapport = exemple()
    rapport["minutes_humaines_totales"] = 10
    with pytest.raises(ValueError):
        essayer(tmp_path, rapport)


def test_rejette_score_harmonique_incoherent(tmp_path):
    rapport = exemple()
    rapport["cas"][0]["voies"]["mesure_harmonique"] = 0.5
    with pytest.raises(ValueError):
        essayer(tmp_path, rapport)


def test_rejette_empreinte_de_gel_absente(tmp_path):
    rapport = exemple()
    del rapport["empreinte_sha256_gel_reponses"]
    with pytest.raises(ValueError):
        essayer(tmp_path, rapport)


def test_rejette_non_fini(tmp_path):
    rapport = exemple()
    rapport["cas"][0]["duree_secondes"] = float("nan")
    with pytest.raises(ValueError):
        essayer(tmp_path, rapport)
