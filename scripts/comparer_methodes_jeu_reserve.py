"""Comparer des rapports du jeu réservé, après évaluation indépendante.

Aucune référence privée n'est ouverte par ce programme.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

DIMENSIONS = (
    ("voies", "mesure_harmonique"),
    ("formes_ressource", "mesure_harmonique"),
)
TEMPS = ("minutes_analyste", "minutes_verification", "duree_secondes")


def charger(chemin: Path) -> dict:
    rapport = json.loads(chemin.read_text(encoding="utf-8"))
    if rapport.get("version_schema") != "resultats-jeu-reserve-v1":
        raise ValueError(f"{chemin}: version de rapport incorrecte")
    if not isinstance(rapport.get("methode"), str) or not rapport["methode"].strip():
        raise ValueError(f"{chemin}: méthode absente")
    if not isinstance(rapport.get("empreinte_sha256_reponses"), str):
        raise ValueError(f"{chemin}: empreinte des réponses absente")
    if not isinstance(rapport.get("empreinte_sha256_references"), str):
        raise ValueError(f"{chemin}: empreinte des références absente")
    cas = rapport.get("cas")
    if not isinstance(cas, list) or not cas or len(cas) != rapport.get("nombre_cas"):
        raise ValueError(f"{chemin}: nombre de cas incohérent")
    codes = [ligne.get("code") for ligne in cas if isinstance(ligne, dict)]
    if len(codes) != len(cas) or len(codes) != len(set(codes)):
        raise ValueError(f"{chemin}: codes manquants ou répétés")
    for ligne in cas:
        for domaine, mesure in DIMENSIONS:
            valeur = ligne.get(domaine, {}).get(mesure)
            if valeur is not None and (type(valeur) not in (int, float) or not 0 <= valeur <= 1):
                raise ValueError(f"{chemin}: valeur incorrecte pour {domaine}")
        for champ in TEMPS:
            valeur = ligne.get(champ)
            if valeur is not None and (type(valeur) not in (int, float) or valeur < 0):
                raise ValueError(f"{chemin}: valeur temporelle incorrecte pour {champ}")
    return rapport


def moyenne(valeurs: list[float | None]) -> float | None:
    valides = [x for x in valeurs if x is not None]
    return sum(valides) / len(valides) if valides else None


def comparer(rapports: list[dict]) -> dict:
    if len(rapports) != 3:
        raise ValueError("Trois méthodes distinctes sont exigées.")
    noms = [r["methode"].strip() for r in rapports]
    if len(set(noms)) != 3:
        raise ValueError("Les méthodes doivent être distinctes.")
    ref_hashes = {r["empreinte_sha256_references"] for r in rapports}
    if len(ref_hashes) != 1:
        raise ValueError("Les méthodes ont été évaluées sur des références différentes.")
    ensembles = [set(ligne["code"] for ligne in r["cas"]) for r in rapports]
    if len({frozenset(s) for s in ensembles}) != 1:
        raise ValueError("Les méthodes n'ont pas les mêmes cas.")
    codes = sorted(ensembles[0])
    index = {r["methode"]: {l["code"]: l for l in r["cas"]} for r in rapports}
    methodes = []
    for rapport in rapports:
        nom = rapport["methode"]
        lignes = index[nom]
        methodes.append({
            "methode": nom,
            "version_methode": rapport.get("version_methode"),
            "empreinte_sha256_reponses": rapport["empreinte_sha256_reponses"],
            "voies_f1_moyen": moyenne([lignes[c]["voies"]["mesure_harmonique"] for c in codes]),
            "formes_f1_moyen": moyenne([lignes[c]["formes_ressource"]["mesure_harmonique"] for c in codes]),
            "minutes_humaines_totales": sum(
                lignes[c]["minutes_analyste"] + lignes[c]["minutes_verification"] for c in codes
            ),
            "durees_observees": sum(lignes[c]["duree_secondes"] is not None for c in codes),
            "temps_ecoule_total_secondes": (
                sum(lignes[c]["duree_secondes"] for c in codes)
                if all(lignes[c]["duree_secondes"] is not None for c in codes) else None
            ),
        })
    ecarts = []
    reference = noms[0]
    for nom in noms[1:]:
        for dimension, mesure in DIMENSIONS:
            differences = []
            for code in codes:
                a = index[nom][code][dimension][mesure]
                b = index[reference][code][dimension][mesure]
                if a is not None and b is not None:
                    differences.append({"code": code, "difference": a - b})
            ecarts.append({
                "methode": nom,
                "reference": reference,
                "dimension": dimension,
                "nombre_paires": len(differences),
                "difference_moyenne": moyenne([d["difference"] for d in differences]),
                "differences_par_cas": differences,
            })
    return {
        "version_schema": "comparaison-appariee-v1",
        "nombre_cas": len(codes),
        "empreinte_sha256_references": next(iter(ref_hashes)),
        "methodes": methodes,
        "ecarts": ecarts,
        "limites": [
            "Les différences descriptives n'établissent pas un effet causal.",
            "Les ressources concrètes et la qualité des preuves ne sont pas notées par ce calcul.",
            "Dix cas ne permettent pas d'inférer une performance nationale.",
            "Les durées humaines et calendaires sont rapportées séparément.",
        ],
    }


def principal() -> None:
    parser = argparse.ArgumentParser(description="Comparer trois rapports évalués sur le même jeu réservé.")
    parser.add_argument("--rapports", nargs=3, type=Path, required=True)
    parser.add_argument("--sortie", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        resultat = comparer([charger(p) for p in arguments.rapports])
    except (ValueError, TypeError, KeyError) as erreur:
        raise SystemExit(f"Rapports incompatibles : {erreur}") from erreur
    arguments.sortie.parent.mkdir(parents=True, exist_ok=True)
    try:
        with arguments.sortie.open("x", encoding="utf-8") as fichier:
            json.dump(resultat, fichier, ensure_ascii=False, indent=2)
            fichier.write("\n")
    except FileExistsError as erreur:
        raise SystemExit("Le rapport existe déjà : choisir un nouveau chemin.") from erreur


if __name__ == "__main__":
    principal()
