from __future__ import annotations

import argparse
import json
from pathlib import Path


def normaliser(valeurs):
    return {str(v).strip().lower() for v in valeurs if str(v).strip()}


def mesurer(attendus, proposes):
    reference = normaliser(attendus)
    proposition = normaliser(proposes)
    if not reference:
        return {"precision": None, "rappel": None, "mesure_harmonique": None}
    precision = len(reference & proposition) / len(proposition) if proposition else 0.0
    rappel = len(reference & proposition) / len(reference)
    harmonique = 0.0 if precision + rappel == 0 else 2 * precision * rappel / (precision + rappel)
    return {"precision": precision, "rappel": rappel, "mesure_harmonique": harmonique}


def principal() -> None:
    analyseur = argparse.ArgumentParser(description="Compare les réponses aux références historiques des cas rétrospectifs.")
    analyseur.add_argument("--references", required=True)
    analyseur.add_argument("--reponses", required=True)
    analyseur.add_argument("--sortie", default="resultats_retrospectifs.json")
    arguments = analyseur.parse_args()

    references = json.loads(Path(arguments.references).read_text(encoding="utf-8"))
    reponses = json.loads(Path(arguments.reponses).read_text(encoding="utf-8"))

    references_par_code = {cas["code"]: cas for cas in references["cas"]}
    reponses_par_code = {cas["code"]: cas for cas in reponses["cas"]}

    if set(references_par_code) != set(reponses_par_code):
        raise SystemExit("les réponses et les références ne couvrent pas les mêmes cas")

    lignes = []
    for code in sorted(references_par_code):
        reference = references_par_code[code]
        reponse = reponses_par_code[code]
        lignes.append({
            "code": code,
            "voies": mesurer(reference["voies_attendues"], reponse["voies"]),
            "formes_ressource": mesurer(reference["formes_attendues"], reponse["formes_ressource"]),
            "minutes_humaines": max(0, reponse.get("minutes_humaines", 0)),
        })

    def moyenne(champ, sous_champ):
        valeurs = [ligne[champ][sous_champ] for ligne in lignes if ligne[champ][sous_champ] is not None]
        return sum(valeurs) / len(valeurs) if valeurs else None

    rapport = {
        "version_schema": "resultats-cas-retrospectifs-developpement-v1",
        "methode": reponses.get("methode"),
        "version_methode": reponses.get("version_methode"),
        "nombre_cas": len(lignes),
        "voies_precision_moyenne": moyenne("voies", "precision"),
        "voies_rappel_moyen": moyenne("voies", "rappel"),
        "voies_mesure_harmonique_moyenne": moyenne("voies", "mesure_harmonique"),
        "formes_precision_moyenne": moyenne("formes_ressource", "precision"),
        "formes_rappel_moyen": moyenne("formes_ressource", "rappel"),
        "formes_mesure_harmonique_moyenne": moyenne("formes_ressource", "mesure_harmonique"),
        "minutes_humaines_totales": sum(ligne["minutes_humaines"] for ligne in lignes),
        "cas": lignes,
    }

    Path(arguments.sortie).write_text(json.dumps(rapport, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    principal()
