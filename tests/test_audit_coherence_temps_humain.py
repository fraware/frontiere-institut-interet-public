"""Tests des incohérences de temps entre une réponse et son journal."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from scripts.auditer_journaux_sessions import auditer


def documents(minutes_humaines: int, temps_ecoule: int):
    """Créer dix observations entièrement artificielles pour un protocole de séance."""
    codes = [f"H{i:02d}" for i in range(1, 11)]
    origine = datetime(2026, 10, 8, tzinfo=timezone.utc)
    q = {"cas": [{"code": code} for code in codes]}
    r = {
        "version_schema": "reponses-jeu-reserve-v1",
        "methode": "analyste",
        "version_methode": "test-artificiel",
        "cas": [{
            "code": code, "voies": [], "formes_ressource": [], "ressources": [],
            "urls_preuves": [], "duree_secondes": temps_ecoule,
            "minutes_analyste": minutes_humaines, "minutes_verification": 0,
            "notes": "Exemple artificiel",
        } for code in codes],
    }
    j = {
        "version_schema": "journal-session-v1",
        "methode": "analyste",
        "operateur_code": "OPERATEUR_FICTIF",
        "version_logiciel_ou_modele": "test-artificiel",
        "cas": [{
            "code": code,
            "debut_iso": origine.isoformat(),
            "fin_iso": (origine + timedelta(seconds=temps_ecoule)).isoformat(),
            "budget_respecte": True,
            "reconnaissance_fortuite_origine": False,
            "interruptions_ou_ecarts": "",
            "sources_revelant_solution": [],
        } for code in codes],
    }
    return q, r, j


def test_audit_signale_temps_humain_impossible_sans_modifier_les_saisies():
    q, r, j = documents(12, 300)
    audit = auditer(q, r, j, budget_minutes=30)
    assert audit["nombre_anomalies"] == 10
    assert all(
        item["description"] == "temps humain supérieur au temps écoulé"
        for item in audit["anomalies"]
    )
    assert audit["modifications_apportees"] is False
    assert r["cas"][0]["minutes_analyste"] == 12


def test_audit_accepte_duree_compatible_avec_arrondis():
    q, r, j = documents(5, 300)
    audit = auditer(q, r, j, budget_minutes=30)
    assert audit["nombre_anomalies"] == 0
    # Une minute de tolérance couvre les deux relevés entiers arrondis.
    q, r, j = documents(6, 300)
    audit = auditer(q, r, j, budget_minutes=30)
    assert audit["nombre_anomalies"] == 0
