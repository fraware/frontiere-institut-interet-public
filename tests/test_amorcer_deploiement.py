"""Plan reproductible d'amorçage : essais sans Docker ni connexion Internet."""
import json
import subprocess

import pytest

from scripts.amorcer_deploiement import (
    etapes, executer, main, plan, valider_repertoire,
)


def environnement(tmp_path):
    base = tmp_path
    for nom in (
        "compose.collecte.yml",
        "institutionnel/besoins_publics/manifest_offres_postes.json",
        "institutionnel/decp/sources_v1.json",
        "institutionnel/decp/sonde_aife_json.json",
        "institutionnel/decp/lot_dgfip_xml.json",
    ):
        chemin = base / nom
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text("{}", encoding="utf-8")
    for n in range(16):
        (base / "institutionnel/besoins_publics/offres_postes"
         / f"lot_{n:02x}.jsonl").parent.mkdir(parents=True, exist_ok=True)
        (base / "institutionnel/besoins_publics/offres_postes"
         / f"lot_{n:02x}.jsonl").write_bytes(b"\n")
    boamp = base / "institutionnel/besoins_publics/historique_boamp/2026/10"
    boamp.mkdir(parents=True, exist_ok=True)
    (boamp / "2026-10-01.json").write_text("{}", encoding="utf-8")
    return base


def test_simulation_restitue_six_services_sans_operation(tmp_path, capsys):
    base = environnement(tmp_path)
    resultat = plan(base)
    assert resultat["pret_a_amorcer"] is True
    assert resultat["aucune_commande_executee"] is True
    assert len(resultat["etapes"]) == 7
    commandes = [x["commande"] for x in resultat["etapes"]]
    assert commandes[0].endswith("config --quiet")
    assert "collecte-decp-consolides" in commandes[1]
    assert "app.plateforme_boamp" in commandes[2]
    assert "app.plateforme_emplois" in commandes[3]
    assert "app.collecteur_decp_continu" in commandes[4]
    assert "up --detach" in commandes[5]
    assert commandes[6].endswith("ps")
    assert main(["--repertoire", str(base)]) == 0
    affichage = json.loads(capsys.readouterr().out)
    assert affichage["mode"] == "simulation"
    assert len(affichage["etapes"]) == 7


def test_manifeste_manquant_refuse_un_amorcage_actif(tmp_path):
    base = environnement(tmp_path)
    (base / "institutionnel/decp/sources_v1.json").unlink()
    assert valider_repertoire(base)["pret_a_amorcer"] is False
    with pytest.raises(ValueError, match="Archives d'amorçage absentes"):
        executer(base, executant=lambda *a, **k: None)


def test_execution_suit_exactement_le_plan_et_s_arrete_en_cas_d_erreur(tmp_path):
    base = environnement(tmp_path)
    vus = []
    def simulation(commande, *, cwd, check):
        assert cwd == base
        assert check is True
        vus.append(commande)
        return subprocess.CompletedProcess(commande, 0)
    resultat = executer(base, executant=simulation)
    assert len(resultat) == 7
    assert [e.commande for e in etapes()] == [tuple(x) for x in vus]

    vus.clear()
    def panne(commande, *, cwd, check):
        vus.append(commande)
        if len(vus) == 3:
            raise subprocess.CalledProcessError(1, commande)
    with pytest.raises(subprocess.CalledProcessError):
        executer(base, executant=panne)
    assert len(vus) == 3
    assert all("up" not in cmd for cmd in vus)


def test_redemarrage_sans_amorcage_sur_repertoire_neuf(tmp_path):
    (tmp_path / "compose.collecte.yml").write_text("services: {}", encoding="utf-8")
    sorties = []
    def executant(commande, *, cwd, check):
        sorties.append(commande)
    assert len(executer(tmp_path, amorcer=False, executant=executant)) == 4
    assert not any("run" in commande for commande in sorties)
    assert sorties[-1][-1] == "ps"
    assert all(x["nom"] != "Importer les avis BOAMP archivés"
               for x in plan(tmp_path, amorcer=False)["etapes"])


def test_preparation_seule_ne_demarre_aucun_service(tmp_path):
    base = environnement(tmp_path)
    commandes = [x.commande for x in etapes(demarrer=False)]
    assert len(commandes) == 5
    assert not any("up" in x for x in commandes)
    executees = []
    executer(base, demarrer=False,
             executant=lambda cmd, **_kw: executees.append(cmd))
    assert len(executees) == 5
