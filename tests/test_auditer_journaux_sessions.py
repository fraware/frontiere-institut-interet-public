from datetime import datetime, timedelta, timezone

from scripts.auditer_journaux_sessions import auditer


def scenario():
    debut = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)
    q = {"cas": [{"code": "H01"}]}
    r = {
        "version_schema": "reponses-jeu-reserve-v1",
        "methode": "analyste", "version_methode": "1",
        "cas": [{
            "code": "H01", "voies": [], "formes_ressource": [],
            "ressources": [], "urls_preuves": [], "duree_secondes": 300,
            "minutes_analyste": 3, "minutes_verification": 1, "notes": "",
        }],
    }
    j = {
        "version_schema": "journal-session-v1", "methode": "analyste",
        "operateur_code": "a-01", "version_logiciel_ou_modele": "manuel",
        "cas": [{
            "code": "H01", "debut_iso": debut.isoformat(),
            "fin_iso": (debut + timedelta(minutes=5)).isoformat(),
            "budget_respecte": True, "reconnaissance_fortuite_origine": False,
            "interruptions_ou_ecarts": "", "sources_revelant_solution": [],
        }],
    }
    return q, r, j


def test_journal_et_reponses_coherents():
    q, r, j = scenario()
    bilan = auditer(q, r, j, 10)
    assert bilan["nombre_anomalies"] == 0
    assert bilan["cas"][0]["secondes_journal"] == 300


def test_incompatibilite_temps_signalee():
    q, r, j = scenario()
    r["cas"][0]["duree_secondes"] = 240
    bilan = auditer(q, r, j, 10)
    assert any("incompatible" in a["description"] for a in bilan["anomalies"])


def test_depassement_de_budget_signale():
    q, r, j = scenario()
    bilan = auditer(q, r, j, 4)
    assert any("dépassement" in a["description"] for a in bilan["anomalies"])
    assert any("contradictoire" in a["description"] for a in bilan["anomalies"])


def test_absence_horodatage_signalee():
    q, r, j = scenario()
    j["cas"][0]["fin_iso"] = None
    bilan = auditer(q, r, j, 10)
    assert any("horodatages" in a["description"] for a in bilan["anomalies"])


def test_declarations_vides_signalees():
    q, r, j = scenario()
    j["cas"][0]["reconnaissance_fortuite_origine"] = None
    bilan = auditer(q, r, j, 10)
    assert any("déclaration absente" in a["description"] for a in bilan["anomalies"])
