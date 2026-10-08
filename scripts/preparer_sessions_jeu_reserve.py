"""Préparer des dossiers strictement publics pour trois méthodes indépendantes.

Les références et leurs réponses historiques ne sont jamais lues par ce programme.
Les dossiers sont générés localement hors du dépôt et ne doivent pas y être publiés.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


METHODES = {
    "analyste": (
        "Recherche manuelle compétente, avec sources publiques et navigateur. "
        "Aucun assistant généraliste ni outil FRONTIÈRE."
    ),
    "assistant_generaliste": (
        "Assistant généraliste avec recherche en ligne. "
        "Aucun accès à FRONTIÈRE ; relever le modèle, sa version et les outils."
    ),
    "frontiere": (
        "Utilisation explicite du logiciel et de la méthode FRONTIÈRE, "
        "avec vérification humaine et sources publiques. "
        "Enregistrer les opérations humaines et les fonctions réellement utilisées."
    ),
}


def empreinte(contenu: bytes) -> str:
    return hashlib.sha256(contenu).hexdigest()


def ecrire_json(chemin: Path, donnees: dict) -> None:
    chemin.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def preparer(
    questions_path: Path,
    modele_path: Path,
    destination: Path,
    identifiant: str,
    budget_minutes: int,
) -> dict:
    depot = Path(__file__).resolve().parents[1]
    if destination.resolve().is_relative_to(depot):
        raise ValueError("La destination doit être extérieure au dépôt public.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,80}", identifiant):
        raise ValueError("L'identifiant doit contenir 3 à 80 caractères alphanumériques, _ ou -.")
    if type(budget_minutes) is not int or budget_minutes < 1:
        raise ValueError("Le budget par cas doit être un entier strictement positif.")
    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    modele = json.loads(modele_path.read_text(encoding="utf-8"))
    if questions.get("version_schema") != "jeu-reserve-v1":
        raise ValueError("Version des questions incorrecte.")
    if modele.get("version_schema") != "reponses-jeu-reserve-v1":
        raise ValueError("Version du modèle de réponses incorrecte.")
    cas = questions.get("cas")
    if not isinstance(cas, list) or not cas:
        raise ValueError("Les questions doivent contenir une liste non vide.")
    if not all(
        isinstance(c, dict)
        and all(isinstance(c.get(k), str) and c[k].strip() for k in ("code", "titre", "question"))
        for c in cas
    ):
        raise ValueError("Chaque cas doit posséder code, titre et question.")
    codes = [c["code"] for c in cas]
    if len(codes) != len(set(codes)):
        raise ValueError("Les codes de cas doivent être uniques.")
    reponses = modele.get("cas")
    if not isinstance(reponses, list) or {r.get("code") for r in reponses} != set(codes):
        raise ValueError("Le modèle de réponses ne correspond pas aux questions.")
    if len(reponses) != len(codes):
        raise ValueError("Le modèle de réponses contient des cas répétés.")

    # Uniquement les trois champs publics nécessaires à la recherche.
    questions_publiques = {
        "version_schema": "jeu-reserve-v1",
        "cas": [{k: c[k] for k in ("code", "titre", "question")} for c in cas],
    }
    # Ne jamais recopier une réponse éventuellement déjà renseignée dans un modèle.
    lignes_vides = [{
        "code": code,
        "voies": [],
        "formes_ressource": [],
        "ressources": [],
        "urls_preuves": [],
        "duree_secondes": None,
        "minutes_analyste": 0,
        "minutes_verification": 0,
        "notes": "",
    } for code in codes]
    destination.mkdir(parents=True, exist_ok=False)
    fichiers = {}
    for methode, conditions in METHODES.items():
        dossier = destination / methode
        dossier.mkdir()
        ecrire_json(dossier / "questions.json", questions_publiques)
        ecrire_json(dossier / "reponses_vierges.json", {
            "version_schema": "reponses-jeu-reserve-v1",
            "methode": methode,
            "version_methode": "a-renseigner",
            "cas": lignes_vides,
        })
        ecrire_json(dossier / "journal_vierge.json", {
            "version_schema": "journal-session-v1",
            "identifiant_session": identifiant,
            "methode": methode,
            "operateur_code": None,
            "version_logiciel_ou_modele": None,
            "outils_et_sources_autorises": [],
            "cas": [{
                "code": code,
                "debut_iso": None,
                "fin_iso": None,
                "budget_respecte": None,
                "reconnaissance_fortuite_origine": None,
                "interruptions_ou_ecarts": None,
                "sources_revelant_solution": [],
            } for code in codes],
        })
        instructions = (
            "# Session d'évaluation indépendante\n\n"
            f"Identifiant : {identifiant}\n\n"
            f"Méthode : {methode}\n\n"
            f"Budget maximal par cas : {budget_minutes} minutes.\n\n"
            f"Conditions : {conditions}\n\n"
            "Utiliser uniquement les questions jointes comme point de départ. "
            "Ne consulter ni le dépôt de FRONTIÈRE, ni ses discussions, "
            "ni les corrigés ou les références privées. "
            "Ne pas chercher à identifier l'origine historique des questions.\n\n"
            "Pour chaque cas, relever le début et la fin de la recherche, "
            "le temps humain direct, le temps de vérification, "
            "les outils et versions employés et tout dépassement de budget, dans le journal joint. "
            "Consigner les URL qui soutiennent directement les propositions. "
            "Fournir le fichier JSON complet, même si certaines listes restent vides. "
            "Conserver les notes de séance en dehors du dépôt public.\n\n"
            "Les mêmes dix questions sont remises dans le même ordre à toutes les méthodes. "
            "Le budget constitue un plafond déclaré, pas une durée observée.\n"
        )
        (dossier / "consignes.md").write_text(instructions, encoding="utf-8")
        fichiers[methode] = {
            nom: empreinte((dossier / nom).read_bytes())
            for nom in ("questions.json", "reponses_vierges.json", "journal_vierge.json", "consignes.md")
        }
    manifeste = {
        "version_schema": "preparation-sessions-v1",
        "identifiant_session": identifiant,
        "nombre_cas": len(codes),
        "codes_cas": codes,
        "budget_maximal_minutes_par_cas": budget_minutes,
        "methodes": list(METHODES),
        "empreinte_sha256_questions_originales": empreinte(questions_path.read_bytes()),
        "empreinte_sha256_modele_original": empreinte(modele_path.read_bytes()),
        "empreintes_sha256_dossiers": fichiers,
        "reference_privee_consultee": False,
        "reponses_collectees": False,
        "attestation_externe_obtenue": False,
        "avertissement": (
            "Préparation seule : ne démontre ni indépendance réelle, "
            "ni antériorité certifiée, ni résultat d'évaluation."
        ),
    }
    ecrire_json(destination / "manifest_preparation.json", manifeste)
    return manifeste


def principal() -> None:
    parser = argparse.ArgumentParser(description="Préparer trois dossiers indépendants sans références privées.")
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--modele", type=Path, required=True)
    parser.add_argument("--sortie", type=Path, required=True)
    parser.add_argument("--identifiant-session", required=True)
    parser.add_argument("--budget-minutes-par-cas", type=int, required=True)
    args = parser.parse_args()
    try:
        manifeste = preparer(
            args.questions, args.modele, args.sortie,
            args.identifiant_session, args.budget_minutes_par_cas,
        )
    except (ValueError, FileExistsError, OSError) as erreur:
        raise SystemExit(f"Impossible de préparer les sessions : {erreur}") from erreur
    print(
        f"Dossiers préparés : {len(manifeste['methodes'])} méthodes, "
        f"{manifeste['nombre_cas']} cas. "
        "Faire enregistrer le manifeste avant distribution. "
        "Ne pas publier les travaux individuels."
    )


if __name__ == "__main__":
    principal()
