"""Vérifier les deux enquêtes statistiques sans fusionner projets, délais et moyens."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

RACINE = Path(__file__).resolve().parents[1]
DOSSIERS = RACINE / "institutionnel/programmes_scientifiques"
HOTES = {"www.ipp.eu", "www.cnis.fr", "www.senat.fr", "www.assemblee-nationale.fr"}


def charger(nom: str) -> dict:
    return json.loads((DOSSIERS / nom).read_text(encoding="utf-8"))


def test_cinq_sources_et_six_jalons_fidelipro_respectent_la_nature_de_preuve():
    f = charger("chronologie_fidelipro_sources_2023_2026_v1.json")
    assert f["version"] == 1
    assert f["etat_au"] == "2026-10-14"
    assert len(f["sources"]) == 5
    assert len(f["jalons"]) == 6
    sources = {s["id"]: s for s in f["sources"]}
    assert len(sources) == 5
    assert {urlsplit(s["url"]).hostname for s in sources.values()} == HOTES
    assert all(urlsplit(s["url"]).scheme == "https" for s in sources.values())
    assert sources["ipp_note92_2023"]["date_document"] == "2023-06"
    assert sources["senat_rapport760_2026"]["date_document"] == "2026-06-17"
    assert sources["assemblee_rapport3056_2026"]["date_document"] == "2026-07-08"
    for jalon in f["jalons"]:
        assert jalon["source_id"] in sources
        assert jalon["qualification"]
        assert jalon["statut"]
    assert {j["statut"] for j in f["jalons"] if j["type"] == "travail_prevu"} == {
        "programme_de_travail"
    }
    assert len([j for j in f["jalons"] if j["type"] == "travail_prevu"]) == 2
    recherche_ipp = next(j for j in f["jalons"] if j["id"] == "resultat_ipp_2016_publie_2023")
    assert recherche_ipp["type"] == "travail_scientifique_realise_distinct_de_fidelipro"
    assert recherche_ipp["statut"] == "publication_scientifique_documentee"
    assert "premiere_production_periodique" in f["inconnus"]
    assert "statut_de_selection_dossier_anr" in f["inconnus"]
    assert "convention_anr" in f["inconnus"]


def test_candidature_ancienne_liee_sans_devenir_selection_ou_financement():
    candidature = charger("candidature_fidelipro_2026_v1.json")
    chrono = charger("chronologie_fidelipro_sources_2023_2026_v1.json")
    assert candidature["chronologie_documentaire_complementaire"] == (
        "institutionnel/programmes_scientifiques/"
        "chronologie_fidelipro_sources_2023_2026_v1.json"
    )
    assert candidature["id"] == "fidelipro_candidature_anr_saps_cppe_2026"
    assert "selection_par_anr" in candidature["etats_non_etablis"]
    assert "convention_signee" in candidature["etats_non_etablis"]
    assert "Insee" in chrono["organismes_mentions"]


def test_dmtg_ressources_constatees_et_annoncees_sont_distinctes():
    d = charger("dmtg_statistiques_successorales_senat_2026_v1.json")
    f = charger("chronologie_fidelipro_sources_2023_2026_v1.json")
    assert d["version"] == 1
    assert d["source"]["date_source"] == "2026-06-17"
    assert d["source"]["url"] == "https://www.senat.fr/rap/r25-760/r25-760_mono.html"
    assert d["donnees_historiques"]["annees_enquetes_dmtg"] == [1994, 2001, 2006, 2010]
    assert d["moyens_rapportes"]["etp_constates_au_rapport"] == 0.5
    assert d["moyens_rapportes"]["etp_additionnel_annonce"] == 1
    assert d["moyens_rapportes"]["date_annoncee"] == "2026-09"
    assert d["moyens_rapportes"]["realisation_de_l_annonce"] == "non_verifiee"
    assert "recrutement_effectif_en_septembre_2026" in d["non_etablis"]
    assert "effet_causal_d_une_nouvelle_institution" in d["non_etablis"]
    assert d["relation_avec_fidelipro"].startswith("cas_different")
    assert d["id"] != f["id"]
    assert all(x["statut"] == "proposition_du_rapport"
               for x in d["recommandations_parlementaires"])
    assert "capacite_d_analyse" in d["hypotheses_a_departager"]


def test_aucun_fichier_fiscal_individuel_ou_statut_de_mission_realisee():
    f = charger("chronologie_fidelipro_sources_2023_2026_v1.json")
    d = charger("dmtg_statistiques_successorales_senat_2026_v1.json")
    assert "Aucun fichier fiscal individuel" in f["donnees_personnelles"]
    assert "enquete_dmtg_2_0_formellement_lancee" in d["non_etablis"]
    assert "premiers_fichiers_statistiques_produits" in d["non_etablis"]



def test_volume_et_offre_de_competences_sont_documentes_sans_recrutement_presume():
    dossier = charger("dmtg_statistiques_successorales_senat_2026_v1.json")
    pieces = {s["id"]: s for s in dossier["sources_complementaires"]}
    assert len(pieces) == 2
    offre = pieces["dgfip_offre_stage_traitement_dmtg_2026"]
    assert offre["url"].startswith("https://www.pass.fonction-publique.gouv.fr/")
    assert offre["nature"] == "fiche_officielle_offre_de_stage"
    reponse = pieces["reponse_ministerielle_question_11677_2026"]
    assert reponse["date_publication"] == "2026-03-10"
    assert reponse["url"].startswith("https://questions.assemblee-nationale.fr/")
    faits = dossier["faits_complementaires"]
    assert faits["effectif_total_desf_renseigne_par_offre"] == "un_peu_plus_de_40_agents"
    assert faits["volume_pdfs_par_an_estime"] == 330000
    assert faits["statut_volume"].startswith("charge_de_documents_annoncee")
    assert faits["activite_preparatoire"].startswith("les_equipes_du_desf_ont_deja_commence")
    assert "python" in faits["competences_recherchees"]
    assert "optimisation_logicielle" in faits["competences_recherchees"]
    assert faits["stage_prevu"]["contrat_effectivement_pourvu"] == "non_etabli"
    assert faits["reponse_ministerielle"]["etat_deploiement_reel_en_octobre"] == "non_verifie"
    assert dossier["moyens_rapportes"]["etp_constates_au_rapport"] == 0.5
    assert dossier["moyens_rapportes"]["etp_additionnel_annonce"] == 1
