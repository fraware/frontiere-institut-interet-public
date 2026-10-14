"""Contrôles reproductibles des quatre épisodes SICTIAM/Sicoval/communes."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.valider_episodes_mobilisation import PreuveInvalide, bilan

ROOT = Path(__file__).resolve().parents[1]


def documents():
    return (
        json.loads((ROOT / "donnees/episodes_mobilisation_preuves_v1.json").read_text(
            encoding="utf-8"
        )),
        json.loads((ROOT / "institutionnel/pieces_publiques/observations_pdfs_municipaux.json")
                   .read_text(encoding="utf-8")),
    )


def test_episodes_reels_passent_et_absences_de_preuve_preservees():
    dossier, captures = documents()
    resultat = bilan(dossier, captures)
    assert resultat["nombre_episodes"] == 4
    assert resultat["nombre_sources"] == 6
    assert resultat["nombre_pdfs_municipaux_empreintes"] == 2
    assert resultat["temoignages_usage_dates_par_document"] == 1
    assert resultat["premieres_contributions_utiles_precisement_datees"] == 0
    assert resultat["mesures_effet_independantes"] == 0
    assert resultat["relations_contractuelles_inter_circuits_etablies"] == 0
    assert all(x["delai_besoin_vers_premiere_utilite_jours"] is None
               for x in resultat["episodes"])
    case = next(x for x in resultat["episodes"]
                if x["id_episode"] == "SICTIAM-SAD-2026")
    assert case["intervalles_choix_a_conclusion_jours"] == {
        "CHOIX-TOMORRO": 56, "CHOIX-AUTRES": 25
    }


def test_empreinte_pdf_non_concordante_interrompt_l_inference():
    dossier, captures = documents()
    dossier["sources"][-1]["sha256_pdf"] = "0" * 64
    with pytest.raises(PreuveInvalide, match="octets réellement"):
        bilan(dossier, captures)


def test_source_du_mauvais_circuit_refusee():
    dossier, captures = documents()
    dossier["episodes"][-1]["evenements"][0]["source_id"] = "BOAMP-SICTIAM-26-43435"
    with pytest.raises(PreuveInvalide, match="mauvais circuit"):
        bilan(dossier, captures)


def test_impossibilite_inventer_premier_usage_depuis_temoignage():
    dossier, captures = documents()
    dossier["episodes"][-1]["date_premiere_contribution_utile"] = "2025-06-18"
    with pytest.raises(PreuveInvalide, match="Aucune date"):
        bilan(dossier, captures)


def test_identite_fournisseur_ne_cree_pas_de_contrat_supplementaire():
    dossier, captures = documents()
    dossier["episodes"][2]["relation_contractuelle_avec_autres_episodes_etablie"] = True
    with pytest.raises(PreuveInvalide, match="ne prouve pas"):
        bilan(dossier, captures)


def test_annee_retrospective_refusee_comme_date_exacte():
    dossier, captures = documents()
    evt = dossier["episodes"][2]["evenements"][0]
    evt["date"] = "2024-01-01"
    with pytest.raises(PreuveInvalide, match="année qualitative"):
        bilan(dossier, captures)


def test_source_sans_octets_ne_peut_usurper_une_empreinte():
    dossier, captures = documents()
    dossier["sources"][0]["sha256_pdf"] = "a" * 64
    with pytest.raises(PreuveInvalide, match="Empreinte ou téléchargement"):
        bilan(dossier, captures)


def test_numero_de_page_superieur_au_pdf_recu_refuse():
    dossier, captures = documents()
    dossier["episodes"][2]["evenements"][0]["page_pdf"] = 222
    with pytest.raises(PreuveInvalide, match="Page absente"):
        bilan(dossier, captures)


def test_pas_de_raccourci_de_chronologie_entre_circuits():
    dossier, captures = documents()
    dossier["episodes"][0]["evenements"][3]["date"] = "2025-01-01"
    with pytest.raises(PreuveInvalide, match="Chronologie"):
        bilan(dossier, captures)


def test_anomalie_de_chaine_acheteur_preservee():
    dossier, captures = documents()
    dossier["episodes"][0]["evenements"][1]["date"] = "2026-04-01"
    with pytest.raises(PreuveInvalide, match="Chronologie"):
        bilan(dossier, captures)


def test_episode_en_double_refuse():
    dossier, captures = documents()
    dossier["episodes"].append(deepcopy(dossier["episodes"][0]))
    with pytest.raises(PreuveInvalide, match="dupliqué"):
        bilan(dossier, captures)
