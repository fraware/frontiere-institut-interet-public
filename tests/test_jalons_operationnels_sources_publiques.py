"""Tests des observations opérationnelles et de leur séparation temporelle."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.bilan_jalons_operationnels_publics import JalonsInvalides, bilan, verifier


def _donnees():
    return json.loads(
        Path("donnees/jalons_operationnels_sources_publiques_2026-10-12.json")
        .read_text(encoding="utf-8")
    )


def _chronologies():
    return json.loads(Path("donnees/chronologies_v9.json").read_text(encoding="utf-8"))


def _identifiants():
    return {x["id_signal"] for x in _chronologies()["chronologies"]}


def test_bilan_reel_ne_fabrique_pas_de_delai():
    resultat = bilan(_donnees(), _chronologies())
    assert resultat["cas_concernes"] == ["S016", "S042", "S050"]
    assert resultat["nombre_sources"] == 3
    assert resultat["nombre_jalons"] == 7
    assert resultat["delais_besoin_vers_premiere_contribution_nouvellement_observes"] == 0
    assert resultat["par_cas"]["S050"]["observations_generation_anterieure"] == 3
    assert resultat["par_cas"]["S016"]["observations_generation_anterieure"] == 0
    assert resultat["par_cas"]["S042"]["dates_individuelles_de_premiere_contribution"] == 0


def test_valeurs_officielles_restituees_sans_recalcul():
    resultat = bilan(_donnees(), _chronologies())
    mesures = {
        ligne["observation"]: ligne["valeur"]
        for entree in resultat["par_cas"].values()
        for ligne in entree["indicateurs"]
    }
    assert mesures["OBS-S016-PROD10"] == 10
    assert mesures["OBS-S016-OCSGE3"] == 3
    assert mesures["OBS-S042-HABIL367"] == 367
    assert mesures["OBS-S042-FORM9135"] == 9135
    assert mesures["OBS-S050-ANCIENS-REC2020"] == 2
    assert mesures["OBS-S050-ANCIENS-GAIN55"] == 5.5
    assert "OBS-S050-ANCIENS-OP2021" not in mesures


@pytest.mark.parametrize("champ,valeur", [
    ("precision_date", "jour"),
    ("date_jour", "2021-01-01"),
    ("lien_avec_cas", "generation_courante"),
])
def test_pas_de_date_inventee_ni_conflation_generation(champ, valeur):
    document = deepcopy(_donnees())
    document["observations"][-2][champ] = valeur
    with pytest.raises(JalonsInvalides):
        verifier(document, _identifiants())


def test_source_inconnue_refusee():
    document = deepcopy(_donnees())
    document["observations"][0]["source_id"] = "inconnue"
    with pytest.raises(JalonsInvalides):
        verifier(document, _identifiants())


def test_indicateur_booleen_refuse():
    document = deepcopy(_donnees())
    document["observations"][0]["indicateur"]["valeur"] = True
    with pytest.raises(JalonsInvalides):
        verifier(document, _identifiants())


def test_identifiant_replique_refuse():
    document = deepcopy(_donnees())
    document["observations"].append(deepcopy(document["observations"][0]))
    with pytest.raises(JalonsInvalides):
        verifier(document, _identifiants())


def test_jalon_inconnu_du_corpus_refuse():
    document = deepcopy(_donnees())
    document["observations"][0]["id_signal"] = "S999"
    with pytest.raises(JalonsInvalides):
        verifier(document, _identifiants())


def test_date_journaliere_reelle_est_conservee():
    jalon = next(x for x in _donnees()["observations"] if x["id"] == "OBS-S042-HABIL367")
    assert jalon["date_jour"] == "2025-12-31"
    assert jalon["periode_reference"] == jalon["date_jour"]
