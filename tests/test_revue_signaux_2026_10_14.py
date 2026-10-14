"""Règles de preuve pour la première qualification manuelle des signaux de veille."""
from __future__ import annotations

import json
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def test_les_dix_publications_restent_identifiables_dans_le_flux_archive():
    registre = json.loads(
        (RACINE / "institutionnel/veille/revue_signaux_2026_10_14.json").read_text(
            encoding="utf-8"
        )
    )
    archive = json.loads(
        (RACINE / "institutionnel/flux_publics/observations.json").read_text(
            encoding="utf-8"
        )
    )
    assert registre["version"] == "revue-signaux-v1"
    assert registre["qualification_basee_sur_extraits_uniquement"] is True
    assert registre["validation_externe_realisee"] is False
    assert len(registre["observations"]) == 10
    par_id = {item["identifiant_publication"]: item for item in archive["observations"]}
    ids = set()
    for observation in registre["observations"]:
        uid = observation["id_observation"]
        assert uid not in ids
        ids.add(uid)
        assert uid in par_id
        origine = par_id[uid]
        assert observation["source_id"] == origine["source_id"]
        assert len(observation["empreinte_contenu_reference"]) == 64
        # Une révision du flux est signalée par le suivi, sans bloquer sa collecte.
        assert observation["url_source"] == origine["lien"]
        assert observation["date_publication_source"] == origine["date_publication"]
        assert observation["date_observation_initiale"] == origine["observe_initialement_le"]
        assert observation["orientation_provisoire"] in registre["orientations_autorisees"]
        assert observation["fondement_de_la_qualification"] == (
            "titre_et_extrait_conserves_uniquement"
        )
        assert observation["lecture_document_primaire_integral"] is False
        assert observation["besoin_public_demontre"] is False
        assert observation["usage_effectif_demontre"] is False
        assert observation["effet_causal_demontre"] is False
        assert observation["question_a_resoudre"]
        assert observation["piece_primaire_a_rechercher"]


def test_dates_absentes_ne_sont_pas_reconstituees_depuis_la_collecte():
    registre = json.loads(
        (RACINE / "institutionnel/veille/revue_signaux_2026_10_14.json").read_text(
            encoding="utf-8"
        )
    )
    sans_date = [x for x in registre["observations"]
                 if x["date_publication_source"] is None]
    assert len(sans_date) == 4
    assert all(x["date_observation_initiale"] for x in sans_date)


def test_proportions_de_qualification_sont_des_categories_et_non_des_resultats():
    registre = json.loads(
        (RACINE / "institutionnel/veille/revue_signaux_2026_10_14.json").read_text(
            encoding="utf-8"
        )
    )
    orientations = [x["orientation_provisoire"] for x in registre["observations"]]
    assert orientations.count("piste_mecanisme_scientifique") == 2
    assert orientations.count("piste_mecanisme_institutionnel") == 1
    assert orientations.count("contexte_reglementaire") == 5
    assert orientations.count("commentaire_general") == 1
    assert orientations.count("contexte_sectoriel") == 1
