"""Essais du balayage mensuel complet, hors réseau et sans déduction juridique."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest

from scripts.balayer_fichiers_consolides_decp import (
    VERSION, BalayageInvalide, MOIS, SOURCE, analyser, cibles,
    choisir_ressources, executer, reexaminer_archive,
)

TARGET = "25M034"
SIRET = "21060027600013"
RIDS = [
    "393f8099-0e3c-41b4-9f40-59ec3914807c",
    "740ccc19-4130-4044-af2d-ae9a60d25311",
    "f90c13f0-4123-4f62-8654-410aa723d5f7",
]


def rapport_cible(tmp_path):
    fichiers = []
    for i in range(17):
        contrats = []
        if i < 7:
            contrats = [{
                "reference_contrat_comparable_decp": True,
                "reference_contrat_declaree": TARGET if i == 0
                  else "2025CC050" + str(i),
                "reference_locale": "CON-0001",
                "origine_reference_contrat": "/ContractReference/cbc:ID",
            }]
        fichiers.append({
            "avis_boamp": f"25-{900+i}",
            "siret_chiffres_sans_schema_boamp": SIRET if i == 0 else "11000201100044",
            "contrats_locaux": contrats,
        })
    chemin = tmp_path / "chaines.json"
    chemin.write_text(json.dumps({
        "version": "chaines-documentaires-acheteurs-17-avis-v1",
        "liaisons_contractuelles_decp_prouvees": 0,
        "nombre_siret_distincts": 16,
        "mesures": {"avis": 17, "references_contrat_comparables": 7},
        "dossiers": fichiers,
    }), encoding="utf-8")
    return chemin


def fichiers_json(tmp_path):
    originaux = {}
    for i, mois in enumerate(MOIS):
        chemin = tmp_path / f"decp-{mois}.json"
        doc = {
            "marches": {"marche": [{
                "_type": "Marché",
                "id": TARGET if i == 0 else "2025CC0501",
                "acheteur": {"id": SIRET if i == 0 else
                            "11000201100044" if i == 1
                            else "99999999999999"},
                "objet": "Marché public d'analyse technique",
                "offresRecues": "NC",
                "dateNotification": "2025-08-26",
            }, {
                "id": TARGET,
                "acheteur": {"id": "88888888888888"},
                "objet": "Autre acheteur avec la même référence",
            }, {
                "id": "REFERENCE-SANS-ACHETEUR",
                "objet": "Marché non qualifiable",
            }], "contrat-concession": [{"id": "CON-1"}]}
        }
        chemin.write_text(json.dumps(doc), encoding="utf-8")
        originaux[f"decp-{mois}.json"] = chemin
    return originaux


def catalogues(originals):
    commun = [
        {"titre": nom, "id": RIDS[i],
         "taille_octets_declaree": fichier.stat().st_size,
         "modifie_le": "2026-10-13T00:00:00+00:00", "format": "json"}
        for i, (nom, fichier) in enumerate(originals.items())
    ]
    fiche = {"resources": [{
        "id": x["id"], "title": x["titre"],
        "format": x["format"], "filesize": x["taille_octets_declaree"],
        "url": "https://static.data.gouv.fr/resources/" + x["titre"],
    } for x in commun]}
    return {"catalogues": [{"source_id": SOURCE, "ressources_recentes": commun}]}, fiche


def test_sept_references_non_probantes_extraites(tmp_path):
    objectifs, preuve = cibles(rapport_cible(tmp_path))
    assert preuve["nombre_references_contractuelles"] == 7
    assert preuve["nombre_couples_candidats_distincts"] == 7
    assert (SIRET, TARGET) in objectifs
    assert objectifs[(SIRET, TARGET)][0]["avis"] == "25-900"


def test_sources_selectionnees_exactement_selon_leurs_tailles(tmp_path):
    fichiers = fichiers_json(tmp_path)
    meta, fiche = catalogues(fichiers)
    result = choisir_ressources(meta, fiche)
    assert [x["titre"] for x in result] == list(fichiers)
    fiche["resources"][0]["filesize"] += 2
    with pytest.raises(BalayageInvalide, match="divergentes"):
        choisir_ressources(meta, fiche)


def test_trois_fichiers_entiers_et_homonymies_conserves(tmp_path):
    c = rapport_cible(tmp_path)
    files = fichiers_json(tmp_path)
    meta, catalogue = catalogues(files)
    def copier(ressource, sortie):
        sortie.write_bytes(files[ressource["titre"]].read_bytes())
    resultat = executer(
        c, meta, catalogue, tmp_path / "sorties",
        recuperer=copier, instant=datetime(2026, 10, 13, tzinfo=timezone.utc)
    )
    assert resultat["version"] == VERSION
    assert resultat["nombre_fichiers_analyses"] == 3
    assert resultat["nombre_references_contractuelles"] == 7
    assert resultat["statistiques_globales_avec_repetitions_possibles"]["objets_lus"] == 12
    assert resultat["statistiques_globales_avec_repetitions_possibles"]["notices_marche_rejetees"] == 3
    assert resultat["statistiques_globales_avec_repetitions_possibles"]["concessions_exclues"] == 3
    assert resultat["candidats_decp_meme_siret"] == 2
    assert resultat["statistiques_globales_avec_repetitions_possibles"][
        "offres_recues_non_communiquees_nc"
    ] == 3
    assert resultat["statistiques_globales_avec_repetitions_possibles"][
        "notices_normalisees"
    ] == 6
    assert resultat["contrats_juridiquement_demontrés"] == 0
    assert len(resultat["sources"][0]["candidats"]) == 2
    assert resultat["sources"][0]["candidats"][0]["meme_siret_acheteur"] is True
    assert resultat["sources"][0]["candidats"][1]["meme_siret_acheteur"] is False
    assert all(x["fichier_integral_parcouru"] for x in resultat["sources"])
    assert all(x["sha256_source_brute"] ==
           hashlib.sha256(files[x["nom_fichier"]].read_bytes()).hexdigest()
           for x in resultat["sources"])
    with pytest.raises(BalayageInvalide, match="écraser"):
        executer(c, meta, catalogue, tmp_path / "sorties", recuperer=copier)


def test_telechargement_partiel_refuse_sans_rapport(tmp_path):
    c = rapport_cible(tmp_path)
    files = fichiers_json(tmp_path)
    meta, catalogue = catalogues(files)
    def tronquer(ressource, destination):
        destination.write_bytes(files[ressource["titre"]].read_bytes()[:-5])
    sortie = tmp_path / "resultats"
    with pytest.raises(BalayageInvalide, match="Taille réelle"):
        executer(c, meta, catalogue, sortie, recuperer=tronquer)
    assert not sortie.exists()


def test_rejet_profil_manquant_est_compte(tmp_path):
    files = fichiers_json(tmp_path)
    m, fiche = catalogues(files)
    select = choisir_ressources(m, fiche)[0]
    objectifs, _ = cibles(rapport_cible(tmp_path))
    resultat = analyser(files[select["titre"]], select, objectifs)
    assert resultat["mesures"]["notices_marche_lues"] == 3
    assert resultat["mesures"]["notices_marche_rejetees"] == 1
    assert resultat["mesures"]["candidats_avec_siret_acheteur_concordant"] == 1


def test_identite_cible_manquante_refusee(tmp_path):
    p = rapport_cible(tmp_path)
    d = json.loads(p.read_text())
    d["dossiers"][0]["contrats_locaux"][0]["reference_contrat_declaree"] = "!!!"
    p.write_text(json.dumps(d))
    with pytest.raises(BalayageInvalide, match="non comparable"):
        cibles(p)


def test_mois_manquant_ne_produit_aucun_resultat(tmp_path):
    files = fichiers_json(tmp_path)
    meta, fiche = catalogues(files)
    del fiche["resources"][-1]
    with pytest.raises(BalayageInvalide):
        choisir_ressources(meta, fiche)


def test_relecture_du_meme_corpus_hors_reseau(tmp_path):
    cible = rapport_cible(tmp_path)
    sources = fichiers_json(tmp_path)
    etat, fiche = catalogues(sources)
    def copier(selection, sortie):
        sortie.write_bytes(sources[selection["titre"]].read_bytes())
    original = tmp_path / "initial"
    premier = executer(
        cible, etat, fiche, original, recuperer=copier,
        instant=datetime(2026, 10, 13, tzinfo=timezone.utc),
    )
    relecture = reexaminer_archive(cible, original, tmp_path / "nouveau.json")
    assert relecture["relecture_de_sources_archivees"] is True
    assert relecture["retelechargement_officiel_effectue"] is False
    assert relecture["interpretation_nc"] == "effectif_offres_non_communique_jamais_zero"
    assert relecture["candidats_decp_meme_siret"] == premier["candidats_decp_meme_siret"]
    assert relecture["statistiques_globales_avec_repetitions_possibles"][
        "offres_recues_non_communiquees_nc"] == 3
    assert relecture["contrats_juridiquement_demontrés"] == 0
    assert all(a["sha256_source_brute"] == b["sha256_source_brute"]
               for a, b in zip(relecture["sources"], premier["sources"]))


def test_relecture_refuse_octets_modifies(tmp_path):
    cible = rapport_cible(tmp_path)
    sources = fichiers_json(tmp_path)
    etat, fiche = catalogues(sources)
    def copier(selection, sortie):
        sortie.write_bytes(sources[selection["titre"]].read_bytes())
    original = tmp_path / "initial"
    executer(cible, etat, fiche, original, recuperer=copier)
    fichier = original / "fichiers-officiels" / "decp-2025-08.json"
    fichier.write_bytes(fichier.read_bytes() + b" ")
    with pytest.raises(BalayageInvalide, match="Octets"):
        reexaminer_archive(cible, original, tmp_path / "refuse.json")
    assert not (tmp_path / "refuse.json").exists()
