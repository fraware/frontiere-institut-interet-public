"""Vérifier l'origine et le statut de six comparateurs SAPS-CPPE 2026.

Les projets sont une sélection de travail, non un recensement exhaustif des
travaux ni une preuve de financement ou de déploiement scientifique.
"""
from __future__ import annotations

import json
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
COMPARATEURS = RACINE / "institutionnel/programmes_scientifiques/comparateurs_saps_cppe_2026_v1.json"
CHRONOLOGIE = RACINE / "institutionnel/programmes_scientifiques/chronologie_documentaire_v1.json"
PDF_PRIMAIRE = "https://anr.fr/fileadmin/aap/2026/selection/aap-saps-cppe-2026-selection.pdf"


def test_provenance_categories_et_absence_inference():
    corpus = json.loads(COMPARATEURS.read_text(encoding="utf-8"))
    chrono = json.loads(CHRONOLOGIE.read_text(encoding="utf-8"))
    saps = next(p for p in chrono["programmes"] if p["id"] == "saps_cppe_2026")
    selection = saps["evenements"][-1]
    assert corpus["version"] == 1
    assert corpus["source_primaire"] == PDF_PRIMAIRE
    assert corpus["corpus_total_selectionnes"] == 22
    assert corpus["corpus_total_complementaires"] == 5
    assert len(corpus["cas"]) == 6
    vus = set()
    for fiche in corpus["cas"]:
        assert fiche["id"] not in vus
        vus.add(fiche["id"])
        if fiche["statut_selection"] == "selectionne":
            assert fiche["id"] in selection["acronymes_selectionnes"]
        else:
            assert fiche["statut_selection"] == "liste_complementaire"
            assert fiche["id"] in selection["acronymes_liste_complementaire"]
        assert fiche["titre"]
        assert fiche["coordinateur"]
        assert fiche["page_pdf"] in (1, 2, 3)
        assert fiche["question"] and fiche["preuve_prioritaire"]
        assert fiche["interpretation_mecanisme"] == "hypothese_a_examiner"
        for cle in (
            "identite_partenaire_administratif",
            "notification_attribution_aide",
            "travaux_realises",
            "usage_administratif",
            "difficulte_recurrente_de_mobilisation",
        ):
            assert fiche[cle].startswith("non_etabli") or fiche[cle] == "non_etablie"
    assert vus == {"DATSUM", "EXACT", "GRANCOMM", "HYDRISK", "ARBOR", "CEPIP-InSERRE"}


def test_aucun_projet_complementaire_presentation_comme_selectionne():
    corpus = json.loads(COMPARATEURS.read_text(encoding="utf-8"))
    extra = [f for f in corpus["cas"] if f["statut_selection"] == "liste_complementaire"]
    assert len(extra) == 1
    assert extra[0]["id"] == "CEPIP-InSERRE"
    assert extra[0]["notification_attribution_aide"] == "non_etablie"
