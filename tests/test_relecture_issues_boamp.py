"""Essais hors réseau des paquets aveugles et de la double lecture BOAMP."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

import pytest

import scripts.preparer_relecture_issues_boamp as prep
from scripts.consolider_relecture_issues_boamp import (
    consolider, verifier_formulaire, JugementInvalide,
)


def fichier_source(code):
    return json.dumps({
        "total_count": 1,
        "results": [{
            "idweb": code,
            "dateparution": "2026-05-12",
            "objet": "Prestation technique sans résultat présumé",
            "nomacheteur": "Établissement public fictif",
            "nature": "APPEL_OFFRE",
            "donnees": json.dumps({"Exemple": {"sans_label": True}}),
        }],
    }, ensure_ascii=False).encode()


def fabriquer_archive(tmp_path, monkeypatch, *, corrompre=False):
    noms, original, a = [], [], tmp_path / "corpus.zip"
    with zipfile.ZipFile(a, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for nombre, dossier, n in (
                (36, "releve-issues-36/", "echantillon-independant-technique.json"),
                (24, "releve-epreuve-enrichie/", "epreuve-enrichie-infructueux.json")):
            cas, rapport = [], []
            for i in range(nombre):
                identifiant = f"{26 if nombre == 36 else 25}-{200000 + i}"
                raw = fichier_source(identifiant)
                cas.append({"avis": identifiant, "date_parution": "2026-05-12"})
                key = "sha256_reponse_http" if nombre == 36 else "sha256_reponse"
                rapport.append({
                    "avis": identifiant, "fichier_reponse": identifiant + ".json",
                    key: hashlib.sha256(raw).hexdigest(),
                })
                # Falsification intentionnelle dans un seul fichier.
                if corrompre and nombre == 24 and i == 0:
                    raw = raw.replace(b'"nature": "APPEL_OFFRE"', b'"nature": "ATTRIBUTION"')
                z.writestr(dossier + identifiant + ".json", raw)
            ids = [x["avis"] for x in cas]
            digest = hashlib.sha256(json.dumps(
                ids, ensure_ascii=False, separators=(",", ":")
            ).encode()).hexdigest()
            noms.append((n, dossier, digest, nombre))
            z.writestr(n, json.dumps({
                "cas": cas, "sha256_identifiants_ordonnes": digest,
            }))
            z.writestr(dossier + "rapport.json", json.dumps({"cas": rapport}))
    monkeypatch.setattr(prep, "CORPUS", tuple(noms))
    return a


def remplir(chemin, nom, *, chiffres=None):
    j = json.loads(chemin.read_text())
    j["identifiant_relecteur"] = nom
    j["declaration_lecture_sans_predictions"] = True
    for cas in j["jugements"]:
        cas["statut_avis"] = "SANS_RESULTAT_DANS_CET_AVIS"
        cas["preuve_statut"] = "/results/0/nature"
    if chiffres is not None:
        exemple = j["jugements"][0]
        exemple["statut_avis"] = "RESULTATS_PAR_LOT"
        exemple["lots"] = [{
            "lot": "LOT-0001", "decision": "NON_ATTRIBUE",
            "code_motif": "other", "offres_totales": chiffres,
            "offres_electroniques": None,
            "cause_non_attribution": "NON_ETABLIE", "preuve_causale": "",
            "preuve_decision": "/EFORMS/.../cbc:TenderResultCode",
            "preuve_effectifs": "/EFORMS/.../efbc:StatisticsNumeric",
        }]
    chemin.write_text(json.dumps(j, ensure_ascii=False))
    return j


def test_preparation_aveugle_et_integrite_60_sources(tmp_path, monkeypatch):
    entree = fabriquer_archive(tmp_path, monkeypatch)
    dossier = tmp_path / "pack"
    resultat = prep.preparer(entree, dossier)
    assert resultat["nombre_cas"] == 60
    assert resultat["references_independantes_etablies"] is False
    assert len(list((dossier / "sources").glob("CAS*.json"))) == 60
    paquet = json.loads((dossier / "paquet_commun.json").read_text())
    assert paquet["prequalifications_automatiques_exclues"] is True
    assert not any("statut_releve" in x or "qualification_regle_automatique" in x
                   for x in paquet["cas"])
    assert len({x["avis"] for x in paquet["cas"]}) == 60
    affectations = json.loads((dossier / "correspondances_privees.json").read_text())
    assert {x["cohorte"] for x in affectations["cohortes"]} == {
        "tirage_36", "epreuve_24"
    }
    with pytest.raises(prep.RelectureInvalide, match="existante"):
        prep.preparer(entree, dossier)


def test_corruption_octets_interrompt_le_paquet(tmp_path, monkeypatch):
    entree = fabriquer_archive(tmp_path, monkeypatch, corrompre=True)
    with pytest.raises(prep.RelectureInvalide, match="altérée"):
        prep.preparer(entree, tmp_path / "invalide")
    assert not (tmp_path / "invalide").exists()


def test_formulaire_vierge_ne_devient_pas_un_verdict(tmp_path, monkeypatch):
    entree = fabriquer_archive(tmp_path, monkeypatch)
    dossier = tmp_path / "pack"
    prep.preparer(entree, dossier)
    paquet_path = dossier / "paquet_commun.json"
    paquet = json.loads(paquet_path.read_text())
    premier = dossier / "relecteur_1" / "jugements_vierges.json"
    second = dossier / "relecteur_2" / "jugements_vierges.json"
    with pytest.raises(JugementInvalide, match="aveuglement"):
        consolider(paquet_path, premier, second, tmp_path / "rapport.json")
    remplir(premier, "lecteur-A")
    remplir(second, "lecteur-B")
    resultat = consolider(paquet_path, premier, second, tmp_path / "rapport.json")
    assert resultat["nombre_cas"] == 60
    assert resultat["compteurs_accord"]["avis_statut_accord"] == 60
    assert resultat["nombre_desaccords"] == 0
    assert resultat["reference_consensuelle_etablie"] is False
    assert resultat["independance_reelle_verifiee_par_logiciel"] is False


def test_desaccord_zero_et_un_offre_est_conserve_sans_consensus(tmp_path, monkeypatch):
    entree = fabriquer_archive(tmp_path, monkeypatch)
    dossier = tmp_path / "pack"
    prep.preparer(entree, dossier)
    premier = dossier / "relecteur_1" / "jugements_vierges.json"
    second = dossier / "relecteur_2" / "jugements_vierges.json"
    remplir(premier, "lecteur-A", chiffres=0)
    remplir(second, "lecteur-B", chiffres=1)
    resultat = consolider(dossier / "paquet_commun.json", premier, second,
                         tmp_path / "rapport.json")
    assert resultat["nombre_desaccords"] == 1
    assert resultat["desaccords"][0]["dimension"] == "offres_totales"
    assert resultat["desaccords"][0]["lecteur_1"] == 0
    assert resultat["desaccords"][0]["lecteur_2"] == 1
    assert resultat["compteurs_accord"]["lots_communs"] == 1
    assert resultat["reference_consensuelle_etablie"] is False


def test_double_lecture_interdit_lecteur_identique(tmp_path, monkeypatch):
    entree = fabriquer_archive(tmp_path, monkeypatch)
    dossier = tmp_path / "pack"
    prep.preparer(entree, dossier)
    premier = dossier / "relecteur_1" / "jugements_vierges.json"
    second = dossier / "relecteur_2" / "jugements_vierges.json"
    remplir(premier, "meme-lecteur")
    remplir(second, "meme-lecteur")
    with pytest.raises(JugementInvalide, match="même lecteur"):
        consolider(dossier / "paquet_commun.json", premier, second,
                   tmp_path / "rapport.json")


def test_une_deduction_sans_preuve_est_refusee(tmp_path, monkeypatch):
    entree = fabriquer_archive(tmp_path, monkeypatch)
    dossier = tmp_path / "pack"
    prep.preparer(entree, dossier)
    premier = dossier / "relecteur_1" / "jugements_vierges.json"
    formulaire = remplir(premier, "lecteur-A", chiffres=0)
    formulaire["jugements"][0]["lots"][0]["preuve_effectifs"] = ""
    premier.write_text(json.dumps(formulaire))
    paquet = json.loads((dossier / "paquet_commun.json").read_text())
    with pytest.raises(JugementInvalide, match="sans passage source"):
        verifier_formulaire(paquet, premier,
            prep.sha((dossier / "paquet_commun.json").read_bytes()))


def test_cause_documentee_exige_piece_specifique(tmp_path, monkeypatch):
    entree = fabriquer_archive(tmp_path, monkeypatch)
    dossier = tmp_path / "pack"
    prep.preparer(entree, dossier)
    premier = dossier / "relecteur_1" / "jugements_vierges.json"
    formulaire = remplir(premier, "lecteur-A")
    formulaire["jugements"][0]["lots"][0]["cause_non_attribution"] = "DOCUMENTEE"
    premier.write_text(json.dumps(formulaire))
    paquet = json.loads((dossier / "paquet_commun.json").read_text())
    with pytest.raises(JugementInvalide, match="sans preuve distincte"):
        verifier_formulaire(paquet, premier,
            prep.sha((dossier / "paquet_commun.json").read_bytes()))
