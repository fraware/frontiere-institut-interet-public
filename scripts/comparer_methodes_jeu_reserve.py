"""Comparer des rapports du jeu réservé, après évaluation indépendante.

Aucune référence privée n'est ouverte par ce programme.
"""
from __future__ import annotations

import argparse
import math
import json
import re
from pathlib import Path

DIMENSIONS = (
    ("voies", "mesure_harmonique"),
    ("formes_ressource", "mesure_harmonique"),
)
TEMPS = ("minutes_analyste", "minutes_verification", "duree_secondes")
METHODES = ("analyste", "assistant_generaliste", "frontiere")


def charger(chemin: Path) -> dict:
    rapport = json.loads(chemin.read_text(encoding="utf-8"))
    if rapport.get("version_schema") != "resultats-jeu-reserve-v1":
        raise ValueError(f"{chemin}: version de rapport incorrecte")
    if rapport.get("methode") not in METHODES:
        raise ValueError(f"{chemin}: méthode inconnue")
    if not isinstance(rapport.get("version_methode"), str) or not rapport["version_methode"].strip():
        raise ValueError(f"{chemin}: version de méthode absente")
    for champ in ("empreinte_sha256_reponses", "empreinte_sha256_references",
                  "empreinte_sha256_gel_reponses"):
        valeur = rapport.get(champ)
        if not isinstance(valeur, str) or re.fullmatch(r"[a-f0-9]{64}", valeur) is None:
            raise ValueError(f"{chemin}: empreinte absente ou incorrecte : {champ}")
    cas = rapport.get("cas")
    if not isinstance(cas, list) or not cas or len(cas) != rapport.get("nombre_cas"):
        raise ValueError(f"{chemin}: nombre de cas incohérent")
    codes = [ligne.get("code") for ligne in cas if isinstance(ligne, dict)]
    if len(codes) != len(cas) or len(codes) != len(set(codes)):
        raise ValueError(f"{chemin}: codes manquants ou répétés")
    for ligne in cas:
        for domaine, _ in DIMENSIONS:
            valeurs = ligne.get(domaine)
            if not isinstance(valeurs, dict):
                raise ValueError(f"{chemin}: mesures absentes pour {domaine}")
            for cle in ("precision", "rappel", "mesure_harmonique"):
                valeur = valeurs.get(cle)
                if valeur is not None and (
                    type(valeur) not in (int, float)
                    or not math.isfinite(valeur) or not 0 <= valeur <= 1
                ):
                    raise ValueError(f"{chemin}: valeur incorrecte pour {domaine}/{cle}")
            p, r, f = (valeurs.get(k) for k in ("precision", "rappel", "mesure_harmonique"))
            if p is None or r is None:
                if any(v is not None for v in (p, r, f)):
                    raise ValueError(f"{chemin}: mesures partielles pour {domaine}")
            else:
                attendu = 0 if p + r == 0 else 2 * p * r / (p + r)
                if f is None or not math.isclose(f, attendu, rel_tol=1e-9, abs_tol=1e-9):
                    raise ValueError(f"{chemin}: mesure harmonique incohérente pour {domaine}")
        for champ in TEMPS:
            valeur = ligne.get(champ)
            if champ == "duree_secondes":
                if valeur is not None and (type(valeur) not in (int, float) or not math.isfinite(valeur) or valeur < 0):
                    raise ValueError(f"{chemin}: durée écoulée incorrecte")
            elif type(valeur) is not int or valeur < 0:
                raise ValueError(f"{chemin}: temps humain invalide : {champ}")
        if type(ligne.get("nombre_preuves")) is not int or ligne["nombre_preuves"] < 0:
            raise ValueError(f"{chemin}: nombre de preuves invalide")
    if rapport.get("minutes_humaines_totales") != sum(
        l["minutes_analyste"] + l["minutes_verification"] for l in cas
    ):
        raise ValueError(f"{chemin}: total humain incohérent")
    if rapport.get("nombre_total_preuves") != sum(l["nombre_preuves"] for l in cas):
        raise ValueError(f"{chemin}: nombre total de preuves incohérent")
    for domaine, prefixe in (("voies", "voies"), ("formes_ressource", "formes")):
        for cle, suffixe in (("precision", "precision_moyenne"),
                             ("rappel", "rappel_moyen"),
                             ("mesure_harmonique", "mesure_harmonique_moyenne")):
            mesures = [l[domaine][cle] for l in cas if l[domaine][cle] is not None]
            attendu = sum(mesures) / len(mesures) if mesures else None
            stocke = rapport.get(f"{prefixe}_{suffixe}")
            if attendu is None:
                if stocke is not None:
                    raise ValueError(f"{chemin}: moyenne incohérente pour {domaine}/{cle}")
            elif type(stocke) not in (int, float) or not math.isclose(
                stocke, attendu, rel_tol=1e-9, abs_tol=1e-9
            ):
                raise ValueError(f"{chemin}: moyenne incohérente pour {domaine}/{cle}")
    return rapport


def moyenne(valeurs: list[float | None]) -> float | None:
    valides = [x for x in valeurs if x is not None]
    return sum(valides) / len(valides) if valides else None


def comparer(rapports: list[dict]) -> dict:
    if len(rapports) != 3:
        raise ValueError("Trois méthodes distinctes sont exigées.")
    noms = [r["methode"] for r in rapports]
    if set(noms) != set(METHODES):
        raise ValueError("Il faut exactement les trois méthodes déclarées dans le protocole.")
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
    for nom, reference in (
        ("assistant_generaliste", "analyste"),
        ("frontiere", "analyste"),
        ("frontiere", "assistant_generaliste"),
    ):
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
    parser.add_argument("--nombre-cas-attendus", type=int, default=10)
    arguments = parser.parse_args()
    depot = Path(__file__).resolve().parents[1]
    if arguments.sortie.resolve().is_relative_to(depot):
        raise SystemExit("Le rapport comparatif doit être enregistré hors du dépôt public.")
    try:
        resultat = comparer([charger(p) for p in arguments.rapports])
        if arguments.nombre_cas_attendus < 1 or resultat["nombre_cas"] != arguments.nombre_cas_attendus:
            raise ValueError("Nombre de cas différent du protocole préenregistré.")
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
