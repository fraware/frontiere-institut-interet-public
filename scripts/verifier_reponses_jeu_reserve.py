from __future__ import annotations

import argparse
import json
from pathlib import Path

CHAMPS_REQUIS = {
    "code",
    "voies",
    "formes_ressource",
    "ressources",
    "urls_preuves",
    "duree_secondes",
    "minutes_analyste",
    "minutes_verification",
    "notes",
}


def verifier_reponses(questions: dict, reponses: dict) -> None:
    """Valide les données avant gel et avant ouverture des références privées."""
    if not isinstance(reponses, dict) or reponses.get("version_schema") != "reponses-jeu-reserve-v1":
        raise ValueError("version_schema doit valoir reponses-jeu-reserve-v1")
    for nom in ("methode", "version_methode"):
        if not isinstance(reponses.get(nom), str) or not reponses[nom].strip():
            raise ValueError(f"{nom} doit être une chaîne non vide")
    if not isinstance(questions, dict) or not isinstance(questions.get("cas"), list):
        raise ValueError("questions.cas doit être une liste")
    codes_attendus = [cas["code"] for cas in questions["cas"]]
    if len(codes_attendus) != len(set(codes_attendus)):
        raise ValueError("questions : codes de cas répétés")
    lignes = reponses.get("cas")
    if not isinstance(lignes, list):
        raise ValueError("cas doit être une liste")
    codes_vus = []
    for ligne in lignes:
        if not isinstance(ligne, dict):
            raise ValueError("chaque réponse doit être un objet")
        manquants = CHAMPS_REQUIS - set(ligne)
        if manquants:
            raise ValueError(f"{ligne.get('code', '?')} : champs manquants {sorted(manquants)}")
        code = ligne["code"]
        if not isinstance(code, str) or not code.strip():
            raise ValueError("code doit être une chaîne non vide")
        codes_vus.append(code)
        for nom in ("voies", "formes_ressource", "ressources", "urls_preuves"):
            valeurs = ligne[nom]
            if not isinstance(valeurs, list) or any(
                not isinstance(valeur, str) or not valeur.strip() for valeur in valeurs
            ):
                raise ValueError(f"{code} : {nom} doit être une liste de chaînes non vides")
        for nom in ("minutes_analyste", "minutes_verification"):
            valeur = ligne[nom]
            if type(valeur) is not int or valeur < 0:
                raise ValueError(f"{code} : {nom} doit être un entier positif ou nul")
        duree = ligne["duree_secondes"]
        if duree is not None:
            import math
            if type(duree) not in (int, float) or not math.isfinite(duree) or duree < 0:
                raise ValueError(f"{code} : duree_secondes doit être un nombre fini positif ou nul")
        if not isinstance(ligne["notes"], str):
            raise ValueError(f"{code} : notes doit être une chaîne")
    if len(codes_vus) != len(set(codes_vus)):
        raise ValueError("un même cas apparaît plusieurs fois")
    manquants = sorted(set(codes_attendus) - set(codes_vus))
    supplementaires = sorted(set(codes_vus) - set(codes_attendus))
    if manquants or supplementaires:
        raise ValueError(f"écart de cas : manquants={manquants}, supplémentaires={supplementaires}")


def principal() -> None:
    analyseur = argparse.ArgumentParser(description="Vérifie un fichier de réponses avant son gel.")
    analyseur.add_argument("--questions", required=True)
    analyseur.add_argument("--reponses", required=True)
    arguments = analyseur.parse_args()
    questions = json.loads(Path(arguments.questions).read_text(encoding="utf-8"))
    reponses = json.loads(Path(arguments.reponses).read_text(encoding="utf-8"))
    try:
        verifier_reponses(questions, reponses)
    except ValueError as erreur:
        raise SystemExit(str(erreur)) from erreur
    print(f"valide : {reponses['methode']} {reponses['version_methode']} — {len(reponses['cas'])} cas")


if __name__ == "__main__":
    principal()
