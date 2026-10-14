"""Tests déterministes du contrôle transversal de la veille, sans réseau."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from scripts.auditer_fraicheur_veille import (
    PolitiqueInvalide, auditer_collecte, auditer_procedure, date_utc,
    lire_politique, produire_bilan, resume_markdown,
)

INSTANT = datetime(2026, 10, 14, 18, tzinfo=timezone.utc)


def ecrire(racine: Path, chemin: str, valeur: object) -> None:
    cible = racine / chemin
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(json.dumps(valeur), encoding="utf-8")


def entree(*, criticite: str = "critique", controle: str = "general",
           retard: int = 12) -> dict:
    return {"id": "exemple", "fichier": "institutionnel/etat_exemple.json",
            "horodatage": "controle_le", "retard_max_heures": retard,
            "criticite": criticite, "controle": controle}


def test_releve_recent_et_retard_critique(tmp_path):
    ecrire(tmp_path, "institutionnel/etat_exemple.json", {
        "controle_le": "2026-10-14T10:00:00+00:00", "erreurs": [],
    })
    ok = auditer_collecte(tmp_path, entree(), INSTANT)
    assert ok["statut"] == "ok"
    assert ok["age_heures"] == 8.0
    tard = auditer_collecte(tmp_path, entree(retard=7), INSTANT)
    assert tard["statut"] == "critique"
    assert tard["alertes"][0]["code"] == "RELEVE_RETARDE"


def test_retard_non_critique_et_releve_partiel(tmp_path):
    ecrire(tmp_path, "institutionnel/etat_exemple.json", {
        "controle_le": "2026-10-13T04:00:00Z", "erreurs": [{"type": "HTTPError"}],
    })
    resultat = auditer_collecte(
        tmp_path, entree(criticite="haute", retard=24), INSTANT
    )
    assert resultat["statut"] == "attention"
    assert {a["code"] for a in resultat["alertes"]} == {
        "RELEVE_RETARDE", "RELEVE_PARTIEL",
    }


@pytest.mark.parametrize("brut", ["2026-10-14", "2026-10-14T18:00:00", "invalide", None])
def test_dates_sans_fuseau_ou_incorrectes_refusees(brut):
    with pytest.raises(PolitiqueInvalide):
        date_utc(brut)


def test_releve_dans_le_futur_est_refuse(tmp_path):
    ecrire(tmp_path, "institutionnel/etat_exemple.json", {
        "controle_le": "2026-10-15T18:00:00+00:00",
    })
    resultat = auditer_collecte(tmp_path, entree(), INSTANT)
    assert resultat["statut"] == "critique"
    assert resultat["alertes"][0]["code"] == "ETAT_ILLISIBLE"


def test_fichier_absent_reste_un_echec(tmp_path):
    assert auditer_collecte(tmp_path, entree(), INSTANT)["statut"] == "critique"


def test_erreur_source_critique_et_contenu_ancien(tmp_path):
    ecrire(tmp_path, "institutionnel/etat_exemple.json", {
        "observe_le": INSTANT.isoformat(), "nombre_sources": 2,
        "sources": [
            {"source_id": "dila", "criticite": "critique", "erreur": "HTTP 503",
             "fraicheur": {"statut": "ERREUR"}},
            {"source_id": "recherche", "criticite": "haute",
             "fraicheur": {"statut": "INDETERMINE"}},
        ],
    })
    item = {**entree(controle="referentiel"), "horodatage": "observe_le"}
    resultat = auditer_collecte(tmp_path, item, INSTANT)
    assert resultat["statut"] == "critique"
    codes = [x["code"] for x in resultat["alertes"]]
    assert codes.count("SOURCE_INDISPONIBLE") == 1
    assert codes.count("CONTENU_A_REVOIR") == 1


def test_flux_success_recent_avec_une_source_sans_succes(tmp_path):
    ecrire(tmp_path, "institutionnel/etat_exemple.json", {
        "cycle_le": INSTANT.isoformat(),
        "sources": [
            {"id": "anr", "actif": True, "cadence_heures": 6, "erreur": None,
             "dernier_succes": INSTANT.isoformat()},
            {"id": "veille_secondaire", "actif": True, "cadence_heures": 6,
             "erreur": "Échec isolé", "dernier_succes": None},
        ],
    })
    item = {**entree(controle="flux", criticite="haute"), "horodatage": "cycle_le"}
    resultat = auditer_collecte(tmp_path, item, INSTANT)
    assert resultat["statut"] == "attention"
    assert {a["code"] for a in resultat["alertes"]} == {
        "FLUX_SANS_SUCCES", "FLUX_EN_ERREUR",
    }


def test_horodatage_dans_liste_protegee(tmp_path):
    ecrire(tmp_path, "institutionnel/etat_exemple.json", {
        "catalogues": [{"observe_le": INSTANT.isoformat()}],
    })
    item = {**entree(), "horodatage": "catalogues[0].observe_le"}
    assert auditer_collecte(tmp_path, item, INSTANT)["statut"] == "ok"
    item["horodatage"] = "catalogues[1].observe_le"
    assert auditer_collecte(tmp_path, item, INSTANT)["statut"] == "critique"


def test_procedure_reussie_et_echec_apres_reussite():
    initial = {
        "fichier": "veille-flux-publics.yml", "retard_max_heures": 24,
        "criticite": "critique",
    }
    succes = {"created_at": "2026-10-14T16:00:00Z",
              "updated_at": "2026-10-14T16:10:00Z",
              "status": "completed", "conclusion": "success"}
    echec = {"created_at": "2026-10-14T17:00:00Z",
             "updated_at": "2026-10-14T17:30:00Z",
             "status": "completed", "conclusion": "failure"}
    courant = auditer_procedure(initial, {"workflow_runs": [echec, succes]}, INSTANT)
    assert courant["statut"] == "attention"
    assert courant["age_heures"] < 2
    tres_ancien = {**succes, "created_at": "2026-10-10T16:00:00Z",
                   "updated_at": "2026-10-10T16:10:00Z"}
    vieux = auditer_procedure(initial, {"workflow_runs": [tres_ancien]}, INSTANT)
    assert vieux["statut"] == "critique"
    assert vieux["alertes"][0]["code"] == "PROCEDURE_RETARDEE"


def test_absence_executions_et_erreur_de_consultation(tmp_path):
    politique = {"version": 1, "collectes": [entree(criticite="haute")],
                 "procedures": [{"fichier": "collecte-besoins-publics.yml",
                                 "retard_max_heures": 36, "criticite": "critique"}]}
    ecrire(tmp_path, "institutionnel/etat_exemple.json", {
        "controle_le": INSTANT.isoformat(),
    })
    bilan = produire_bilan(tmp_path, politique, INSTANT,
                           repertoire="fraware/frontiere-institut-interet-public",
                           interroger=lambda *_: {"workflow_runs": []})
    assert bilan["statuts"] == {"ok": 1, "attention": 0, "critique": 1}
    assert "AUCUNE_EXECUTION" in resume_markdown(bilan)
    def echoue(*_args):
        raise OSError("service indisponible")
    erreur = produire_bilan(tmp_path, politique, INSTANT,
                           repertoire="fraware/frontiere-institut-interet-public",
                           interroger=echoue)
    assert erreur["controles"][-1]["alertes"][0]["code"] == (
        "CONTROLE_EXECUTION_IMPOSSIBLE"
    )


def test_configuration_refuse_fuite_de_chemin(tmp_path):
    politique = {"version": 1, "collectes": [{**entree(),
                 "fichier": "institutionnel/../secret.json"}],
                "procedures": []}
    fichier = tmp_path / "politique.json"
    fichier.write_text(json.dumps(politique), encoding="utf-8")
    with pytest.raises(PolitiqueInvalide, match="Chemin"):
        lire_politique(fichier)


def test_politique_reelle_ne_recommande_pas_fausse_couverture():
    racine = Path(__file__).resolve().parents[1]
    politique = lire_politique(racine / "institutionnel/veille/controle_v1.json")
    assert len(politique["collectes"]) >= 8
    assert len(politique["procedures"]) >= 5
    for entree_reelle in politique["collectes"]:
        assert (racine / entree_reelle["fichier"]).is_file()
    for proc in politique["procedures"]:
        assert (racine / ".github/workflows" / proc["fichier"]).is_file()
