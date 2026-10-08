"""Figer puis vérifier les réponses avant toute ouverture des références privées."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from verifier_reponses_jeu_reserve import verifier_reponses


def empreinte(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


def creer_manifeste(questions: Path, reponses: Path) -> dict:
    jeu = json.loads(questions.read_text(encoding="utf-8"))
    donnees = json.loads(reponses.read_text(encoding="utf-8"))
    verifier_reponses(jeu, donnees)
    return {
        "version_schema": "gel-reponses-independantes-v1",
        "methode": donnees["methode"],
        "version_methode": donnees["version_methode"],
        "nombre_cas": len(donnees["cas"]),
        "empreinte_sha256_questions": empreinte(questions),
        "empreinte_sha256_reponses": empreinte(reponses),
        "enregistre_a": datetime.now(timezone.utc).isoformat(),
        "attestation_externe": None,
        "avertissement": "Le manifeste local seul ne prouve pas l'antériorité indépendante.",
    }


def verifier_manifeste(questions: Path, reponses: Path, manifeste: dict) -> bool:
    """Contrôle le gel local complet, sans présumer d'une attestation extérieure."""
    if not isinstance(manifeste, dict):
        return False
    try:
        donnees = json.loads(reponses.read_text(encoding="utf-8"))
        jeu = json.loads(questions.read_text(encoding="utf-8"))
        verifier_reponses(jeu, donnees)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return False
    return (
        manifeste.get("version_schema") == "gel-reponses-independantes-v1"
        and manifeste.get("empreinte_sha256_questions") == empreinte(questions)
        and manifeste.get("empreinte_sha256_reponses") == empreinte(reponses)
        and manifeste.get("methode") == donnees["methode"]
        and manifeste.get("version_methode") == donnees["version_methode"]
        and manifeste.get("nombre_cas") == len(donnees["cas"])
    )


def principal() -> None:
    parser = argparse.ArgumentParser(description="Figer les réponses du jeu réservé avant évaluation.")
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--reponses", type=Path, required=True)
    parser.add_argument("--manifeste", type=Path, required=True)
    parser.add_argument("--verifier", action="store_true", help="Comparer les fichiers à un manifeste existant.")
    args = parser.parse_args()

    if args.verifier:
        manifeste = json.loads(args.manifeste.read_text(encoding="utf-8"))
        if not verifier_manifeste(args.questions, args.reponses, manifeste):
            raise SystemExit("Échec de vérification : questions ou réponses modifiées.")
        print("Empreintes conformes au manifeste.")
        return

    manifeste = creer_manifeste(args.questions, args.reponses)
    args.manifeste.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.manifeste.open("x", encoding="utf-8") as sortie:
            json.dump(manifeste, sortie, ensure_ascii=False, indent=2)
            sortie.write("\n")
    except FileExistsError as erreur:
        raise SystemExit("Un manifeste existe déjà : utiliser --verifier ou un nouveau chemin.") from erreur
    print("Manifeste créé. Enregistrer son empreinte auprès d'un tiers AVANT ouverture des références.")


if __name__ == "__main__":
    principal()
