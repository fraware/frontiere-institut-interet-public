"""Contrôler les journaux de séances et les durées déclarées, sans les modifier."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from verifier_reponses_jeu_reserve import verifier_reponses


def horodatage(valeur: str) -> datetime:
    if not isinstance(valeur, str):
        raise ValueError("horodatage absent ou invalide")
    instant = datetime.fromisoformat(valeur)
    if instant.utcoffset() is None:
        raise ValueError("horodatage sans fuseau horaire")
    return instant.astimezone(timezone.utc)


def auditer(questions: dict, reponses: dict, journal: dict, budget_minutes: int, tolerance_secondes: float = 2) -> dict:
    verifier_reponses(questions, reponses)
    if type(budget_minutes) is not int or budget_minutes < 1:
        raise ValueError("budget par cas invalide")
    if type(tolerance_secondes) not in (int, float) or not math.isfinite(tolerance_secondes) or tolerance_secondes < 0:
        raise ValueError("tolérance invalide")
    if journal.get("version_schema") != "journal-session-v1":
        raise ValueError("version du journal incorrecte")
    if journal.get("methode") != reponses["methode"]:
        raise ValueError("les méthodes du journal et des réponses diffèrent")
    if not isinstance(journal.get("operateur_code"), str) or not journal["operateur_code"].strip():
        raise ValueError("identifiant opérateur obligatoire")
    if not isinstance(journal.get("version_logiciel_ou_modele"), str) or not journal["version_logiciel_ou_modele"].strip():
        raise ValueError("version du logiciel ou modèle obligatoire")
    records = journal.get("cas")
    if not isinstance(records, list):
        raise ValueError("journal sans cas")
    codes = [r.get("code") for r in records if isinstance(r, dict)]
    expected = {r["code"] for r in reponses["cas"]}
    if len(codes) != len(records) or len(set(codes)) != len(codes) or set(codes) != expected:
        raise ValueError("journal : cas manquants, dupliqués ou inattendus")
    by_code = {r["code"]: r for r in records}
    anomalies = []
    lignes = []
    for reponse in reponses["cas"]:
        code = reponse["code"]
        j = by_code[code]
        observations = []
        for cle in ("budget_respecte", "reconnaissance_fortuite_origine"):
            if type(j.get(cle)) is not bool:
                observations.append(f"{cle} : déclaration absente")
        if j.get("interruptions_ou_ecarts") is None or not isinstance(j["interruptions_ou_ecarts"], str):
            observations.append("interruptions ou écarts : déclaration absente")
        if not isinstance(j.get("sources_revelant_solution"), list) or any(
            not isinstance(s, str) or not s.strip() for s in j.get("sources_revelant_solution", [])
        ):
            observations.append("sources révélant la solution : liste invalide")
        mesure = None
        try:
            debut = horodatage(j.get("debut_iso"))
            fin = horodatage(j.get("fin_iso"))
            mesure = (fin - debut).total_seconds()
            if mesure < 0:
                observations.append("fin antérieure au début")
            if reponse["duree_secondes"] is None:
                observations.append("durée des réponses inconnue malgré des horodatages")
            elif abs(reponse["duree_secondes"] - mesure) > tolerance_secondes:
                observations.append("durée des réponses incompatible avec le journal")
            if mesure > budget_minutes * 60 + tolerance_secondes:
                observations.append("dépassement du plafond de temps")
            if type(j.get("budget_respecte")) is bool and j["budget_respecte"] != (mesure <= budget_minutes * 60 + tolerance_secondes):
                observations.append("déclaration de respect du budget contradictoire")
        except (ValueError, TypeError):
            observations.append("horodatages absents ou invalides")
        lignes.append({
            "code": code,
            "secondes_journal": mesure,
            "secondes_reponses": reponse["duree_secondes"],
            "anomalies": observations,
        })
        for detail in observations:
            anomalies.append({"code": code, "description": detail})
    return {
        "version_schema": "audit-journal-sessions-v1",
        "methode": reponses["methode"],
        "nombre_cas": len(lignes),
        "budget_maximal_minutes_par_cas": budget_minutes,
        "nombre_anomalies": len(anomalies),
        "anomalies": anomalies,
        "cas": lignes,
        "modifications_apportees": False,
        "limite": "Contrôle déclaratif et chronologique, sans vérification indépendante du travail effectué.",
    }


def principal() -> None:
    p = argparse.ArgumentParser(description="Auditer les durées et anomalies des séances.")
    p.add_argument("--questions", required=True, type=Path)
    p.add_argument("--reponses", required=True, type=Path)
    p.add_argument("--journal", required=True, type=Path)
    p.add_argument("--budget-minutes-par-cas", required=True, type=int)
    p.add_argument("--sortie", required=True, type=Path)
    args = p.parse_args()
    if args.sortie.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        raise SystemExit("Rapport à conserver hors du dépôt public.")
    try:
        rapport = auditer(
            json.loads(args.questions.read_text(encoding="utf-8")),
            json.loads(args.reponses.read_text(encoding="utf-8")),
            json.loads(args.journal.read_text(encoding="utf-8")),
            args.budget_minutes_par_cas,
        )
    except (ValueError, TypeError, OSError) as erreur:
        raise SystemExit(f"Journal invalide : {erreur}") from erreur
    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.sortie.open("x", encoding="utf-8") as fichier:
            json.dump(rapport, fichier, ensure_ascii=False, indent=2)
            fichier.write("\n")
    except FileExistsError as erreur:
        raise SystemExit("Le rapport existe déjà.") from erreur


if __name__ == "__main__":
    principal()
