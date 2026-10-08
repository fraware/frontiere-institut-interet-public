"""Auditer les recherches publiques déjà enregistrées, sans jamais les modifier.

Permet de repérer les résultats historiques qui auraient été classés comme
absence de capacité malgré une réponse inconnue ou contradictoire.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.models import SearchRun
from app.services import classify_public_search


def auditer_recherches(lignes) -> dict:
    observations = list(lignes)
    anomalies = []
    anciens = Counter()
    calcules = Counter()
    for ligne in observations:
        if ligne.search_type != "PUBLIQUE":
            continue
        anciens[str(ligne.public_result)] += 1
        try:
            attendu = classify_public_search(
                complete=ligne.complete_enough_to_conclude,
                relevant_found=ligne.public_relevant_found,
                mobilizable_found=ligne.public_mobilizable_found,
            )
        except ValueError as erreur:
            anomalies.append({
                "recherche_id": ligne.id,
                "episode_id": ligne.episode_id,
                "type": "saisie_contradictoire",
                "resultat_enregistre": ligne.public_result,
                "resultat_recalcule": None,
                "description": str(erreur),
            })
            continue
        calcules[attendu] += 1
        if ligne.public_result != attendu:
            anomalies.append({
                "recherche_id": ligne.id,
                "episode_id": ligne.episode_id,
                "type": "classification_divergente",
                "resultat_enregistre": ligne.public_result,
                "resultat_recalcule": attendu,
                "description": (
                    "Écart à examiner dans ses sources et sa chronologie ; "
                    "aucune requalification automatique."
                ),
            })
    return {
        "version_schema": "audit-recherches-publiques-v1",
        "nombre_recherches_publiques": sum(anciens.values()),
        "repartition_enregistree": dict(anciens),
        "repartition_recalculee_hors_contradictions": dict(calcules),
        "nombre_anomalies": len(anomalies),
        "anomalies": anomalies,
        "donnees_modifiees": False,
        "limite": (
            "Le reclassement calculé ne constitue pas une vérification documentaire. "
            "Chaque cas signalé exige une vérification humaine des preuves initiales."
        ),
    }


def principal() -> None:
    analyseur = argparse.ArgumentParser(
        description="Repérer les anciennes classifications incorrectes, sans écrire dans la base."
    )
    analyseur.add_argument("--sortie", type=Path, help="Rapport privé optionnel (sans écrasement).")
    analyseur.add_argument("--strict", action="store_true", help="Sortir en échec si des anomalies existent.")
    args = analyseur.parse_args()
    with SessionLocal() as db:
        rapport = auditer_recherches(db.scalars(select(SearchRun).order_by(SearchRun.id)).all())
    texte = json.dumps(rapport, ensure_ascii=False, indent=2) + "\n"
    if args.sortie is not None:
        if args.sortie.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
            raise SystemExit("Le rapport des dossiers doit rester hors du dépôt public.")
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        try:
            with args.sortie.open("x", encoding="utf-8") as fichier:
                fichier.write(texte)
        except FileExistsError as erreur:
            raise SystemExit("Rapport existant : choisir un autre chemin.") from erreur
    else:
        print(texte, end="")
    if args.strict and rapport["nombre_anomalies"]:
        raise SystemExit(1)


if __name__ == "__main__":
    principal()
