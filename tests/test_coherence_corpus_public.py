import json
from pathlib import Path

from scripts.verifier_corpus_public import valider_date, verifier

ROOT = Path(__file__).resolve().parents[1]


def test_dates_a_precision_conservee():
    assert valider_date("2026", "annee")
    assert valider_date("2026-04", "mois")
    assert valider_date("2026-04-07", "jour")
    assert valider_date("2023-fin", "intervalle")
    assert valider_date("2024-S2", "intervalle")
    assert valider_date("2025-2033", "intervalle")
    assert not valider_date("2026-02-30", "jour")
    assert not valider_date("2026-13", "mois")
    assert not valider_date("2024-S2", "jour")
    assert not valider_date("2033-2025", "intervalle")


def test_controle_corpus_reel_sur_chronologies_v3():
    signaux = json.loads((ROOT / "donnees" / "signaux_publics_v1.json").read_text(encoding="utf-8"))
    chronos = json.loads((ROOT / "donnees" / "chronologies_v3.json").read_text(encoding="utf-8"))
    rapport = verifier(signaux, chronos)
    assert rapport["valide_structurellement"], rapport["erreurs"]
    assert rapport["nombre_signaux"] == 50
    assert rapport["niveaux_documentaires"]["cas_solide"] == 16
    assert rapport["nombre_chronologies"] == 10
    assert rapport["nombre_evenements"] > 0


def test_controle_rejette_lien_inconnu_et_date_invalide():
    signaux = {
        "nombre_signaux": 1,
        "signaux": [{
            "id_signal": "S001",
            "niveau_documentaire": "cas_solide",
            "titre": "Cas fictif",
            "institution": "Organisme fictif",
            "fait_documente": "Fait fictif",
            "capacite_concernee": "Capacité fictive",
            "source_url": "https://exemple.fr",
            "date_source": "2025",
        }],
    }
    chronos = {"chronologies": [{
        "id_signal": "S999",
        "evenements": [{"date": "2026-02-30", "precision": "jour", "evenement": "Événement fictif"}],
    }]}
    rapport = verifier(signaux, chronos)
    assert not rapport["valide_structurellement"]
    assert any("signal inexistant" in erreur for erreur in rapport["erreurs"])
    assert any("date ou précision" in erreur for erreur in rapport["erreurs"])
