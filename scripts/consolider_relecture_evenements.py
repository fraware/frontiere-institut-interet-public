"""Valider et comparer deux lectures historiques indépendantes sans effacer les désaccords."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

DIMENSIONS = ("piece_retrouvee", "fait_etaye", "date_etayee", "precision_respectee")
VALEURS = {"OUI", "NON", "INDETERMINE"}


def sha256(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


def indexer(lignes: list[dict], description: str) -> dict:
    if not isinstance(lignes, list):
        raise ValueError(f"{description} : liste attendue.")
    indices = {}
    for item in lignes:
        if not isinstance(item, dict):
            raise ValueError(f"{description} : objet attendu.")
        identifiant = item.get("identifiant_evenement")
        if not isinstance(identifiant, str) or not identifiant:
            raise ValueError(f"{description} : identifiant invalide.")
        if identifiant in indices:
            raise ValueError(f"{description} : identifiant répété : {identifiant}.")
        indices[identifiant] = item
    return indices


def consolider(paquet: dict, jeux: list[dict], empreinte_paquet: str) -> dict:
    if paquet.get("version_schema") != "paquet-relecture-evenements-v1":
        raise ValueError("Version du paquet inconnue.")
    fiches = indexer(paquet.get("fiches"), "paquet")
    if type(paquet.get("nombre_evenements")) is not int or paquet["nombre_evenements"] != len(fiches):
        raise ValueError("Nombre de faits annoncé incohérent.")
    if len(jeux) != 2:
        raise ValueError("Deux jeux de jugements sont requis.")
    auteurs, indices = [], []
    for jeu in jeux:
        if jeu.get("version_schema") != "jugements-evenements-v1":
            raise ValueError("Version de jugements incorrecte.")
        if jeu.get("empreinte_sha256_paquet") != empreinte_paquet:
            raise ValueError("Les jugements ne portent pas sur le même paquet.")
        code = jeu.get("relecteur_code")
        if not isinstance(code, str) or not code.strip() or code == "A_RENSEIGNER":
            raise ValueError("Identifiant du relecteur non renseigné.")
        auteurs.append(code)
        notes = indexer(jeu.get("jugements"), f"jugements de {code}")
        if set(notes) != set(fiches):
            raise ValueError(f"Cas manquants ou supplémentaires pour {code}.")
        for identifiant, note in notes.items():
            if not isinstance(note.get("justification"), str) or not note["justification"].strip():
                raise ValueError(f"Justification manquante : {code}/{identifiant}.")
            if not isinstance(note.get("passage_effectivement_consulte"), str):
                raise ValueError(f"Passage contrôlé invalide : {code}/{identifiant}.")
            for dimension in DIMENSIONS:
                if note.get(dimension) not in VALEURS:
                    raise ValueError(f"Jugement absent ou invalide : {code}/{identifiant}/{dimension}.")
            if note["piece_retrouvee"] == "OUI" and not note["passage_effectivement_consulte"].strip():
                raise ValueError(f"Pièce déclarée retrouvée sans repère contrôlable : {code}/{identifiant}.")
        indices.append(notes)
    if auteurs[0] == auteurs[1]:
        raise ValueError("Les deux relecteurs doivent être distincts.")
    divergences = []
    accords = Counter()
    effectifs = Counter()
    repartition = {auteur: {dimension: Counter() for dimension in DIMENSIONS} for auteur in auteurs}
    for identifiant in sorted(fiches):
        a, b = indices[0][identifiant], indices[1][identifiant]
        for dimension in DIMENSIONS:
            v1, v2 = a[dimension], b[dimension]
            repartition[auteurs[0]][dimension][v1] += 1
            repartition[auteurs[1]][dimension][v2] += 1
            effectifs[dimension] += 1
            if v1 == v2:
                accords[dimension] += 1
            else:
                divergences.append({
                    "identifiant_evenement": identifiant, "dimension": dimension,
                    "avis_relecteur_1": v1, "avis_relecteur_2": v2,
                })
    return {
        "version_schema": "bilan-relecture-evenements-v1",
        "empreinte_sha256_paquet": empreinte_paquet,
        "relecteurs": auteurs,
        "nombre_evenements": len(fiches),
        "nombre_desaccords": len(divergences),
        "desaccords": divergences,
        "accords_par_dimension": {x: {"accords": accords[x], "comparaisons": effectifs[x]} for x in DIMENSIONS},
        "repartition_par_relecteur": {
            auteur: {dim: dict(compte) for dim, compte in dimensions.items()}
            for auteur, dimensions in repartition.items()
        },
        "consensus_automatique": False,
        "limites": [
            "Une concordance entre deux avis n'établit pas à elle seule la vérité historique.",
            "Les désaccords restent intacts et exigent, le cas échéant, une adjudication distincte.",
            "L'identité et l'indépendance réelles des relecteurs doivent être attestées hors du logiciel.",
        ],
    }


def principal() -> None:
    p = argparse.ArgumentParser(description="Consolider deux jugements historiques indépendants.")
    p.add_argument("--paquet", type=Path, required=True)
    p.add_argument("--jugements", type=Path, nargs=2, required=True)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args()
    depot = Path(__file__).resolve().parents[1]
    if a.sortie.resolve().is_relative_to(depot):
        raise SystemExit("Le bilan des relecteurs doit être enregistré hors du dépôt public.")
    try:
        paquet = json.loads(a.paquet.read_text(encoding="utf-8"))
        jeux = [json.loads(path.read_text(encoding="utf-8")) for path in a.jugements]
        resultat = consolider(paquet, jeux, sha256(a.paquet))
        resultat["empreintes_sha256_jugements"] = [sha256(path) for path in a.jugements]
    except (ValueError, TypeError, KeyError, OSError) as e:
        raise SystemExit(f"Consolidation refusée : {e}") from e
    a.sortie.parent.mkdir(parents=True, exist_ok=True)
    try:
        with a.sortie.open("x", encoding="utf-8") as f:
            json.dump(resultat, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except FileExistsError as e:
        raise SystemExit("Un bilan existe déjà : aucune réécriture automatique.") from e
    print(f"Deux relectures consolidées, {resultat['nombre_desaccords']} désaccords conservés.")


if __name__ == "__main__":
    principal()
