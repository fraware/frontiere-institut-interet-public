"""Essais entièrement artificiels de la relecture des sources et ressources."""
import copy
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def ecrire(p, objet):
    p.write_text(json.dumps(objet, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def executer(script, *args):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )


def preparer(tmp_path):
    questions = ecrire(tmp_path / "questions.json", {"version_schema": "jeu-reserve-v1",
        "cas": [{"code": "H01", "titre": "Exemple", "question": "Quelle ressource ?"}]})
    reponses = []
    gels = []
    for methode in ("analyste", "assistant_generaliste", "frontiere"):
        r = ecrire(tmp_path / f"{methode}.json", {
            "version_schema": "reponses-jeu-reserve-v1",
            "methode": methode, "version_methode": "1",
            "cas": [{"code": "H01", "voies": ["COOPERATION"], "formes_ressource": ["LABORATOIRE"],
                     "ressources": ["Laboratoire inventé"], "urls_preuves": ["https://exemple.fr/source"],
                     "duree_secondes": 30, "minutes_analyste": 1, "minutes_verification": 0, "notes": ""}],
        })
        gel = tmp_path / f"{methode}_gel.json"
        resultat = executer("geler_reponses_jeu_reserve.py", "--questions", questions,
                            "--reponses", r, "--manifeste", gel)
        assert resultat.returncode == 0, resultat.stderr
        reponses.append(r)
        gels.append(gel)
    destination = tmp_path / "relecture"
    resultat = executer("preparer_relecture_qualite.py", "--questions", questions,
                        "--reponses", *reponses, "--gels", *gels, "--sortie", destination)
    assert resultat.returncode == 0, resultat.stderr
    return questions, reponses, gels, destination


def renseigner(template, auteur, divergence=False):
    note = copy.deepcopy(template)
    note["relecteur_code"] = auteur
    for cas in note["cas"]:
        for proposition in cas["propositions"]:
            for ressource in proposition["ressources"]:
                ressource["existence"] = "CONFIRMEE"
                ressource["pertinence"] = "PARTIELLE" if divergence and proposition["id"].endswith("-A") else "FORTE"
                ressource["mobilisabilite"] = "INDETERMINEE"
                ressource["motif"] = "Contrôle artificiel consigné."
            for source in proposition["sources"]:
                source["fiabilite"] = "SECONDAIRE"
                source["appui"] = "PARTIEL"
                source["motif"] = "Source inventée pour test."
    return note


def test_deux_relectures_completes_et_desaccord_preserve(tmp_path):
    _, _, _, destination = preparer(tmp_path)
    paquet = json.loads((destination / "paquet_aveugle.json").read_text(encoding="utf-8"))
    correspondances = json.loads((destination / "correspondances_privees.json").read_text(encoding="utf-8"))
    assert len(paquet["cas"][0]["propositions"]) == 3
    assert len({p["methode"] for p in correspondances["correspondances"][0]["propositions"]}) == 3
    assert "methode" not in paquet["cas"][0]["propositions"][0]
    assert "analyste" not in json.dumps(paquet, ensure_ascii=False)
    template = json.loads((destination / "jugements_relecteur_1_vierges.json").read_text(encoding="utf-8"))
    r1 = ecrire(tmp_path / "r1.json", renseigner(template, "relecteur-001"))
    r2 = ecrire(tmp_path / "r2.json", renseigner(template, "relecteur-002", divergence=True))
    sortie = tmp_path / "bilan.json"
    resultat = executer("consolider_relecture_qualite.py", "--paquet", destination / "paquet_aveugle.json",
                        "--correspondances-privees", destination / "correspondances_privees.json",
                        "--jugements", r1, r2, "--sortie", sortie)
    assert resultat.returncode == 0, resultat.stderr
    bilan = json.loads(sortie.read_text(encoding="utf-8"))
    assert bilan["nombre_desaccords"] == 1
    assert bilan["desaccords"][0]["dimension"] == "pertinence"
    assert len(bilan["methodes"]) == 3


def test_incomplet_rejete(tmp_path):
    _, _, _, destination = preparer(tmp_path)
    template = json.loads((destination / "jugements_relecteur_1_vierges.json").read_text(encoding="utf-8"))
    r1 = ecrire(tmp_path / "r1.json", renseigner(template, "relecteur-001"))
    r2 = ecrire(tmp_path / "r2.json", renseigner(template, "relecteur-002"))
    contenu = json.loads(r2.read_text(encoding="utf-8"))
    contenu["cas"][0]["propositions"][0]["ressources"][0]["pertinence"] = "A_VERIFIER"
    ecrire(r2, contenu)
    resultat = executer("consolider_relecture_qualite.py", "--paquet", destination / "paquet_aveugle.json",
                        "--correspondances-privees", destination / "correspondances_privees.json",
                        "--jugements", r1, r2, "--sortie", tmp_path / "bilan.json")
    assert resultat.returncode != 0


def test_dossiers_refuses_si_reponses_alterees_apres_gel(tmp_path):
    questions, reponses, gels, destination = preparer(tmp_path)
    contenu = json.loads(reponses[0].read_text(encoding="utf-8"))
    contenu["cas"][0]["ressources"] = ["Nouvelle ressource inventée"]
    ecrire(reponses[0], contenu)
    resultat = executer("preparer_relecture_qualite.py", "--questions", questions,
                        "--reponses", *reponses, "--gels", *gels,
                        "--sortie", tmp_path / "autre_relecture")
    assert resultat.returncode != 0
    assert not (tmp_path / "autre_relecture").exists()


def test_dossiers_refuses_si_destination_dans_depot(tmp_path):
    questions, reponses, gels, _ = preparer(tmp_path)
    resultat = executer("preparer_relecture_qualite.py", "--questions", questions,
                        "--reponses", *reponses, "--gels", *gels,
                        "--sortie", ROOT / "evaluation" / "a_ne_pas_creer")
    assert resultat.returncode != 0
    assert not (ROOT / "evaluation" / "a_ne_pas_creer").exists()
