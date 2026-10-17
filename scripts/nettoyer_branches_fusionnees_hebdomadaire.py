"""Entretien hebdomadaire des seules branches de demandes de fusion intégrées.

Ce programme ne touche pas aux PR ouvertes, PR fermées sans fusion, branches
sans PR associée, branches protégées ou branches récemment fusionnées.
Il réutilise le vérificateur de références exactes du nettoyage exceptionnel.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys

from scripts.nettoyer_branches_fusionnees import (
    GitHub, LIMITE_SUPPRESSIONS, NettoyageRefuse, PLAN_VERSION,
    REPO_ATTENDU, executer, selectionner,
)

DELAI_HEURES = 24


def elaborer_plan(branches: list[dict], fermees: list[dict],
                  ouvertes: list[dict], maintenant: datetime) -> dict:
    """Construire uniquement les références anciennes et exactement intégrées."""
    if maintenant.tzinfo is None:
        raise NettoyageRefuse("Date de contrôle sans fuseau.")
    seuil = maintenant.astimezone(timezone.utc) - timedelta(hours=DELAI_HEURES)
    par_nom: dict[str, list[dict]] = {}
    for p in fermees:
        head = p.get("head") or {}
        repo = head.get("repo") or {}
        date = p.get("merged_at")
        if (repo.get("full_name") != REPO_ATTENDU or not date
                or not isinstance(head.get("ref"), str)):
            continue
        try:
            fusion = datetime.fromisoformat(date.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as exc:
            raise NettoyageRefuse("Horodatage de fusion incompatible.") from exc
        if fusion.tzinfo is None:
            raise NettoyageRefuse("Horodatage de fusion sans fuseau.")
        if fusion.astimezone(timezone.utc) > seuil:
            continue
        par_nom.setdefault(head["ref"], []).append(p)
    ouverts_noms = {
        (p.get("head") or {}).get("ref") for p in ouvertes
        if ((p.get("head") or {}).get("repo") or {}).get("full_name") == REPO_ATTENDU
    }
    candidats = []
    for b in branches:
        nom, sha = b.get("name"), (b.get("commit") or {}).get("sha")
        if (not isinstance(nom, str) or nom == "main" or b.get("protected") is not False
                or nom in ouverts_noms):
            continue
        pr = next((p for p in par_nom.get(nom, []) if
                   (p.get("head") or {}).get("sha") == sha), None)
        if pr is not None:
            candidats.append({"branche": nom, "sha": sha, "pr": pr["number"]})
    candidats.sort(key=lambda x: x["branche"])
    if len(candidats) > LIMITE_SUPPRESSIONS:
        raise NettoyageRefuse("Trop de références : audit manuel nécessaire.")
    return {
        "version": PLAN_VERSION, "repository": REPO_ATTENDU,
        "type": "inventaire_dynamique_hebdomadaire",
        "candidats": candidats,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--appliquer", action="store_true")
    parser.add_argument("--rapport", required=True, type=Path)
    args = parser.parse_args()
    try:
        client = GitHub(os.getenv("GH_TOKEN", ""))
        depot = client.appel("")
        if not isinstance(depot, dict) or depot.get("full_name") != REPO_ATTENDU:
            raise NettoyageRefuse("Dépôt inattendu.")
        branches = client.pages("/branches")
        fermees = client.pages("/pulls?state=closed")
        ouvertes = client.pages("/pulls?state=open")
        plan = elaborer_plan(branches, fermees, ouvertes, datetime.now(timezone.utc))
        if not plan["candidats"]:
            rapport = {"version": PLAN_VERSION, "mode": "aucune_suppression",
                       "candidats": 0, "admissibles": 0,
                       "supprimees": [], "exclues": [], "erreurs": []}
        else:
            # Une seconde lecture REST avant suppression réévalue les ref, PR,
            # protections et SHA de la même façon que le nettoyage initial.
            rapport = executer(plan, client, args.appliquer)
    except (NettoyageRefuse, OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Revue hebdomadaire refusée : {exc}", file=sys.stderr)
        return 1
    args.rapport.parent.mkdir(parents=True, exist_ok=True)
    args.rapport.write_text(
        json.dumps(rapport, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"mode": rapport["mode"], "candidats": rapport["candidats"],
                      "supprimees": len(rapport["supprimees"]),
                      "exclues": len(rapport["exclues"]),
                      "erreurs": len(rapport["erreurs"])}, ensure_ascii=False))
    return 1 if rapport["erreurs"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
