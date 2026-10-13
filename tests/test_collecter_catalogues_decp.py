"""Contrôles hors réseau des deux inventaires officiels de données de marchés."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.collecter_catalogues_decp import (
    ErreurDECP, executer, reduire_fiche, verifier_catalogue,
)


def catalogue():
    return json.loads(Path("institutionnel/decp/sources_v1.json").read_text(encoding="utf-8"))


def fiche(source, n=5):
    return {
        "id": source["id"] + "-jeu-id",
        "title": "Données essentielles de marchés",
        "license": "fr-lo",
        "last_update": "2026-10-12T12:00:00Z",
        "resources": [
            {"id": f"resource-{i}", "title": f"decp-2026-{i}.json",
             "format": "json", "filesize": 123456 + i,
             "last_modified": f"2026-09-{i+1:02d}T12:00:00Z"}
            for i in range(n)
        ],
    }


def test_source_fermee_et_deux_jeux_distincts():
    sources = verifier_catalogue(catalogue())
    assert len(sources) == 2
    assert all(x["url"].startswith("https://www.data.gouv.fr/api/1/datasets/") for x in sources)
    faux = deepcopy(catalogue())
    faux["sources"][0]["url"] = "https://attacker.invalid/requete"
    with pytest.raises(ErreurDECP):
        verifier_catalogue(faux)


def test_index_limite_et_empreinte_couvre_toutes_les_ressources():
    source = dict(catalogue()["sources"][0], limite_ressources_indexees=2)
    resultat = reduire_fiche(source, fiche(source, 5))
    assert resultat["nombre_ressources_total"] == 5
    assert resultat["nombre_ressources_indexees"] == 2
    assert resultat["nombre_ressources_non_detaillees"] == 3
    assert resultat["ressources_recentes"][0]["id"] == "resource-4"
    assert resultat["completude_des_marches_etablie"] is False
    modifie = fiche(source, 5)
    modifie["resources"][0]["filesize"] += 1
    assert reduire_fiche(source, modifie)["empreinte_inventaire_complet"] != resultat["empreinte_inventaire_complet"]


def test_resultat_invariant_a_ordre_du_catalogue():
    source = catalogue()["sources"][0]
    first = fiche(source)
    reverse = deepcopy(first)
    reverse["resources"].reverse()
    assert (reduire_fiche(source, first)["empreinte_inventaire_complet"] ==
            reduire_fiche(source, reverse)["empreinte_inventaire_complet"])


def test_echec_partiel_preserve_source_precedente():
    sources = catalogue()["sources"]
    premier = executer(catalogue(), {}, recuperer=lambda src: fiche(src),
                       instant="2026-10-12T12:00:00+00:00")
    original = next(x for x in premier["catalogues"] if x["source_id"] == sources[0]["id"])
    def panne(source):
        if source["id"] == sources[0]["id"]:
            raise TimeoutError("simulateur")
        return fiche(source, 6)
    suivant = executer(catalogue(), premier, recuperer=panne,
                       instant="2026-10-12T18:00:00+00:00")
    assert suivant["sources_reussies"] == 1
    assert suivant["sources_echouees"][0]["motif"] == "TimeoutError"
    conserve = next(x for x in suivant["catalogues"] if x["source_id"] == sources[0]["id"])
    assert conserve == original
    assert suivant["nombre_catalogues_avec_modifications"] == 1


def test_aucune_reussite_refuse_remplacement():
    with pytest.raises(ErreurDECP):
        executer(catalogue(), {}, recuperer=lambda _: (_ for _ in ()).throw(TimeoutError()))


def test_ressources_doublonnees_refusees():
    source = catalogue()["sources"][0]
    doc = fiche(source)
    doc["resources"].append(deepcopy(doc["resources"][0]))
    with pytest.raises(ErreurDECP):
        reduire_fiche(source, doc)


def test_pas_d_inference_de_besoins_actuels():
    resultat = executer(catalogue(), {}, recuperer=lambda x: fiche(x),
                        instant="2026-10-12T12:00:00+00:00")
    assert resultat["qualifie_des_besoins_actuels"] is False
    assert resultat["inventaires_complets_telecharges"] == 0
    assert all(x["nouveaux_besoins_prospectifs_deduits"] == 0 for x in resultat["catalogues"])
