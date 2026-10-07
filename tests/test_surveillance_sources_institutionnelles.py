from scripts.surveiller_sources_institutionnelles import (
    fraicheur,
    lister_erreurs_critiques,
)
from datetime import datetime, timezone


def test_cadence_cog_est_explicitement_traitee():
    source = {"cadence_attendue": "annuelle_avec_verification_hebdomadaire"}
    observation = {"derniere_mise_a_jour": "2026-02-24T00:00:00+00:00"}
    resultat = fraicheur(source, observation, datetime(2026, 10, 7, tzinfo=timezone.utc))
    assert resultat["statut"] == "FRAIS"
    assert resultat["seuil_jours"] == 400


def test_cadence_evenementielle_est_non_applicable():
    source = {"cadence_attendue": "evenementielle"}
    resultat = fraicheur(source, {}, datetime(2026, 10, 7, tzinfo=timezone.utc))
    assert resultat == {"statut": "NON_APPLICABLE", "seuil_jours": None, "age_jours": None}


def test_seules_les_erreurs_critiques_font_echouer_la_surveillance():
    etat = {
        "sources": [
            {"source_id": "critique", "criticite": "critique", "erreur": "HTTP 500"},
            {"source_id": "haute", "criticite": "haute", "erreur": "HTTP 500"},
            {"source_id": "ok", "criticite": "critique"},
        ]
    }
    assert lister_erreurs_critiques(etat) == ["critique"]
