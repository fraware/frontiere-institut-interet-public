"""Contrôler le bilan public des sept ressources et ses dénominateurs."""
from __future__ import annotations

import json
from pathlib import Path
import re

BILAN = Path("institutionnel/decp/bilan_sept_mois_2026_10_13.json")
HEX64 = re.compile(r"[0-9a-f]{64}")
MOIS = {"2025-08", "2025-10", "2025-12", "2026-02",
        "2026-03", "2026-04", "2026-05"}


def test_bilan_sept_mois_source_et_unites():
    rapport = json.loads(BILAN.read_text(encoding="utf-8"))
    assert rapport["version"] == "bilan-decp-sept-mois-v1"
    assert rapport["source_catalogue"] == "mef_decp_consolides"
    assert rapport["execution_originale"].endswith("/actions/runs/38484330790")
    assert HEX64.fullmatch(rapport["sha256_rapport_original"])
    assert HEX64.fullmatch(rapport["sha256_rapport_initial_trois_mois"])
    assert HEX64.fullmatch(rapport["sha256_rapport_cibles_boamp"])
    sources = rapport["sources"]
    assert len(sources) == len(MOIS)
    assert {s["mois"] for s in sources} == MOIS
    assert {s["origine"] for s in sources} == {"anterieure", "nouvelle"}
    assert len({s["ressource_id"] for s in sources}) == len(MOIS)
    assert all(HEX64.fullmatch(s["sha256_fichier_brut"]) for s in sources)
    assert all(s["octets"] > 0 for s in sources)


def test_bilan_sept_mois_denominateurs_et_rejets():
    d = json.loads(BILAN.read_text(encoding="utf-8"))
    mesures, sources = d["mesures"], d["sources"]
    assert mesures["objets_documentaires_lus"] == (
        mesures["observations_marches"] + mesures["concessions_exclues"]
    )
    assert mesures["observations_marches"] == (
        mesures["observations_normalisees"] + mesures["notices_rejetees"]
    )
    assert mesures["notices_rejetees"] == 0
    for nom_bilan, nom_source in [
        ("observations_marches", "notices_marche_lues"),
        ("offres_non_communiquees_nc", "offres_nc"),
        ("identites_distinctes_additionnees_par_fichier",
         "identites_distinctes_dans_fichier"),
        ("repetitions_identites_dans_fichier", "repetitions_dans_fichier"),
    ]:
        assert mesures[nom_bilan] == sum(x[nom_source] for x in sources)
    assert mesures["observations_normalisees"] == (
        mesures["variantes_documentaires_distinctes"]
        + mesures["repetitions_variantes_identiques"]
    )
    assert mesures["identites_uniques_entre_mois"] <= (
        mesures["identites_distinctes_additionnees_par_fichier"]
    )
    assert mesures["identites_uniques_entre_mois"] <= (
        mesures["variantes_documentaires_distinctes"]
    )
    assert mesures["identites_avec_plusieurs_variantes"] <= (
        mesures["identites_uniques_entre_mois"]
    )
    assert mesures["identites_dans_plusieurs_mois"] <= (
        mesures["identites_uniques_entre_mois"]
    )


def test_bilan_sept_mois_nattribue_aucun_contrat():
    d = json.loads(BILAN.read_text(encoding="utf-8"))
    m = d["mesures"]
    assert m["pistes_reference_et_meme_siret_acheteur"] == 0
    assert m["contrats_juridiquement_confirmes"] == 0
    assert m["homonymies_reference_avec_autre_acheteur"] == 1
    assert m["references_decp_communes_avec_cibles_boamp_tous_acheteurs"] == 1
    collision = d["homonymie_identifiee"]
    assert collision["siret_acheteur_decp"] != collision["siret_acheteur_dans_avis_boamp"]
    assert collision["preuve_contrat_confirme"] is False
    assert d["limites"]["corpus_national_exhaustif"] is False
