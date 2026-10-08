"""Signaler les écritures automatiques vers main avant une protection de branche.

Analyse statique conservative : détecte des commandes littérales « git push »
dans les fichiers GitHub Actions. Une construction dynamique de commande ou
une action tierce dotée d'un jeton d'écriture exige une revue supplémentaire.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

RACINE = Path(__file__).resolve().parents[1]
DOSSIER = RACINE / ".github" / "workflows"
# Dette existante autorisée pour l'audit, et non approuvée comme modèle cible.
ECRITURES_HISTORIQUES = frozenset({
    "ingestion-roae.yml",
    "ingestion-annuaire-local.yml",
    "ingestion-cog.yml",
    "ingestion-rnsr.yml",
    "surveillance-institutionnelle.yml",
})
PUSH = re.compile(r"^\s*git\s+push(?:\s|$)", re.MULTILINE)


def auditer(dossier: Path = DOSSIER) -> dict:
    """Compter les commandes identifiées et refuser les nouveaux auteurs."""
    if not dossier.is_dir():
        raise ValueError("Répertoire des procédures introuvable.")
    fichiers = sorted(dossier.glob("*.yml")) + sorted(dossier.glob("*.yaml"))
    writers = []
    for fichier in fichiers:
        lignes = fichier.read_text(encoding="utf-8").splitlines()
        occurrences = [i for i, ligne in enumerate(lignes, 1) if PUSH.match(ligne)]
        if occurrences:
            writers.append({"procedure": fichier.name, "lignes_push": occurrences,
                            "autorisee_par_inventaire": fichier.name in ECRITURES_HISTORIQUES})
    nouveaux = [x["procedure"] for x in writers if not x["autorisee_par_inventaire"]]
    return {
        "version_schema": "audit-ecritures-git-v1",
        "nombre_procedures": len(fichiers),
        "ecritures_directes_detectees": writers,
        "nouvelles_ecritures": nouveaux,
        "conformite_absence_nouveaux_push": not nouveaux,
        "protection_main_confirmee": False,
        "limite": (
            "Recherche de commandes littérales seulement. L'absence de git push "
            "n'établit ni l'absence de toute écriture ni une protection GitHub."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflows", type=Path, default=DOSSIER)
    args = parser.parse_args()
    try:
        resultat = auditer(args.workflows)
    except (ValueError, OSError, UnicodeError) as exc:
        parser.exit(1, f"Audit des écritures impossible : {exc}\n")
    print(json.dumps(resultat, ensure_ascii=False, indent=2))
    if not resultat["conformite_absence_nouveaux_push"]:
        parser.exit(1, "Nouvelles écritures directes à examiner avant fusion.\n")


if __name__ == "__main__":
    main()
