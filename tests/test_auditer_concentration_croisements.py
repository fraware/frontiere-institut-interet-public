"""Tests de diversité des preuves, sans prétendre établir une pertinence réelle."""
from copy import deepcopy
import json

import pytest

from scripts.auditer_concentration_croisements import (
    calculer, presenter, AuditIncoherent,
)
from scripts.croiser_pistes_capacites import VERSION


def exemple():
    preuve = {
        "niveau": "mission_publiee",
        "expression": "intelligence artificielle",
        "texte_publie": "Atelier proposant une initiation à l'intelligence artificielle",
        "source_id": "service-fictif",
        "sha256_passage_complet": "a" * 64,
    }
    def structure(identifiant):
        return {
            "identifiant": identifiant,
            "niveau_documentaire": "mission_publiee",
            "mobilisabilite": "NON_ETABLIE",
            "disponibilite": "INCONNUE",
            "passages_justificatifs": [dict(preuve)],
        }
    dossiers = []
    for i in range(3):
        dossiers.append({
            "theme": "intelligence_artificielle",
            "date_parution": "2026-10-01",
            "identifiant_avis": "26-" + str(i),
            "acheteur_declare": "Acheteur " + str(i),
            "groupes": {
                "capacite_publiee": [],
                "mission_publiee": [structure("FRONTIERE-INST-A"),
                                    structure("FRONTIERE-INST-B")],
                "domaine_scientifique_publie": [],
                "nom_seul": [],
            },
            "groupes_tronques": {
                "capacite_publiee": False,
                "mission_publiee": False,
                "domaine_scientifique_publie": False,
                "nom_seul": False,
            },
            "recherche_tronquee": False,
            "besoin_scientifique_valide": False,
            "disponibilite_etablie": False,
            "qualification_humaine_effectuee": False,
        })
    croisement = {
        "version": VERSION, "dossiers": dossiers,
        "pistes_par_theme": {"intelligence_artificielle": 3},
        "nombre_pistes": 3,
        "revision_depot_source": "f" * 40,
        "nombre_organismes_dans_index": 7,
        "empreinte_sha256_referentiel": "b" * 64,
    }
    bilan = {
        "empreinte_sha256_sources": "b" * 64,
        "nombre_entites": 7,
        "nombre_capacites_explicitement_publiees": 0,
        "nombre_domaines_scientifiques_publies": 1,
    }
    return croisement, bilan


def test_six_liens_ne_font_qu_une_preuve_distincte():
    c, b = exemple()
    r = calculer(c, b, "c" * 64)
    t = r["par_theme"]["intelligence_artificielle"]
    assert t["pistes"] == 3
    assert t["pistes_avec_passage_publie"] == 3
    assert t["organismes_distincts_par_identifiant"] == 2
    assert t["total_occurrences_passages_publies"] == 6
    assert t["passages_publies_distincts_par_empreinte"] == 1
    assert t["part_passage_le_plus_repris"] == 1
    assert t["passage_le_plus_repris"]["nombre_occurrences"] == 6
    assert r["resultat_experimental_independant"] is False
    assert "6 / 6" in presenter(r)


def test_deux_passages_differents_restent_distincts():
    c, b = exemple()
    second = c["dossiers"][1]["groupes"]["mission_publiee"][0]
    second["passages_justificatifs"][0]["sha256_passage_complet"] = "d" * 64
    r = calculer(c, b, "c" * 64)
    t = r["par_theme"]["intelligence_artificielle"]
    assert t["passages_publies_distincts_par_empreinte"] == 2
    assert t["part_passage_le_plus_repris"] == round(5 / 6, 4)


def test_exclusion_d_un_bilan_institutionnel_perime():
    c, b = exemple()
    b["empreinte_sha256_sources"] = "e" * 64
    with pytest.raises(AuditIncoherent, match="Provenance"):
        calculer(c, b, "c" * 64)


def test_refus_d_une_capacite_faussement_validee():
    c, b = exemple()
    c["dossiers"][0]["disponibilite_etablie"] = True
    with pytest.raises(AuditIncoherent, match="validé"):
        calculer(c, b, "c" * 64)


def test_piste_sans_correspondance_conservee():
    c, b = exemple()
    c["dossiers"].append({
        "theme": "robotique",
        "date_parution": "2026-10-01",
        "identifiant_avis": "26-robot",
        "acheteur_declare": "Organisme fictif",
        "groupes": {k: [] for k in ("capacite_publiee","mission_publiee",
                                  "domaine_scientifique_publie","nom_seul")},
        "groupes_tronques": {},
        "recherche_tronquee": False,
        "besoin_scientifique_valide": False,
        "disponibilite_etablie": False,
        "qualification_humaine_effectuee": False,
    })
    c["pistes_par_theme"]["robotique"] = 1
    c["nombre_pistes"] = 4
    r = calculer(c, b, "c" * 64)
    t = r["par_theme"]["robotique"]
    assert t["pistes_avec_passage_publie"] == 0
    assert t["total_occurrences_passages_publies"] == 0
    assert t["passage_le_plus_repris"] is None
    assert t["part_passage_le_plus_repris"] is None


def test_refuse_une_preuve_sans_empreinte():
    c, b = exemple()
    c["dossiers"][0]["groupes"]["mission_publiee"][0]["passages_justificatifs"][0].pop(
        "sha256_passage_complet",
    )
    with pytest.raises(AuditIncoherent, match="Empreinte"):
        calculer(c, b, "c" * 64)
