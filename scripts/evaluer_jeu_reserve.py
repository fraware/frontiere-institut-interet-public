from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def normaliser(valeurs):
    return {str(v).strip().upper() for v in valeurs if str(v).strip()}


def mesurer(attendus, proposes):
    reference = normaliser(attendus)
    proposition = normaliser(proposes)
    if not reference:
        return {"precision": None, "rappel": None, "mesure_harmonique": None}
    precision = len(reference & proposition) / len(proposition) if proposition else 0.0
    rappel = len(reference & proposition) / len(reference)
    harmonique = 0.0 if precision + rappel == 0 else 2 * precision * rappel / (precision + rappel)
    return {"precision": precision, "rappel": rappel, "mesure_harmonique": harmonique}


def empreinte(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def principal() -> None:
    analyseur = argparse.ArgumentParser(description="Évalue des réponses du jeu réservé hors du dépôt public.")
    analyseur.add_argument("--questions", required=True)
    analyseur.add_argument("--manifeste", required=True)
    analyseur.add_argument("--references", required=True)
    analyseur.add_argument("--reponses", required=True)
    analyseur.add_argument("--sortie", default="resultats_jeu_reserve.json")
    arguments = analyseur.parse_args()

    questions_path = Path(arguments.questions)
    manifeste_path = Path(arguments.manifeste)
    references_path = Path(arguments.references)
    reponses_path = Path(arguments.reponses)

    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    manifeste = json.loads(manifeste_path.read_text(encoding="utf-8"))
    references = json.loads(references_path.read_text(encoding="utf-8"))
    reponses = json.loads(reponses_path.read_text(encoding="utf-8"))

    empreinte_reelle = empreinte(references_path)
    empreinte_attendue = manifeste["empreinte_sha256_references"]
    if empreinte_reelle != empreinte_attendue:
        raise SystemExit(f"empreinte des références différente : {empreinte_reelle} != {empreinte_attendue}")

    codes_questions = {c["code"] for c in questions["cas"]}
    references_par_code = {c["code"]: c for c in references["cas"]}
    reponses_par_code = {c["code"]: c for c in reponses["cas"]}

    if codes_questions != set(references_par_code):
        raise SystemExit("les questions et les références ne couvrent pas les mêmes cas")

    manquants = sorted(codes_questions - set(reponses_par_code))
    supplementaires = sorted(set(reponses_par_code) - codes_questions)
    if manquants or supplementaires:
        raise SystemExit(f"écart de cas : manquants={manquants}, supplémentaires={supplementaires}")

    lignes = []
    for code in sorted(codes_questions):
        reference = references_par_code[code]
        reponse = reponses_par_code[code]
        voies = mesurer(reference.get("voies_attendues", []), reponse.get("voies", []))
        formes = mesurer(reference.get("formes_ressource_attendues", []), reponse.get("formes_ressource", []))
        lignes.append({
            "code": code,
            "voies": voies,
            "formes_ressource": formes,
            "minutes_analyste": max(0, reponse.get("minutes_analyste", 0)),
            "minutes_verification": max(0, reponse.get("minutes_verification", 0)),
            "duree_secondes": reponse.get("duree_secondes"),
            "nombre_preuves": len(reponse.get("urls_preuves", [])),
        })

    def moyenne(champ, sous_champ):
        valeurs = [ligne[champ][sous_champ] for ligne in lignes if ligne[champ][sous_champ] is not None]
        return sum(valeurs) / len(valeurs) if valeurs else None

    rapport = {
        "version_schema": "resultats-jeu-reserve-v1",
        "methode": reponses.get("methode"),
        "version_methode": reponses.get("version_methode"),
        "nombre_cas": len(lignes),
        "empreinte_sha256_references": empreinte_reelle,
        "voies_precision_moyenne": moyenne("voies", "precision"),
        "voies_rappel_moyen": moyenne("voies", "rappel"),
        "voies_mesure_harmonique_moyenne": moyenne("voies", "mesure_harmonique"),
        "formes_precision_moyenne": moyenne("formes_ressource", "precision"),
        "formes_rappel_moyen": moyenne("formes_ressource", "rappel"),
        "formes_mesure_harmonique_moyenne": moyenne("formes_ressource", "mesure_harmonique"),
        "minutes_humaines_totales": sum(l["minutes_analyste"] + l["minutes_verification"] for l in lignes),
        "nombre_total_preuves": sum(l["nombre_preuves"] for l in lignes),
        "cas": lignes,
    }

    Path(arguments.sortie).write_text(json.dumps(rapport, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    principal()
