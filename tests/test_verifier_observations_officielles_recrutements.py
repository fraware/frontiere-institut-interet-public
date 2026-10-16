"""Régression : même projet scientifique n'établit pas un recrutement échoué.

Les assertions testent la portée des énoncés du registre. Elles ne
reconstituent pas les pages web et ne prétendent pas les certifier.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.verifier_observations_officielles_recrutements import (
    PreuveInadmissible, verifier_rapport
)

CHEMIN = Path("evaluation/observations_officielles_recrutements_2026-10-15.json")


def lire_registre() -> dict:
    return json.loads(CHEMIN.read_text(encoding="utf-8"))


def test_quatre_pieces_officielles_deux_annonces_distinctes():
    r = lire_registre()
    bilan = verifier_rapport(r)
    assert bilan["sources_officielles_referencees"] == 4
    assert bilan["annonces_preco_bove_distinctes"] == 2
    assert bilan["deux_echeances_de_candidature_documentees"]
    assert bilan["deficits_de_capacite_confirmes"] == 0
    assert not bilan["pages_archives_avec_sha256"]
    assert bilan["recrutements_pourvus_confirmes"] == 0


@pytest.mark.parametrize("changer", [
    lambda x: x.update({"preuves_web_capturees_sha256": True}),
    lambda x: x["observations"][0].update(
        {"date_limite_candidature": "2026-09-25"}),
    lambda x: x["observations"][0].update(
        {"date_limite_candidature": "2026-02-30"}),
    lambda x: x["observations"][1].update(
        {"contrat_annonce": "18 mois"}),
    lambda x: x["observations"][1].update(
        {"url": "https://malveillant.example/offre-emploi/2026-2398908"}),
    lambda x: x["observations"][2].update(
        {"url": "http://choisirleservicepublic.gouv.fr/offre-emploi/DEF_04-00070536"}),
    lambda x: x["observations"][3].update(
        {"information_affichee": "poste pourvu"}),
    lambda x: x["observations"].append(x["observations"][0]),
    lambda x: x["recoupements"][0].update(
        {"recrutement_anterieur_echoue": "oui"}),
    lambda x: x["recoupements"][0].update(
        {"republication_du_meme_poste": "oui"}),
    lambda x: x["recoupements"][0].update(
        {"nombre_de_postes_distincts": 1}),
    lambda x: x["etats_non_etablis"].update({"recrutements_pourvus": 2}),
    lambda x: x["etats_non_etablis"].update(
        {"organisme_contacte_dans_cette_enquete": True}),
    lambda x: x["contexte_financement"].update(
        {"etat_paiement": "verse"}),
    lambda x: x["contexte_financement"].update(
        {"url": "https://exemple.invalid/anr.pdf"}),
])
def test_refuser_les_inferences_non_documentees(changer):
    r = deepcopy(lire_registre())
    changer(r)
    with pytest.raises(PreuveInadmissible):
        verifier_rapport(r)
