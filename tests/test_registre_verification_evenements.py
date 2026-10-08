import json
from pathlib import Path

from scripts.construire_registre_verification_evenements import construire

RACINE = Path(__file__).resolve().parents[1]


def test_registre_coherent_avec_les_chronologies():
    signaux = json.loads((RACINE / "donnees" / "signaux_publics_v1.json").read_text(encoding="utf-8"))
    chronos = json.loads((RACINE / "donnees" / "chronologies_v3.json").read_text(encoding="utf-8"))
    registre = json.loads((RACINE / "donnees" / "registre_verification_evenements_v1.json").read_text(encoding="utf-8"))
    assert construire(signaux, chronos) == registre
    assert registre["nombre_evenements"] == 48
    assert len(set(x["identifiant_evenement"] for x in registre["evenements"])) == 48


def test_aucun_evenement_n_est_declare_verifie_sans_relecture():
    registre = json.loads((RACINE / "donnees" / "registre_verification_evenements_v1.json").read_text(encoding="utf-8"))
    assert all(x["preuve_directe_de_cet_evenement"] == "A_VERIFIER" for x in registre["evenements"])
    assert all(x["resultat_relecture"] is None for x in registre["evenements"])
    assert all(x["source_candidate_du_signal"].startswith("https://") for x in registre["evenements"])


def test_les_dates_partielles_restent_identiques_aux_sources():
    registre = json.loads((RACINE / "donnees" / "registre_verification_evenements_v1.json").read_text(encoding="utf-8"))
    assert any(x["date_documentee"] == "2023-fin" and x["precision_temporelle"] == "intervalle"
               for x in registre["evenements"])
    assert any(x["date_documentee"] == "2024-S2" and x["precision_temporelle"] == "intervalle"
               for x in registre["evenements"])
