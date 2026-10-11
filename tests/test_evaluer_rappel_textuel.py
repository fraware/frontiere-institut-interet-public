"""Vérifier le recensement lexical indépendant du plafond de restitution."""
import json
from scripts.rechercher_capacites_institutionnelles import (
    construire_index, ouvrir_index, chercher,
)
from scripts.croiser_pistes_capacites import chercher_expressions_exactes
from scripts.evaluer_rappel_textuel import reference_exacte, ids_verifies


def test_reference_exhaustive_et_rappel_exact(tmp_path):
    racine = tmp_path / "entites"
    racine.mkdir()
    lignes = []
    for n in range(65):
        lignes.append({
            "id": f"FRONTIERE-INST-LEURRE-{n:03d}",
            "nom_officiel": f"Service administratif {n}",
            "etat": "ACTIF", "famille": "recherche_publique",
            "missions": [{
                "nature": "PUBLIEE", "source_id": "fictive",
                "texte": "Développe une intelligence stratégique indépendante.",
            }],
            "provenance": [{"source_id": "fictive"}],
        })
    lignes.append({
        "id": "FRONTIERE-INST-EXACT", "nom_officiel": "Équipe scientifique",
        "etat": "ACTIF", "famille": "recherche_publique",
        "missions": [{
            "nature": "PUBLIEE", "source_id": "fictive",
            "texte": "Étude des systèmes d'intelligence artificielle.",
        }],
        "provenance": [{"source_id": "fictive"}],
    })
    (racine / "organismes.jsonl").write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lignes),
        encoding="utf-8",
    )
    chemin = tmp_path / "recherche.sqlite3"
    construire_index(racine, chemin)
    with ouvrir_index(chemin) as db:
        reference, digest = reference_exacte(db, "intelligence artificielle")
        exact = chercher_expressions_exactes(db, "intelligence artificielle")
        nouveau = ids_verifies(db, exact["candidats"], "intelligence artificielle")
        ancien = chercher(db, "intelligence artificielle", limite=25)
        anciens = ids_verifies(
            db,
            ancien["correspondances_aux_missions_ou_capacites_publiees"],
            "intelligence artificielle",
        )
    assert reference == {"FRONTIERE-INST-EXACT"}
    assert nouveau == reference
    assert anciens <= reference
    assert len(digest) == 64
