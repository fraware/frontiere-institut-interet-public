"""Contrôles de provenance et de cohérence temporelle de la revue DMTG.

Aucune vérification ne transforme une offre, une prévision ou une recommandation
en recrutement, volume effectivement traité ou production achevée.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

RACINE = Path(__file__).resolve().parents[1] / "institutionnel/programmes_scientifiques"


def charger(nom):
    return json.loads((RACINE / nom).read_text(encoding="utf-8"))


def test_sources_primaire_et_jalons_sur_chantiers_distincts():
    r = charger("revue_dmtg_moyens_et_echeances_2026_10_14.json")
    assert r["version"] == 1
    assert r["etat_au"] == "2026-10-14"
    sources = {s["id"]: s for s in r["pieces"]}
    assert len(sources) == 7
    assert set(sources) == {
        "fiche_dgfip_decembre_2025",
        "fiche_dgfip_fevrier_2026",
        "reponse_ministerielle_mars_2026",
        "rapport_senat_juin_2026",
        "offre_dp5_moe_septembre_2026",
        "offre_dp5_moa_septembre_2026",
        "dgfip_stats_recettes_2026",
    }
    assert all(urlsplit(s["url"]).scheme == "https" for s in sources.values())
    assert all(urlsplit(s["url"]).hostname in {
        "www.pass.fonction-publique.gouv.fr", "questions.assemblee-nationale.fr",
        "www.senat.fr", "www.passerelles.economie.gouv.fr",
        "passerelles.economie.gouv.fr", "www.impots.gouv.fr",
    } for s in sources.values())
    assert len(r["jalons"]) == 7
    assert all(j["piece_id"] in sources for j in r["jalons"])


def test_deux_volumetries_sont_des_estimates_et_non_des_sorties_reelles():
    r = charger("revue_dmtg_moyens_et_echeances_2026_10_14.json")
    volumes = r["versionnage_charges_annuelles"]
    assert len(volumes) == 2
    assert [p["volume_annuel_estime"] for p in volumes] == [300000, 330000]
    assert all(p["statut"] == "estimation_de_la_charge" for p in volumes)
    assert all(p["effectivement_traite"] is None for p in volumes)


def test_un_etp_annonce_n_est_jamais_assimile_a_un_etp_affecte():
    r = charger("revue_dmtg_moyens_et_echeances_2026_10_14.json")
    d = charger("dmtg_statistiques_successorales_senat_2026_v1.json")
    assert d["moyens_rapportes"]["etp_constates_au_rapport"] == 0.5
    assert d["moyens_rapportes"]["etp_additionnel_annonce"] == 1
    assert d["moyens_rapportes"]["realisation_de_l_annonce"] == "non_verifiee"
    assert any(j["etat"] == "un_etp_supplementaire_annonce_non_confirme"
               for j in r["jalons"])
    assert d["faits_complementaires"]["stage_prevu"][
        "contrat_effectivement_pourvu"
    ] == "non_etabli"
    assert r["recherches_documentaires_negatives"][0]["conclusion"].startswith(
        "non_etabli"
    )


def test_les_trois_calendriers_ne_sont_pas_confondus():
    r = charger("revue_dmtg_moyens_et_echeances_2026_10_14.json")
    jalons = {j["id"]: j for j in r["jalons"]}
    assert jalons["pilotage_declarations_successions_2026"]["date"] == "2026-S2"
    assert jalons["pilotage_declarations_successions_2026"]["type"] == (
        "deploiement_envisage"
    )
    assert jalons["diffusion_microdonnees_2028"]["date"] == "2028"
    assert jalons["diffusion_microdonnees_2028"]["type"] == (
        "objectif_administratif_rapporte"
    )
    assert jalons["couverture_numerisation_2029"]["date"] == "2029"
    assert jalons["couverture_numerisation_2029"]["type"] == (
        "recommandation_parlementaire"
    )
    assert jalons["donations_manuelles_janvier_2026"]["autre_processus"] == (
        "n_etablit_pas_la_dematerialisation_des_successions"
    )


def test_offres_de_poste_dp5_ne_prouvent_aucun_renfort_desf():
    r = charger("revue_dmtg_moyens_et_echeances_2026_10_14.json")
    offres = [x for x in r["pieces"] if x["id"].startswith("offre_dp5_")]
    assert len(offres) == 2
    assert all("DP5" in x["producteur"] for x in offres)
    assert all("aucun lien établi" in x["limite"] or
               "aucune preuve" in x["limite"] for x in offres)


def test_cas_source_et_revue_sont_relies_sans_etat_invente():
    r = charger("revue_dmtg_moyens_et_echeances_2026_10_14.json")
    d = charger("dmtg_statistiques_successorales_senat_2026_v1.json")
    assert r["source_principale"].endswith(
        "/dmtg_statistiques_successorales_senat_2026_v1.json"
    )
    assert d["revue_moyens_et_echeances"].endswith(
        "/revue_dmtg_moyens_et_echeances_2026_10_14.json"
    )
    assert d["faits_complementaires"]["statistique_microdonnees_cible_2028"][
        "premiere_diffusion_effectivement_constatee"
    ] == "non_etablie"
    assert d["faits_complementaires"]["numerisation_declarations_cible_2029"][
        "couverture_effectivement_constatee"
    ] == "non_etablie"
    assert "nombre_de_pdf_extraits_avec_validation_statistique" in d["non_etablis"]


def test_agregats_dmtg_ne_sont_pas_des_microdonnees_successorales():
    r = charger("revue_dmtg_moyens_et_echeances_2026_10_14.json")
    pieces = {piece["id"]: piece for piece in r["pieces"]}
    assert pieces["dgfip_stats_recettes_2026"]["genre"] == "bulletin_statistiques_agregees"
    assert pieces["dgfip_stats_recettes_2026"]["date_document"] == "2026-06"
    assert "microdonnées successorales" in pieces["dgfip_stats_recettes_2026"]["limite"]
    assert r["distinction_statistique"]["agregats_fiscaux_2026"] == "publies_dans_bulletin_dgfip_stats"
    assert r["distinction_statistique"]["microdonnees_successions_nouvelle_serie"] == "publication_comparable_non_retrouvee"
