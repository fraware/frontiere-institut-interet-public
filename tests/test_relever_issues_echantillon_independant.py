"""Essais du relevé des issues sans étiquettes indépendantes inventées."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pytest

from scripts.tirer_jeu_independant_boamp import MOIS, QUOTA, EXCLUS, VERSION as VERSION_TIRAGE
from scripts.relever_issues_echantillon_independant import (
    charger_tirage, qualifier, capturer, ReleveInvalide,
)
from scripts.collecter_notices_pilotes_boamp import adresse


def notice(code, date, nature, *, resultats=None):
    contenu = None
    if nature == "ATTRIBUTION":
        bloc = {"efac:LotResult": resultats}
        contenu = {"EFORMS": {"ContractAwardNotice": {
            "ext:UBLExtensions": {"ext:UBLExtension": {
                "ext:ExtensionContent": {"efext:EformsExtension": {
                    "efac:NoticeResult": bloc,
                }},
            }},
        }}}
    return json.dumps({"total_count": 1, "results": [{
        "idweb": code, "dateparution": date, "nature": nature,
        "donnees": json.dumps(contenu) if contenu is not None else None,
    }]}).encode("utf-8")


def lot(code, etat, motif=None):
    x = {
        "efac:TenderLot": {"cbc:ID": {"#text": code}},
        "cbc:TenderResultCode": {"#text": etat},
        "efac:ReceivedSubmissionsStatistics": {
            "efbc:StatisticsCode": {"#text": "t-esubm"},
            "efbc:StatisticsNumeric": "0" if etat == "clos-nw" else "1",
        },
    }
    if motif is not None:
        x["efac:DecisionReason"] = {
            "efbc:DecisionReasonCode": {"#text": motif}
        }
    return x


def tirage_fictif(tmp_path):
    code = 900
    cas = []
    for mois in MOIS:
        for n in range(QUOTA):
            cas.append({
                "avis": f"26-{code}", "date_parution": mois + "-08",
            })
            code += 1
    ids = [x["avis"] for x in cas]
    assert not set(ids) & EXCLUS
    digest = hashlib.sha256(json.dumps(
        ids, ensure_ascii=False, separators=(",", ":"),
    ).encode()).hexdigest()
    fichier = tmp_path / "tirage.json"
    fichier.write_text(json.dumps({
        "version": VERSION_TIRAGE, "nombre_cas": len(cas),
        "sha256_identifiants_ordonnes": digest, "cas": cas,
        "etiquettes_officielles_verifiees": False,
        "comparaison_de_methodes_effectuee": False,
    }), encoding="utf-8")
    return fichier, cas


def test_attribution_mixtes_resultats_lots():
    raw = notice("26-900", "2026-01-08", "ATTRIBUTION", resultats=[
        lot("LOT-0001", "selec-w"),
        lot("LOT-0002", "clos-nw", "no-rece"),
    ])
    q = qualifier(raw, "26-900", "2026-01-08")
    assert q["statut_releve"] == "attribution_officielle_avec_resultats"
    assert [i["qualification_regle_automatique"] for i in q["resultats_lots"]] == [
        "attribue_dans_cet_avis", "absence_offre_explicite",
    ]
    assert all(i["confirmation_independante"] is False for i in q["resultats_lots"])


def test_avis_initial_n_est_pas_consultation_sans_offre():
    q = qualifier(notice("26-901", "2026-02-08", "APPEL_OFFRE"),
                 "26-901", "2026-02-08")
    assert q["resultats_lots"] == []
    assert q["statut_releve"] == "avis_observe_sans_resultat_attribution"


def test_donnees_manquantes_et_dates_divergentes_reste_indeterminees():
    absent = qualifier(b'{"total_count":0,"results":[]}', "26-900", "2026-01-08")
    assert absent["statut_releve"] == "non_retrouve_lors_du_releve"
    autre = qualifier(notice("26-900", "2026-01-09", "ATTRIBUTION"),
                     "26-900", "2026-01-08")
    assert autre["statut_releve"] == "date_officielle_divergente"
    assert autre["resultats_lots"] == []


def test_refuser_deux_identifiants_ou_total_incorrect():
    with pytest.raises(ReleveInvalide):
        qualifier(b'{"total_count":2,"results":[]}', "26-900", "2026-01-08")


def test_capture_reproductible_et_independance_non_revendiqee(tmp_path):
    fichier, items = tirage_fictif(tmp_path)
    reponses = {
        x["avis"]: notice(x["avis"], x["date_parution"], "APPEL_OFFRE")
        for x in items
    }
    reponses[items[0]["avis"]] = notice(
        items[0]["avis"], items[0]["date_parution"], "ATTRIBUTION",
        resultats=[lot("LOT-0001", "selec-w")],
    )
    def recevoir(url):
        return next(x for k, x in reponses.items() if url == adresse(k))
    dossier = tmp_path / "releve"
    bilan = capturer(fichier, dossier, obtenir=recevoir,
                    maintenant=datetime(2026, 10, 12, tzinfo=timezone.utc))
    assert bilan["nombre_cas"] == 36
    assert bilan["statuts_releve"]["attribution_officielle_avec_resultats"] == 1
    assert bilan["statuts_releve"]["avis_observe_sans_resultat_attribution"] == 35
    assert bilan["issues_lots_couvertes"]["attribue_dans_cet_avis"] == 1
    assert bilan["resultats_independamment_etiquetes"] is False
    assert bilan["comparaison_avec_classifications_concurrentes_effectuee"] is False
    assert len(list(dossier.glob("26-*.json"))) == 36
    assert charger_tirage(fichier)["nombre_cas"] == 36
    with pytest.raises(ReleveInvalide, match="existante"):
        capturer(fichier, dossier, obtenir=recevoir)


def test_mutation_du_tirage_refusee(tmp_path):
    f, _ = tirage_fictif(tmp_path)
    data = json.loads(f.read_text(encoding="utf-8"))
    data["cas"][0]["avis"] = "26-30147"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ReleveInvalide):
        charger_tirage(f)



def test_formulaire_mapa_attribution_sans_inventer_de_numero_lot():
    source = json.dumps({
        "MAPA": {"attribution": {
            "attribution": {"resultat": {"attribue": {
                "titulaire": {"PersonneMorale": "LIBRICIEL SCOP"}
            }}},
            "autresInformations": {
                "dateAttribution": "2025-10-16",
                "nbOffresRecues": "1",
            },
        }}
    })
    raw = json.dumps({"total_count": 1, "results": [{
        "idweb": "25-121097", "dateparution": "2025-10-30",
        "nature": "ATTRIBUTION", "donnees": source,
    }]}).encode()
    qual = qualifier(raw, "25-121097", "2025-10-30")
    assert qual["statut_releve"] == "attribution_structuree_sans_numero_lot"
    assert qual["format_source"] == "mapa"
    assert qual["resultats_lots"] == []
    assert qual["observations_hors_lots"][0]["titulaire_declare"] == "LIBRICIEL SCOP"
    assert qual["observations_hors_lots"][0]["nombre_offres_declare"] == 1
    assert qual["observations_hors_lots"][0]["identifiant_lot_verifie"] is None


def test_fnsimple_attribution_en_texte_libre_n_est_pas_classee_par_lot():
    phrase = "Lots 1 et 2 attribués à ECLIPSE ISTEC SAS"
    raw = json.dumps({"total_count": 1, "results": [{
        "idweb": "25-121801", "dateparution": "2025-10-31",
        "nature": "ATTRIBUTION",
        "donnees": json.dumps({"FNSimple": {"attribution": {
            "attributionMarche": phrase,
        }}}),
    }]}).encode()
    qual = qualifier(raw, "25-121801", "2025-10-31")
    assert qual["statut_releve"] == "attribution_textuelle_non_lotifiee"
    assert qual["resultats_lots"] == []
    assert qual["observations_hors_lots"][0]["texte_officiel"] == phrase
    assert qual["observations_hors_lots"][0]["qualification_regle_automatique"] is None
    assert qual["observations_hors_lots"][0]["confirmation_independante"] is False


def test_mapa_invalide_ne_cree_aucune_attribution():
    raw = json.dumps({"total_count": 1, "results": [{
        "idweb": "25-121097", "dateparution": "2025-10-30",
        "nature": "ATTRIBUTION", "donnees": json.dumps({
            "MAPA": {"attribution": {
                "attribution": {"resultat": {"attribue": {
                    "titulaire": {"PersonneMorale": "EXEMPLE"}
                }}},
                "autresInformations": {"nbOffresRecues": "0"},
            }}
        }),
    }]}).encode()
    qual = qualifier(raw, "25-121097", "2025-10-30")
    assert qual["statut_releve"] == "resultat_officiel_structure_non_interpretee"
    assert qual["resultats_lots"] == []
    assert qual["format_source"] == "mapa"


def test_formulaire_inconnu_reste_explicitement_ininterprete():
    raw = json.dumps({"total_count": 1, "results": [{
        "idweb": "25-121801", "dateparution": "2025-10-31",
        "nature": "ATTRIBUTION", "donnees": json.dumps({
            "AutreSchema": {"attribution": "indéfinie"}
        }),
    }]}).encode()
    qual = qualifier(raw, "25-121801", "2025-10-31")
    assert qual["statut_releve"] == "resultat_officiel_structure_non_interpretee"
    assert qual["format_source"] == "autreschema"
