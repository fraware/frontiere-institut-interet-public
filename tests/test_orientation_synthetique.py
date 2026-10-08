"""Le jeu de recherche adversariale est purement fictif et reproductible."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.evaluer_orientation_synthetique import evaluer, verifier_jeu

ROOT = Path(__file__).resolve().parents[1]
JEU = ROOT / "evaluation" / "jeu_orientation_synthetique_v1.json"


def donnees():
    return json.loads(JEU.read_text(encoding="utf-8"))


def test_jeu_artificiel_mesure_aussi_les_defauts_sans_les_masquer():
    premiere = evaluer(donnees())
    seconde = evaluer(donnees())
    assert premiere == seconde
    assert premiere["nature"] == "EXCLUSIVEMENT_ARTIFICIELLE"
    assert premiere["nombre_notices_fictives"] == 12
    assert premiere["nombre_cas_fictifs"] == 10
    assert premiere["reperes_attendus"] == premiere["reperes_retrouves"] + premiere["reperes_omis"]
    assert premiere["integrite_operations"] == {
        "journalisations": 10, "recherches_publiques_creees": 0,
        "ressources_creees": 0, "decouvertes_creees": 0,
    }
    assert premiere["reperes_omis"] >= 1, "Le test doit illustrer une omission terminologique."
    assert premiere["pistes_hors_reperes"] >= 1, "Le test doit illustrer un rapprochement trop général."
    cas = {r["cas"]: r for r in premiere["cas"]}
    assert "S-IRM" in cas["IRM-ABREVIATION"]["reperes_omis"]["domaine_scientifique_publie"]
    assert "S-EAU" in cas["ANALYSE-SPECTRALE"]["pistes_hors_reperes"]["mission_ou_capacite_publiee"]
    assert all(r["verification_sources"] for r in premiere["cas"])
    assert all(len(r["empreinte_sha256_reponse"]) == 64 for r in premiere["cas"])
    assert "ne mesure" in premiere["limite"]


def test_refuse_reperes_absents_ou_incoherents():
    d = donnees()
    d["cas"][0]["attendus"]["mission_ou_capacite_publiee"].append("S-INCONNUE")
    with pytest.raises(ValueError, match="absent"):
        verifier_jeu(d)
    d = donnees()
    d["structures"].append(copy.deepcopy(d["structures"][0]))
    with pytest.raises(ValueError, match="répété"):
        verifier_jeu(d)
    d = donnees()
    d["nature"] = "DONNEES_REELLES"
    with pytest.raises(ValueError, match="artificiel"):
        verifier_jeu(d)


def test_refuse_les_classes_de_repere_incompletes():
    d = donnees()
    del d["cas"][0]["attendus"]["nom_uniquement"]
    with pytest.raises(ValueError, match="trois classes"):
        verifier_jeu(d)


def test_la_commande_fonctionne_sans_reseau_et_restitue_des_mesures(tmp_path):
    sortie = subprocess.run(
        [sys.executable, "scripts/evaluer_orientation_synthetique.py", "--jeu", str(JEU)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert sortie.returncode == 0, sortie.stderr
    bilan = json.loads(sortie.stdout)
    assert bilan["nombre_cas_fictifs"] == 10
    assert bilan["nature"] == "EXCLUSIVEMENT_ARTIFICIELLE"
    assert bilan["integrite_operations"]["recherches_publiques_creees"] == 0
