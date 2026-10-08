"""Contrôler deux relectures indépendantes et révéler les méthodes après dépôt.

Le programme ne note jamais automatiquement la qualité d'une preuve.
Il conserve les jugements distincts et localise les désaccords.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

REGLES = {
    "ressources": {
        "existence": {"CONFIRMEE", "NON_CONFIRMEE", "INDETERMINEE"},
        "pertinence": {"FORTE", "PARTIELLE", "INSUFFISANTE", "INDETERMINEE"},
        "mobilisabilite": {"CONFIRMEE", "NON_CONFIRMEE", "INDETERMINEE"},
    },
    "sources": {
        "fiabilite": {"PRIMAIRE", "SECONDAIRE", "INSUFFISANTE", "INDETERMINEE"},
        "appui": {"DIRECT", "PARTIEL", "AUCUN", "INDETERMINE"},
    },
}


def empreinte(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def indexer(lignes: list[dict], description: str) -> dict[str, dict]:
    if not isinstance(lignes, list):
        raise ValueError(f"{description} : une liste est attendue")
    indices = {}
    for entree in lignes:
        if not isinstance(entree, dict) or not isinstance(entree.get("id"), str):
            raise ValueError(f"{description} : identifiant invalide")
        identifiant = entree["id"]
        if identifiant in indices:
            raise ValueError(f"{description} : identifiant dupliqué")
        indices[identifiant] = entree
    return indices


def valider(paquet: dict, correspondances: dict, relectures: list[dict], hash_paquet: str) -> dict:
    if paquet.get("version_schema") != "relecture-aveugle-v1":
        raise ValueError("Version du paquet incorrecte.")
    if correspondances.get("version_schema") != "correspondances-relecture-v1":
        raise ValueError("Version des correspondances incorrecte.")
    if correspondances.get("empreinte_sha256_paquet") != hash_paquet:
        raise ValueError("Correspondances associées à un autre paquet.")
    if len(relectures) != 2:
        raise ValueError("Deux relectures indépendantes sont exigées.")
    auteurs = [r.get("relecteur_code") for r in relectures]
    if any(not isinstance(x, str) or not x.strip() or x == "a-renseigner" for x in auteurs):
        raise ValueError("Chaque relecteur doit avoir un identifiant renseigné.")
    if len(set(auteurs)) != 2:
        raise ValueError("Les deux relectures doivent provenir de deux relecteurs distincts.")
    for revue in relectures:
        if revue.get("version_schema") != "jugements-relecture-v1":
            raise ValueError("Version de jugement incorrecte.")
        if revue.get("empreinte_sha256_paquet") != hash_paquet:
            raise ValueError("Jugements associés à un autre paquet.")

    cas_paquet = {c["code"]: c for c in paquet["cas"]}
    cas_prives = {c["code"]: c for c in correspondances["correspondances"]}
    if len(cas_paquet) != len(paquet["cas"]) or len(cas_prives) != len(correspondances["correspondances"]):
        raise ValueError("Codes de cas répétés.")
    if set(cas_paquet) != set(cas_prives):
        raise ValueError("Cas des correspondances et du paquet différents.")
    cas_jugements = []
    for revue in relectures:
        index = {c["code"]: c for c in revue["cas"]}
        if len(index) != len(revue["cas"]) or set(index) != set(cas_paquet):
            raise ValueError("Cas incomplets ou dupliqués dans une relecture.")
        cas_jugements.append(index)

    resultats = {nom: {"ressources": defaultdict(Counter), "sources": defaultdict(Counter)}
                 for nom in ("analyste", "assistant_generaliste", "frontiere")}
    desaccords = []
    for code in sorted(cas_paquet):
        propositions = indexer(cas_paquet[code]["propositions"], f"{code} : paquet")
        identites = indexer(cas_prives[code]["propositions"], f"{code} : correspondances")
        if set(propositions) != set(identites) or len(propositions) != 3:
            raise ValueError(f"{code} : affectations incomplètes.")
        if {i["methode"] for i in identites.values()} != set(resultats):
            raise ValueError(f"{code} : une méthode absente ou dupliquée.")
        jugements = [indexer(index[code]["propositions"], f"{code} : jugements") for index in cas_jugements]
        if any(set(x) != set(propositions) for x in jugements):
            raise ValueError(f"{code} : propositions manquantes.")
        for identifiant, proposition in propositions.items():
            methode = identites[identifiant]["methode"]
            for famille, dimensions in REGLES.items():
                objets = indexer(proposition[famille], f"{code}/{identifiant}/{famille}")
                notes = [indexer(j[identifiant][famille], f"{code}/{identifiant}/{famille}/relecture")
                         for j in jugements]
                if any(set(n) != set(objets) for n in notes):
                    raise ValueError(f"{code}/{identifiant} : objets de relecture manquants.")
                for identifiant_objet in objets:
                    for revue_idx, releves in enumerate(notes):
                        note = releves[identifiant_objet]
                        if not isinstance(note.get("motif"), str) or not note["motif"].strip():
                            raise ValueError(f"{code}/{identifiant}/{identifiant_objet} : justification manquante.")
                        for dimension, valeurs in dimensions.items():
                            valeur = note.get(dimension)
                            if valeur not in valeurs:
                                raise ValueError(f"{code}/{identifiant}/{identifiant_objet} : {dimension} non évalué.")
                            resultats[methode][famille][f"{dimension}_relecteur_{revue_idx+1}"][valeur] += 1
                    for dimension in dimensions:
                        premiere = notes[0][identifiant_objet][dimension]
                        seconde = notes[1][identifiant_objet][dimension]
                        if premiere != seconde:
                            desaccords.append({
                                "cas": code, "proposition": identifiant,
                                "methode": methode, "objet": famille,
                                "identifiant_objet": identifiant_objet, "dimension": dimension,
                                "relecteur_1": premiere, "relecteur_2": seconde,
                            })
    methodes = []
    for methode, familles in resultats.items():
        methodes.append({
            "methode": methode,
            "jugements": {
                famille: {dimension: dict(comptes) for dimension, comptes in compteurs.items()}
                for famille, compteurs in familles.items()
            },
        })
    return {
        "version_schema": "bilan-relecture-qualite-v1",
        "empreinte_sha256_paquet": hash_paquet,
        "relecteurs": auteurs,
        "methodes": methodes,
        "nombre_desaccords": len(desaccords),
        "desaccords": desaccords,
        "limites": [
            "Aucun verdict automatique de pertinence, de fiabilité ou de mobilisation.",
            "Les deux jugements sont conservés sans effacer les désaccords.",
            "L'anonymisation par cas réduit certains biais sans garantir l'aveuglement.",
            "Un résultat indéterminé reste distinct d'une réponse négative.",
        ],
    }


def principal() -> None:
    parser = argparse.ArgumentParser(description="Consolider deux relectures sur un paquet identique.")
    parser.add_argument("--paquet", type=Path, required=True)
    parser.add_argument("--correspondances-privees", type=Path, required=True)
    parser.add_argument("--jugements", type=Path, nargs=2, required=True)
    parser.add_argument("--sortie", type=Path, required=True)
    args = parser.parse_args()
    depot = Path(__file__).resolve().parents[1]
    if args.sortie.resolve().is_relative_to(depot):
        raise SystemExit("Le bilan identifié doit rester hors du dépôt public.")
    try:
        paquet = json.loads(args.paquet.read_text(encoding="utf-8"))
        correspondances = json.loads(args.correspondances_privees.read_text(encoding="utf-8"))
        relectures = [json.loads(path.read_text(encoding="utf-8")) for path in args.jugements]
        resultat = valider(paquet, correspondances, relectures, empreinte(args.paquet))
        resultat["empreintes_sha256_jugements"] = [empreinte(p) for p in args.jugements]
        resultat["empreinte_sha256_correspondances"] = empreinte(args.correspondances_privees)
    except (ValueError, TypeError, KeyError, OSError) as erreur:
        raise SystemExit(f"Relectures invalides : {erreur}") from erreur
    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.sortie.open("x", encoding="utf-8") as fichier:
            json.dump(resultat, fichier, ensure_ascii=False, indent=2)
            fichier.write("\n")
    except FileExistsError as erreur:
        raise SystemExit("Le bilan existe déjà ; aucune réécriture automatique.") from erreur


if __name__ == "__main__":
    principal()
