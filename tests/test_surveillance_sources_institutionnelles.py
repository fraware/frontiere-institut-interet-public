from scripts.surveiller_sources_institutionnelles import (
    fraicheur,
    lister_erreurs_critiques,
)
from datetime import datetime, timezone


def test_cadence_cog_est_explicitement_traitee():
    source = {
        "cadence_attendue": "annuelle_avec_verification_hebdomadaire",
        "reference_le": "2026-01-01",
    }
    observation = {}
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

def test_classification_de_l_acces_refuse_ne_juge_pas_le_producteur():
    """Le statut HTTP d'un robot ne prouve pas l'indisponibilité de la source."""
    from scripts.surveiller_sources_institutionnelles import (
        classifier_erreur_source, construire_alertes,
    )
    erreur = "HTTPError: HTTP Error 403: Forbidden"
    assert classifier_erreur_source(erreur) == "ACCES_REFUSE_CLIENT_AUTOMATISE"
    assert classifier_erreur_source("HTTPError: HTTP Error 429: Too Many Requests") == (
        "LIMITATION_TEMPORAIRE_ACCES"
    )
    assert classifier_erreur_source("HTTPError: HTTP Error 404: Not Found") == (
        "RESSOURCE_NON_TROUVEE_A_CETTE_ADRESSE"
    )
    alertes = construire_alertes(
        {"sources": []},
        {"sources": [{"source_id": "ape", "criticite": "moyenne", "erreur": erreur}]},
    )
    assert alertes[0]["type"] == "ACCES_REFUSE_CLIENT_AUTOMATISE"


def test_code_source_explicitement_enregistre_prime_sur_texte():
    from scripts.surveiller_sources_institutionnelles import construire_alertes

    alertes = construire_alertes({"sources": []}, {"sources": [{
        "source_id": "exemple",
        "criticite": "haute",
        "erreur": "HTTPError: HTTP Error 403: Forbidden",
        "code_erreur": "DIAGNOSTIC_SOURCE",
    }]})
    assert alertes[0]["type"] == "DIAGNOSTIC_SOURCE"
