"""Vérifier la séparation entre l'antécédent HYD2M et le lot de 2025."""
import json
from pathlib import Path


def test_antecedent_radar_reference_un_pilote_exact():
    antecedent = json.loads(
        Path("donnees/antecedent_radar_caen_hyd2m_v1.json").read_text(encoding="utf-8")
    )
    pilotes = json.loads(
        Path("evaluation/cas_pilotes_boamp_v1.json").read_text(encoding="utf-8")
    )
    codes = {cas["identifiant"] for cas in pilotes["cas"]}
    assert antecedent["id_avis_pilote"] == "26-30147"
    assert antecedent["id_avis_pilote"] in codes
    assert antecedent["lot_cible"]["id"] == "LOT-0002"
    assert antecedent["lot_cible"]["motif"] == "no-rece"
    assert antecedent["lot_cible"]["nombre_soumissions_electroniques_declare"] == 0


def test_capacite_historique_ne_devient_pas_preuve_de_mobilisation():
    d = json.loads(
        Path("donnees/antecedent_radar_caen_hyd2m_v1.json").read_text(encoding="utf-8")
    )
    assert d["antecedent_recherche"]["periode"] == "2016-2019"
    assert d["antecedent_recherche"]["duree_mois_declaree"] == 44
    assert d["nature_rapprochement"] == "proximite_thematique_et_acheteur"
    for cle in (
        "identite_de_mission_demontree",
        "identite_des_livrables_demontree",
        "disponibilite_technique_en_2025_demontree",
        "capacite_mobilisable_sur_le_lot_2_demontree",
        "cause_absence_offres_etablie",
    ):
        assert d[cle] is False
    assert d["antecedent_recherche"]["source"]["url"].startswith("https://")


def test_note_separe_antecedent_des_conditions_du_marche():
    note = Path("docs/ANTECEDENT_SCIENTIFIQUE_RADAR_CAEN_2026-10-12.md").read_text(
        encoding="utf-8"
    )
    assert "Un antécédent de recherche n'est pas une candidature au marché." in note
    assert "lot 2" in note
    assert "clauses techniques particulières" in note
