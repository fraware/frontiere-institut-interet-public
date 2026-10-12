"""Contrôles de non-régression des nouveaux constats d'exécution."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.extraire_jalons_execution_publics import (
    ObservationInvalide,
    resumer,
    verifier_observations,
)


def corpus():
    """Charger les observations primaires déclarées dans le dépôt."""
    return json.loads(
        Path("donnees/observations_execution_publiques_2026-10-12.json")
        .read_text(encoding="utf-8")
    )


def test_les_deux_sources_restent_distinctes():
    bilan = resumer(corpus())
    assert bilan["nombre_observations"] == 2
    assert bilan["cas_documentes"] == ["S001", "S024"]
    assert bilan["attestations_retrospectives_datees"] == 1
    assert bilan["descriptions_poste_non_datees"] == 1
    assert bilan["dates_precises_actions_individuelles"] == 0
    assert bilan["temps_jusqua_premiere_contribution_utile_observables"] == 0


def test_saint_brieuc_borne_collective_sans_date_individuelle():
    observation = verifier_observations(corpus())[0]
    assert observation["date_attestation"] == "2024-02-14"
    assert observation["borne_superieure_action_collective"] == "2024-02-14"
    assert observation["date_action_exacte"] is None


def test_fiche_non_datee_interdit_une_date_inventee():
    document = deepcopy(corpus())
    document["observations"][1]["date_attestation"] = "2025-04-01"
    with pytest.raises(ObservationInvalide):
        verifier_observations(document)


def test_attestation_interdit_une_borne_posterieure():
    document = deepcopy(corpus())
    document["observations"][0]["borne_superieure_action_collective"] = "2025-06-01"
    with pytest.raises(ObservationInvalide):
        verifier_observations(document)


def test_identifiant_d_observation_unique():
    document = deepcopy(corpus())
    document["observations"].append(deepcopy(document["observations"][0]))
    with pytest.raises(ObservationInvalide):
        verifier_observations(document)


def test_adresse_non_securisee_refusee():
    document = deepcopy(corpus())
    document["observations"][0]["source"]["url"] = "http://exemple.fr/avis.pdf"
    with pytest.raises(ObservationInvalide):
        verifier_observations(document)
