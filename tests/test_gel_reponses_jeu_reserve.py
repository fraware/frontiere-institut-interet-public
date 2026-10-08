import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "geler_reponses_jeu_reserve.py"


def preparer(tmp_path):
    q = tmp_path / "questions.json"
    r = tmp_path / "reponses.json"
    m = tmp_path / "manifeste.json"
    q.write_text(json.dumps({"cas": [{"code": "H01"}]}), encoding="utf-8")
    r.write_text(json.dumps({
        "version_schema": "reponses-jeu-reserve-v1",
        "methode": "analyste",
        "version_methode": "1",
        "cas": [{
            "code": "H01",
            "voies": [],
            "formes_ressource": [],
            "ressources": [],
            "urls_preuves": [],
            "duree_secondes": 5,
            "minutes_analyste": 1,
            "minutes_verification": 0,
            "notes": "",
        }],
    }), encoding="utf-8")
    return q, r, m


def executer(q, r, m, *suite):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--questions", str(q), "--reponses", str(r),
         "--manifeste", str(m), *suite],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )


def test_gel_et_verification(tmp_path):
    q, r, m = preparer(tmp_path)
    assert executer(q, r, m).returncode == 0
    manifeste = json.loads(m.read_text(encoding="utf-8"))
    assert manifeste["empreinte_sha256_reponses"] == hashlib.sha256(r.read_bytes()).hexdigest()
    assert manifeste["attestation_externe"] is None
    assert executer(q, r, m, "--verifier").returncode == 0


def test_gel_refuse_ecrasement(tmp_path):
    q, r, m = preparer(tmp_path)
    assert executer(q, r, m).returncode == 0
    assert executer(q, r, m).returncode != 0


def test_gel_detecte_modification_apres_signature(tmp_path):
    q, r, m = preparer(tmp_path)
    assert executer(q, r, m).returncode == 0
    r.write_text(r.read_text(encoding="utf-8") + " ", encoding="utf-8")
    assert executer(q, r, m, "--verifier").returncode != 0


def test_gel_refuse_fichier_incomplet(tmp_path):
    q, r, m = preparer(tmp_path)
    contenu = json.loads(r.read_text(encoding="utf-8"))
    contenu["cas"] = []
    r.write_text(json.dumps(contenu), encoding="utf-8")
    assert executer(q, r, m).returncode != 0
    assert not m.exists()
