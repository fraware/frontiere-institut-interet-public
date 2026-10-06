from __future__ import annotations

import argparse
import json
from pathlib import Path


def principal() -> None:
    analyseur = argparse.ArgumentParser(description="Vérifie les réponses aux cas rétrospectifs de développement.")
    analyseur.add_argument("--questions", required=True)
    analyseur.add_argument("--categories", required=True)
    analyseur.add_argument("--reponses", required=True)
    arguments = analyseur.parse_args()

    questions = json.loads(Path(arguments.questions).read_text(encoding="utf-8"))
    categories = json.loads(Path(arguments.categories).read_text(encoding="utf-8"))
    reponses = json.loads(Path(arguments.reponses).read_text(encoding="utf-8"))

    if reponses.get("version_schema") != "reponses-cas-retrospectifs-developpement-v1":
        raise SystemExit("version_schema incorrecte")
    if not reponses.get("methode") or not reponses.get("version_methode"):
        raise SystemExit("methode et version_methode sont obligatoires")

    codes_attendus = [cas["code"] for cas in questions["cas"]]
    lignes = reponses.get("cas")
    if not isinstance(lignes, list):
        raise SystemExit("cas doit être une liste")

    voies_admises = set(categories["voies_resolution"])
    formes_admises = set(categories["formes_ressource"])

    codes_vus = []
    for ligne in lignes:
        code = ligne.get("code")
        codes_vus.append(code)
        if not isinstance(ligne.get("voies"), list):
            raise SystemExit(f"{code} : voies doit être une liste")
        if not isinstance(ligne.get("formes_ressource"), list):
            raise SystemExit(f"{code} : formes_ressource doit être une liste")
        if not isinstance(ligne.get("justification"), str):
            raise SystemExit(f"{code} : justification doit être du texte")
        if ligne.get("minutes_humaines", 0) < 0:
            raise SystemExit(f"{code} : minutes_humaines doit être positif ou nul")

        inconnues_voies = sorted(set(ligne["voies"]) - voies_admises)
        inconnues_formes = sorted(set(ligne["formes_ressource"]) - formes_admises)
        if inconnues_voies:
            raise SystemExit(f"{code} : voies non admises {inconnues_voies}")
        if inconnues_formes:
            raise SystemExit(f"{code} : formes de ressource non admises {inconnues_formes}")

    if len(codes_vus) != len(set(codes_vus)):
        raise SystemExit("un même cas apparaît plusieurs fois")

    manquants = sorted(set(codes_attendus) - set(codes_vus))
    supplementaires = sorted(set(codes_vus) - set(codes_attendus))
    if manquants or supplementaires:
        raise SystemExit(f"écart de cas : manquants={manquants}, supplémentaires={supplementaires}")

    print(f"valide : {reponses['methode']} {reponses['version_methode']} — {len(lignes)} cas")


if __name__ == "__main__":
    principal()
