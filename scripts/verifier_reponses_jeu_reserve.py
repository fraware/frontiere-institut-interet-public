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


def principal() -> None:
    analyseur = argparse.ArgumentParser(description="Vérifie un fichier de réponses avant son gel.")
    analyseur.add_argument("--questions", required=True)
    analyseur.add_argument("--reponses", required=True)
    arguments = analyseur.parse_args()

    questions = json.loads(Path(arguments.questions).read_text(encoding="utf-8"))
    reponses = json.loads(Path(arguments.reponses).read_text(encoding="utf-8"))

    if reponses.get("version_schema") != "reponses-jeu-reserve-v1":
        raise SystemExit("version_schema doit valoir reponses-jeu-reserve-v1")
    if not reponses.get("methode") or not reponses.get("version_methode"):
        raise SystemExit("methode et version_methode sont obligatoires")

    codes_attendus = [cas["code"] for cas in questions["cas"]]
    lignes = reponses.get("cas")
    if not isinstance(lignes, list):
        raise SystemExit("cas doit être une liste")

    codes_vus = []
    for ligne in lignes:
        manquants = CHAMPS_REQUIS - set(ligne)
        if manquants:
            raise SystemExit(f"{ligne.get('code','?')} : champs manquants {sorted(manquants)}")
        code = ligne["code"]
        codes_vus.append(code)
        for nom in ("voies", "formes_ressource", "ressources", "urls_preuves"):
            if not isinstance(ligne[nom], list):
                raise SystemExit(f"{code} : {nom} doit être une liste")
        if ligne["minutes_analyste"] < 0 or ligne["minutes_verification"] < 0:
            raise SystemExit(f"{code} : les durées doivent être positives ou nulles")
        if ligne["duree_secondes"] is not None and ligne["duree_secondes"] < 0:
            raise SystemExit(f"{code} : duree_secondes doit être positive ou nulle")

    if len(codes_vus) != len(set(codes_vus)):
        raise SystemExit("un même cas apparaît plusieurs fois")
    manquants = sorted(set(codes_attendus) - set(codes_vus))
    supplementaires = sorted(set(codes_vus) - set(codes_attendus))
    if manquants or supplementaires:
        raise SystemExit(f"écart de cas : manquants={manquants}, supplémentaires={supplementaires}")

    print(f"valide : {reponses['methode']} {reponses['version_methode']} — {len(lignes)} cas")


if __name__ == "__main__":
    principal()
