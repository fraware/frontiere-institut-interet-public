"""Essai complet avec cas intégralement artificiels : aucune référence réelle."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def ecrire(path, donnees):
    path.write_text(json.dumps(donnees, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def lancer(nom, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / nom), *map(str, args)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )


def scenario(tmp_path):
    questions = ecrire(tmp_path / "questions.json", {"cas": [
        {"code": "H01", "question": "Question inventée 1"},
        {"code": "H02", "question": "Question inventée 2"},
    ]})
    references = ecrire(tmp_path / "references_artificielles.json", {"cas": [
        {"code": "H01", "voies_attendues": ["MOBILITE"], "formes_ressource_attendues": ["EQUIPE"]},
        {"code": "H02", "voies_attendues": ["FORMATION"], "formes_ressource_attendues": ["FORMATION"]},
    ]})
    manifeste = ecrire(tmp_path / "manifeste_references.json", {
        "empreinte_sha256_references": hashlib.sha256(references.read_bytes()).hexdigest()
    })
    return questions, references, manifeste


def reponse(nom, voie_2):
    return {
        "version_schema": "reponses-jeu-reserve-v1",
        "methode": nom,
        "version_methode": "essai-artificiel",
        "cas": [
            {
                "code": code,
                "voies": [voie],
                "formes_ressource": [forme],
                "ressources": [],
                "urls_preuves": [],
                "duree_secondes": 30,
                "minutes_analyste": 1,
                "minutes_verification": 0,
                "notes": "",
            }
            for code, voie, forme in [
                ("H01", "MOBILITE", "EQUIPE"),
                ("H02", voie_2, "FORMATION"),
            ]
        ],
    }


def test_chaine_complete_sur_cas_artificiels(tmp_path):
    questions, references, manifeste = scenario(tmp_path)
    rapports = []
    for nom, voie in [("analyste", "AUTRE"), ("assistant_generaliste", "FORMATION"), ("frontiere", "FORMATION")]:
        chemin = ecrire(tmp_path / f"{nom}_reponses.json", reponse(nom, voie))
        gel = tmp_path / f"{nom}_gel.json"
        assert lancer("geler_reponses_jeu_reserve.py", "--questions", questions,
                     "--reponses", chemin, "--manifeste", gel).returncode == 0
        assert lancer("geler_reponses_jeu_reserve.py", "--questions", questions,
                     "--reponses", chemin, "--manifeste", gel, "--verifier").returncode == 0
        rapport = tmp_path / f"{nom}_rapport.json"
        result = lancer("evaluer_jeu_reserve.py", "--questions", questions,
                       "--references", references, "--manifeste", manifeste,
                       "--reponses", chemin, "--gel-reponses", gel, "--sortie", rapport)
        assert result.returncode == 0, result.stderr
        assert json.loads(rapport.read_text(encoding="utf-8"))["empreinte_sha256_gel_reponses"] == hashlib.sha256(gel.read_bytes()).hexdigest()
        rapports.append(rapport)
    final = tmp_path / "comparaison.json"
    comparaison = lancer("comparer_methodes_jeu_reserve.py", "--rapports", *rapports, "--nombre-cas-attendus", "2", "--sortie", final)
    assert comparaison.returncode == 0, comparaison.stderr
    resultat = json.loads(final.read_text(encoding="utf-8"))
    assert resultat["nombre_cas"] == 2
    assert len(resultat["methodes"]) == 3
    assert resultat["methodes"][0]["voies_f1_moyen"] == 0.5
    assert resultat["methodes"][1]["voies_f1_moyen"] == 1.0


def test_correction_refuse_alteration_apres_gel(tmp_path):
    questions, references, manifeste = scenario(tmp_path)
    fichier = ecrire(tmp_path / "reponse.json", reponse("analyste", "FORMATION"))
    gel = tmp_path / "gel.json"
    assert lancer("geler_reponses_jeu_reserve.py", "--questions", questions,
                 "--reponses", fichier, "--manifeste", gel).returncode == 0
    contenu = json.loads(fichier.read_text(encoding="utf-8"))
    contenu["cas"][0]["voies"] = ["VOIE_FABRIQUEE"]
    ecrire(fichier, contenu)
    sortie = tmp_path / "resultat.json"
    evaluation = lancer("evaluer_jeu_reserve.py", "--questions", questions,
                        "--references", references, "--manifeste", manifeste,
                        "--reponses", fichier, "--gel-reponses", gel, "--sortie", sortie)
    assert evaluation.returncode != 0
    assert "gel" in evaluation.stderr.lower()
    assert not sortie.exists()


def test_correction_exige_manifeste(tmp_path):
    questions, references, manifeste = scenario(tmp_path)
    fichier = ecrire(tmp_path / "reponse.json", reponse("analyste", "FORMATION"))
    sortie = tmp_path / "resultat.json"
    evaluation = lancer("evaluer_jeu_reserve.py", "--questions", questions,
                        "--references", references, "--manifeste", manifeste,
                        "--reponses", fichier, "--sortie", sortie)
    assert evaluation.returncode != 0
    assert not sortie.exists()


def test_gel_refuse_manifeste_reecrit(tmp_path):
    questions, _, _ = scenario(tmp_path)
    fichier = ecrire(tmp_path / "reponse.json", reponse("analyste", "FORMATION"))
    gel = tmp_path / "gel.json"
    assert lancer("geler_reponses_jeu_reserve.py", "--questions", questions,
                 "--reponses", fichier, "--manifeste", gel).returncode == 0
    contenu = json.loads(gel.read_text(encoding="utf-8"))
    contenu["methode"] = "frontiere"
    ecrire(gel, contenu)
    result = lancer("geler_reponses_jeu_reserve.py", "--questions", questions,
                   "--reponses", fichier, "--manifeste", gel, "--verifier")
    assert result.returncode != 0
