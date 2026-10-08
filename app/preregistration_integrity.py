"""Contrôle d'intégrité interne des préenregistrements FRONTIÈRE.

Les empreintes détectent une divergence entre contenu et empreinte enregistrée.
Elles ne constituent ni un horodatage externe ni une preuve d'antériorité.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime


def empreinte(objet: dict) -> str:
    brut = json.dumps(objet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(brut).hexdigest()


def verifier_preenregistrements(
    baseline_payload: dict | None,
    comparison_payload: dict | None,
    baseline_timestamp: datetime | None = None,
    comparison_timestamp: datetime | None = None,
) -> dict:
    """Vérifie les empreintes, le lien entre documents et l'ordre des événements."""
    controles: dict[str, bool | None] = {
        "empreinte_etat_initial": None,
        "empreinte_comparaison": None,
        "lien_etat_initial_comparaison": None,
        "ordre_enregistrement": None,
    }
    if baseline_payload is not None:
        baseline = baseline_payload.get("baseline")
        signature = baseline_payload.get("baseline_sha256")
        controles["empreinte_etat_initial"] = (
            isinstance(baseline, dict)
            and isinstance(signature, str)
            and empreinte(baseline) == signature
        )
    if comparison_payload is not None:
        plan_signature = comparison_payload.get("plan_sha256")
        plan = {k: v for k, v in comparison_payload.items() if k != "plan_sha256"}
        controles["empreinte_comparaison"] = (
            isinstance(plan_signature, str) and empreinte(plan) == plan_signature
        )
        controles["lien_etat_initial_comparaison"] = (
            baseline_payload is not None
            and isinstance(baseline_payload.get("baseline_sha256"), str)
            and comparison_payload.get("baseline_sha256") == baseline_payload["baseline_sha256"]
        )
        controles["ordre_enregistrement"] = (
            baseline_timestamp is not None
            and comparison_timestamp is not None
            and baseline_timestamp <= comparison_timestamp
        )
    evaluated = [v for v in controles.values() if v is not None]
    return {
        "checks": controles,
        "internally_consistent": bool(evaluated) and all(evaluated),
        "external_timestamp_verified": False,
        "note": "Contrôle interne uniquement : ne prouve pas l'antériorité indépendante.",
    }
