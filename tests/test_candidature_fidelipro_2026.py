"""Filiation probatoire d'une candidature parlementaire distincte de la sélection ANR."""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "institutionnel/programmes_scientifiques"


def test_fidelipro_reste_une_candidature_documentee():
    candidature = json.loads((BASE / "candidature_fidelipro_2026_v1.json").read_text(encoding="utf-8"))
    assert candidature["version"] == 1
    assert candidature["programme_reference"] == "SAPS–CPPE 2026"
    assert "assemblee-nationale.fr" in candidature["source_primaire"]
    assert {x["nom"] for x in candidature["acteurs_cites"]} == {
        "Département des études et statistiques fiscales (DESF)",
        "Insee",
        "Institut des politiques publiques (IPP)",
    }
    assert candidature["relation_avec_datsum_ou_exact"] == "aucune_relation_documentee"
    assert "selection_par_anr" in candidature["etats_non_etablis"]
    assert "mise_en_production_reguliere" in candidature["etats_non_etablis"]
    assert "aide_attribuee" in candidature["etats_non_etablis"]


def test_aucun_rattachement_automatique_aux_projets_selectionnes():
    selection = json.loads((BASE / "chronologie_documentaire_v1.json").read_text(encoding="utf-8"))
    candidature = json.loads((BASE / "candidature_fidelipro_2026_v1.json").read_text(encoding="utf-8"))
    saps = next(x for x in selection["programmes"] if x["id"] == "saps_cppe_2026")
    inscrits = saps["evenements"][-1]["acronymes_selectionnes"]
    assert candidature["id"] not in inscrits
    assert "sans_correspondance_validee" in candidature["position_dans_corpus"]
