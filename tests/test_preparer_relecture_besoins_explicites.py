"""Contrôles de filiation et d'interprétation de l'échantillon CSP.

Les exemples sont synthétiques et ne représentent aucune demande française.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.preparer_relecture_besoins_explicites import (
    EchecPreuve, PARTITIONS, candidat, preparer, rang,
)


def offre(numero: int, technique: bool) -> dict:
    return {
        "reference": f"OFFRE-{numero:04d}",
        "cle_enregistrement": hashlib.sha256(f"ligne-{numero}".encode()).hexdigest(),
        "intitule": ("Ingénieur informatique " if technique else "Agent administratif ")
                    + str(numero),
        "organisme": "Service public fictif",
        "metier": "Recherche" if technique else "Accueil",
        "specialisation": "Calcul intensif" if technique else "",
        "competences_attendues": "Maîtrise des outils documentés",
        "publication_debut": "2026-10-01",
        "premiere_publication": "2026-09-20",
        "publication_fin": "2026-11-01",
        "champs_tronques": [],
    }


def ecrire_dossier(racine: Path, donnees: list[dict]) -> None:
    dossier = racine / "institutionnel/besoins_publics"
    chemins = dossier / "offres_postes"
    chemins.mkdir(parents=True)
    liste = {nom: [] for nom in PARTITIONS}
    for n, offre_individuelle in enumerate(donnees):
        liste[PARTITIONS[n % 16]].append(offre_individuelle)
    empreintes = {}
    for nom, lignes in liste.items():
        brut = b"".join((json.dumps(o, sort_keys=True, ensure_ascii=False) + "\n")
                         .encode() for o in lignes)
        (chemins / nom).write_bytes(brut)
        empreintes[nom] = hashlib.sha256(brut).hexdigest()
    manifeste = {
        "version": "emplois-publics-extraits-v1",
        "offres_distinctes": len(donnees),
        "sha256_csv": "b" * 64,
        "empreintes_partitions": empreintes,
        "source_modifie_le": "2026-10-12T06:01:04Z",
    }
    (dossier / "manifest_offres_postes.json").write_text(
        json.dumps(manifeste, sort_keys=True), encoding="utf-8")


def test_prelever_des_extraits_integraux_sans_statut_actuel():
    o = offre(1, True)
    b = (json.dumps(o, ensure_ascii=False) + "\n").encode()
    observation = candidat(o, "institutionnel/besoins_publics/offres_postes/lot_00.jsonl", 42, b)
    assert observation["titre_cite_integralement"] == o["intitule"]
    assert observation["entite_declarante"] == o["organisme"]
    assert observation["champ_entite_declarante"] == "organisme"
    assert observation["competences_attendues_citees_integralement"] == (
        o["competences_attendues"])
    assert observation["preuve"]["ligne"] == 42
    assert observation["preuve"]["sha256_ligne_jsonl"] == hashlib.sha256(b).hexdigest()
    assert observation["champ_date_publication"] == "publication_debut"
    assert observation["etat_actuel"] == "indetermine"
    assert observation["revue_humaine"] == "non_effectuee"
    assert observation["selection_lexicale_scientifique_technique"] is True


def test_l_employeur_est_un_champ_de_source_et_non_un_organisme_invente():
    o = offre(4, True)
    o["organisme"] = None
    o["employeur"] = "Établissement public fictif"
    r = candidat(o, "f.jsonl", 1, b"test")
    assert r["entite_declarante"] == "Établissement public fictif"
    assert r["champ_entite_declarante"] == "employeur"
    assert "employeur" in r["preuve"]["champs"]
    o["champs_tronques"] = ["employeur"]
    assert candidat(o, "f.jsonl", 1, b"test") is None

def test_ne_pas_recopier_un_champ_tronque_ni_du_contenu_de_contact():
    o = offre(3, True)
    o["competences_attendues"] = "Contact : personne@example.fr"
    assert candidat(o, "f.jsonl", 1, b"test")[
        "competences_attendues_citees_integralement"] is None
    o["competences_attendues"] = "Appeler le 06 12 34 56 78"
    assert candidat(o, "f.jsonl", 1, b"test")[
        "competences_attendues_citees_integralement"] is None
    o["competences_attendues"] = "a" * 500
    assert candidat(o, "f.jsonl", 1, b"test")[
        "competences_attendues_citees_integralement"] is None
    o["competences_attendues"] = "Données"
    o["champs_tronques"] = ["competences_attendues"]
    assert candidat(o, "f.jsonl", 1, b"test")[
        "competences_attendues_citees_integralement"] is None
    o["champs_tronques"] = ["intitule"]
    assert candidat(o, "f.jsonl", 1, b"test") is None
    o["champs_tronques"] = []
    o["intitule"] = "Personne prénom.nom@example.fr"
    assert candidat(o, "f.jsonl", 1, b"test") is None


def test_verifier_16_lots_et_produire_deux_strates_disjointes(tmp_path: Path):
    donnees = [offre(i, i % 2 == 0) for i in range(48)]
    ecrire_dossier(tmp_path, donnees)
    r = preparer(tmp_path, par_strate=3)
    assert r["partitions_verifiees"] == 16
    assert r["variantes_lues"] == 48
    assert r["variantes_admissibles"] == 48
    assert r["variantes_admissibles_lexicales"] == 24
    assert r["nombre_candidats"] == 6
    assert len({x["reference"] for x in r["candidats"]}) == 6
    assert [x["strate"] for x in r["candidats"]] == (
        ["generale"] * 3 + ["lexicale_scientifique_technique"] * 3)
    assert all(x["selection_lexicale_scientifique_technique"]
               for x in r["candidats"][3:])
    assert r["relecture_humaine_effectuee"] is False
    assert r["representativite_statistique_etablie"] is False
    assert r["besoins_actuellement_non_satisfaits_demonstres"] == 0
    assert r == preparer(tmp_path, par_strate=3)
    assert r["candidats"][0]["reference"] == min(
        (o["reference"] for o in donnees),
        key=lambda v: rang(v, "general"))


def test_un_octet_change_refuse_l_integration(tmp_path: Path):
    ecrire_dossier(tmp_path, [offre(i, i % 2 == 0) for i in range(48)])
    fichier = tmp_path / "institutionnel/besoins_publics/offres_postes/lot_00.jsonl"
    brut = fichier.read_bytes()
    assert b"Service public fictif" in brut
    fichier.write_bytes(brut.replace(b"Service public fictif",
                                    b"Service public fIctif", 1))
    with pytest.raises(EchecPreuve, match="Empreinte incohérente"):
        preparer(tmp_path, par_strate=2)


def test_refuser_un_compteur_ou_un_identifiant_de_source_incompatible(tmp_path: Path):
    ecrire_dossier(tmp_path, [offre(i, i % 2 == 0) for i in range(48)])
    manifeste = tmp_path / "institutionnel/besoins_publics/manifest_offres_postes.json"
    donnees = json.loads(manifeste.read_text())
    donnees["offres_distinctes"] += 1
    manifeste.write_text(json.dumps(donnees))
    with pytest.raises(EchecPreuve, match="Nombre de variantes"):
        preparer(tmp_path, par_strate=2)
    donnees["offres_distinctes"] -= 1
    donnees["empreintes_partitions"].pop(PARTITIONS[-1])
    manifeste.write_text(json.dumps(donnees))
    with pytest.raises(EchecPreuve, match="Manifeste"):
        preparer(tmp_path, par_strate=2)


def test_ne_pas_faire_passer_une_date_impossible_pour_un_besoin_actuel():
    o = offre(2, True)
    o["publication_debut"] = "2026-02-30"
    o["premiere_publication"] = "2026-02-30"
    assert candidat(o, "f.jsonl", 1, b"test") is None
    o["premiere_publication"] = "2025-10-02"
    cas = candidat(o, "f.jsonl", 1, b"test")
    assert cas["champ_date_publication"] == "premiere_publication"
    assert cas["date_publication"] == "2025-10-02"
    o["publication_debut"] = "02/10/2025"
    cas = candidat(o, "f.jsonl", 1, b"test")
    assert cas["champ_date_publication"] == "publication_debut"
    assert cas["date_publication"] == "2025-10-02"
    o["publication_debut"] = "31/02/2025"
    o["premiere_publication"] = "2025-02-30"
    assert candidat(o, "f.jsonl", 1, b"test") is None


def test_variantes_meme_reference_ne_se_transforment_pas_en_plusieurs_besoins(tmp_path):
    donnees = [offre(i, i % 2 == 0) for i in range(48)]
    duplicata = deepcopy(donnees[0])
    duplicata["cle_enregistrement"] = "f" * 64
    duplicata["intitule"] = "Agent administratif variante"
    donnees.append(duplicata)
    ecrire_dossier(tmp_path, donnees)
    r = preparer(tmp_path, par_strate=3)
    assert r["variantes_lues"] == 49
    assert len({x["reference"] for x in r["candidats"]}) == 6
