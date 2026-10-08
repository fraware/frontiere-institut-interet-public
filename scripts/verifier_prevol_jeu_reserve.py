"""Contrôler les artefacts publics du jeu réservé sans ouvrir ses références privées.

Ce contrôle établit uniquement la cohérence structurelle des questions, du
formulaire vierge et de l'engagement public. Il ne certifie ni la présence du
corrigé privé ni l'indépendance de l'évaluation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

RACINE = Path(__file__).resolve().parents[1]
CODES = [f"H{i:02d}" for i in range(1, 11)]
CHAMPS_CAS = {
    "code", "voies", "formes_ressource", "ressources", "urls_preuves",
    "duree_secondes", "minutes_analyste", "minutes_verification", "notes",
}


def charger_json(chemin: Path) -> dict:
    """Charger un document JSON et refuser une racine autre qu'un objet."""
    try:
        valeur = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{chemin} : fichier illisible ou JSON incorrect") from exc
    if not isinstance(valeur, dict):
        raise ValueError(f"{chemin} : la racine doit être un objet")
    return valeur


def verifier_preparation(questions: dict, modele: dict, manifeste: dict) -> dict:
    """Vérifier la cohérence du jeu public et l'absence de réponses dans le modèle.

    Les seules données confidentielles admises sont absentes : les références
    privées ne figurent dans aucun argument. L'empreinte publiée est contrôlée
    comme format, sans prétendre la comparer au corrigé non disponible.
    """
    if questions.get("version_schema") != "jeu-reserve-v1":
        raise ValueError("Version des questions incorrecte.")
    cas = questions.get("cas")
    if not isinstance(cas, list) or [c.get("code") if isinstance(c, dict) else None for c in cas] != CODES:
        raise ValueError("Les questions doivent couvrir H01–H10 exactement et dans l'ordre.")
    for c in cas:
        if set(c) != {"code", "titre", "question"}:
            raise ValueError(f"{c['code']} : champs publics des questions inattendus.")
        for champ in ("titre", "question"):
            if not isinstance(c[champ], str) or not c[champ].strip():
                raise ValueError(f"{c['code']} : {champ} vide ou invalide.")

    if modele.get("version_schema") != "reponses-jeu-reserve-v1":
        raise ValueError("Version du modèle de réponses incorrecte.")
    if modele.get("methode") != "a-remplacer":
        raise ValueError("Le modèle public doit conserver son indicateur de méthode non renseignée.")
    if not isinstance(modele.get("version_methode"), str) or not modele["version_methode"].strip():
        raise ValueError("Version du modèle absente.")
    reponses = modele.get("cas")
    if not isinstance(reponses, list) or [r.get("code") if isinstance(r, dict) else None for r in reponses] != CODES:
        raise ValueError("Le modèle doit couvrir exactement les dix codes attendus.")
    for ligne in reponses:
        if set(ligne) != CHAMPS_CAS:
            raise ValueError(f"{ligne['code']} : champs du modèle invalides.")
        for champ in ("voies", "formes_ressource", "ressources", "urls_preuves"):
            if ligne[champ] != []:
                raise ValueError(f"{ligne['code']} : le modèle public contient une proposition.")
        if (ligne["duree_secondes"] is not None
                or type(ligne["minutes_analyste"]) is not int
                or type(ligne["minutes_verification"]) is not int
                or ligne["minutes_analyste"] != 0
                or ligne["minutes_verification"] != 0
                or ligne["notes"] != ""):
            raise ValueError(f"{ligne['code']} : le modèle contient une observation non vierge.")

    if manifeste.get("version_schema") != "manifeste-jeu-reserve-v1":
        raise ValueError("Version du manifeste incorrecte.")
    if type(manifeste.get("nombre_cas")) is not int or manifeste["nombre_cas"] != len(CODES):
        raise ValueError("Le manifeste ne déclare pas les dix cas attendus.")
    empreinte = manifeste.get("empreinte_sha256_references")
    if not isinstance(empreinte, str) or re.fullmatch(r"[a-f0-9]{64}", empreinte) is None:
        raise ValueError("Empreinte publiée du corrigé absente ou mal formée.")
    if empreinte == "0" * 64:
        raise ValueError("Empreinte du corrigé réduite à une valeur fictive.")
    if not isinstance(manifeste.get("emplacement_references"), str) or not manifeste["emplacement_references"].strip():
        raise ValueError("La séparation des références privées n'est pas décrite.")

    return {
        "version_schema": "prevol-jeu-reserve-v1",
        "conformite_structurelle": True,
        "nombre_cas_publics": len(CODES),
        "references_privees_ouvertes": False,
        "references_privees_verifiees": False,
        "resultat_independant_obtenu": False,
    }


def principal() -> None:
    parser = argparse.ArgumentParser(description="Contrôler la préparation publique du jeu réservé.")
    parser.add_argument("--questions", type=Path, default=RACINE / "evaluation/jeu_reserve_v1_questions.json")
    parser.add_argument("--modele", type=Path, default=RACINE / "evaluation/modele_reponses.json")
    parser.add_argument("--manifeste", type=Path, default=RACINE / "evaluation/jeu_reserve_v1_manifeste.json")
    args = parser.parse_args()
    try:
        resultat = verifier_preparation(
            charger_json(args.questions), charger_json(args.modele),
            charger_json(args.manifeste),
        )
    except ValueError as exc:
        parser.exit(1, f"Préparation incohérente : {exc}\n")
    for nom, chemin in (("questions", args.questions), ("modele", args.modele),
                        ("manifeste", args.manifeste)):
        resultat[f"empreinte_sha256_{nom}_public"] = hashlib.sha256(chemin.read_bytes()).hexdigest()
    print(json.dumps(resultat, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    principal()
