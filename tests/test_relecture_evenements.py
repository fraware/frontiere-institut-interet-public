"""Tester la préparation et la consolidation des relectures sans résultat réel."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.preparer_relecture_evenements import preparer
from scripts.consolider_relecture_evenements import consolider

ROOT = Path(__file__).resolve().parents[1]


def preparer_dossiers(tmp_path):
    dossier = tmp_path / "revue_001"
    manifest = preparer(
        ROOT / "donnees" / "registre_verification_evenements_v7.json",
        ROOT / "donnees" / "passages_sources_evenements_v6.json",
        dossier,
    )
    return dossier, manifest


def avis_essai(dossier, n, diverger=False):
    path = dossier / f"relecteur_{n}" / "jugements_vierges.json"
    avis = json.loads(path.read_text(encoding="utf-8"))
    avis["relecteur_code"] = f"expert-{n}"
    for i, ligne in enumerate(avis["jugements"]):
        ligne["piece_retrouvee"] = "OUI"
        ligne["fait_etaye"] = "NON" if diverger and i == 0 else "INDETERMINE"
        ligne["date_etayee"] = "INDETERMINE"
        ligne["precision_respectee"] = "INDETERMINE"
        ligne["passage_effectivement_consulte"] = "Emplacement d'essai, sans vérification réelle."
        ligne["justification"] = "Jugement artificiel exclusivement destiné au contrôle logiciel."
    return avis


def test_deux_dossiers_identiques_sans_jugement_fabrique(tmp_path):
    dossier, manifest = preparer_dossiers(tmp_path)
    assert manifest["nombre_evenements"] == 45
    assert manifest["avis_independants_disponibles"] is False
    paquet1 = (dossier / "relecteur_1" / "paquet.json").read_bytes()
    paquet2 = (dossier / "relecteur_2" / "paquet.json").read_bytes()
    assert paquet1 == paquet2
    assert hashlib.sha256(paquet1).hexdigest() == manifest["empreinte_sha256_paquet"]
    assert len(json.loads(paquet1)["fiches"]) == 45
    for n in (1, 2):
        form = json.loads((dossier / f"relecteur_{n}" / "jugements_vierges.json").read_text(encoding="utf-8"))
        assert form["relecteur_code"] == "A_RENSEIGNER"
        assert all(x["fait_etaye"] == "A_VERIFIER" and not x["justification"] for x in form["jugements"])


def test_deux_relectures_artificielles_et_desaccord_conserve(tmp_path):
    dossier, manifest = preparer_dossiers(tmp_path)
    paquet = json.loads((dossier / "paquet_commun.json").read_text(encoding="utf-8"))
    a = avis_essai(dossier, 1)
    b = avis_essai(dossier, 2, diverger=True)
    bilan = consolider(paquet, [a, b], manifest["empreinte_sha256_paquet"])
    assert bilan["nombre_evenements"] == 45
    assert bilan["nombre_desaccords"] == 1
    assert bilan["desaccords"][0]["dimension"] == "fait_etaye"
    assert bilan["consensus_automatique"] is False
    assert bilan["accords_par_dimension"]["fait_etaye"]["accords"] == 44


def test_refuse_jugements_incomplets_ou_relecteur_duplique(tmp_path):
    dossier, manifest = preparer_dossiers(tmp_path)
    paquet = json.loads((dossier / "paquet_commun.json").read_text(encoding="utf-8"))
    a = avis_essai(dossier, 1)
    b = avis_essai(dossier, 2)
    b["relecteur_code"] = a["relecteur_code"]
    with pytest.raises(ValueError, match="distinct"):
        consolider(paquet, [a, b], manifest["empreinte_sha256_paquet"])
    b["relecteur_code"] = "autre"
    b["jugements"][0]["fait_etaye"] = "A_VERIFIER"
    with pytest.raises(ValueError, match="invalide"):
        consolider(paquet, [a, b], manifest["empreinte_sha256_paquet"])


def test_refuse_alteration_du_paquet_et_ecrasement(tmp_path):
    dossier, manifest = preparer_dossiers(tmp_path)
    paquet = json.loads((dossier / "paquet_commun.json").read_text(encoding="utf-8"))
    a = avis_essai(dossier, 1)
    b = avis_essai(dossier, 2)
    b["empreinte_sha256_paquet"] = "0" * 64
    with pytest.raises(ValueError, match="même paquet"):
        consolider(paquet, [a, b], manifest["empreinte_sha256_paquet"])
    with pytest.raises(FileExistsError):
        preparer(
            ROOT / "donnees" / "registre_verification_evenements_v7.json",
            ROOT / "donnees" / "passages_sources_evenements_v6.json",
            dossier,
        )


def test_refuse_dossier_dans_le_depot(tmp_path):
    with pytest.raises(ValueError, match="hors du dépôt"):
        preparer(
            ROOT / "donnees" / "registre_verification_evenements_v7.json",
            ROOT / "donnees" / "passages_sources_evenements_v6.json",
            ROOT / "evaluation" / "dossier_interdit",
        )
