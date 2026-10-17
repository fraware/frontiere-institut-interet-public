"""Supprimer uniquement six branches anciennes entièrement incluses dans main.

Chaque référence est préenregistrée avec son SHA. L'ascendance est vérifiée
dans le clone complet de main avant toute suppression. Les branches associées
à une PR ouverte ou protégées sont conservées. Aucune recherche par préfixe,
aucune suppression forcée et aucune réécriture de l'historique n'est permise.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Callable

from scripts.nettoyer_branches_fusionnees import (
    GitHub, NettoyageRefuse, REPO_ATTENDU,
)

RACINE = Path(__file__).resolve().parents[1]
PLAN = RACINE / "institutionnel/maintenance/branches_ancetres_2026-10-17.json"
VERSION = "frontiere-ancetres-hygiene-v1"
SHA = re.compile(r"^[0-9a-f]{40}$")
NOM = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_./-]{0,180}$")


def imposer(ok: bool, cause: str) -> None:
    if not ok:
        raise NettoyageRefuse(cause)


def verifier_plan(plan: dict) -> list[dict]:
    imposer(isinstance(plan, dict) and plan.get("version") == VERSION
            and plan.get("repository") == REPO_ATTENDU,
            "Plan inattendu.")
    items = plan.get("candidats")
    imposer(isinstance(items, list) and len(items) == 6,
            "Exactement six branches initiales sont attendues.")
    noms = set()
    for item in items:
        imposer(isinstance(item, dict) and set(item) == {"branche", "sha"},
                "Entrée de plan inattendue.")
        nom, sha = item["branche"], item["sha"]
        imposer(isinstance(nom, str) and NOM.fullmatch(nom) is not None
                and nom not in noms and nom not in {"main", "master"}
                and not nom.startswith("refs/") and not nom.endswith("/")
                and ".." not in nom and "//" not in nom and "\\" not in nom
                and isinstance(sha, str) and SHA.fullmatch(sha) is not None,
                "Référence dangereuse, inconnue ou dupliquée.")
        noms.add(nom)
    return items


def selectionner(candidats: list[dict], branches: list[dict],
                ouvertes: list[dict],
                ancetre: Callable[[str], bool]) -> tuple[list[dict], list[dict]]:
    """Refuser les branches modifiées, utilisées ou non intégrées."""
    visibles = {b["name"]: b for b in branches}
    actives = {
        (p.get("head") or {}).get("ref") for p in ouvertes
        if ((p.get("head") or {}).get("repo") or {}).get("full_name") == REPO_ATTENDU
    }
    admissibles, exclues = [], []
    for item in candidats:
        nom, sha = item["branche"], item["sha"]
        b = visibles.get(nom)
        if b is None:
            raison = "absente"
        elif b.get("protected") is not False:
            raison = "protegee"
        elif nom in actives:
            raison = "pr_ouverte"
        elif (b.get("commit") or {}).get("sha") != sha:
            raison = "sha_modifie"
        elif not ancetre(sha):
            raison = "contenu_non_integre"
        else:
            raison = None
        if raison:
            exclues.append({"branche": nom, "raison": raison})
        else:
            admissibles.append(item)
    return admissibles, exclues


def est_ancetre(sha: str, main: str) -> bool:
    """Le commit doit exister et être ancêtre strict ou égal de main."""
    resultat = subprocess.run(
        ["git", "merge-base", "--is-ancestor", sha, main],
        cwd=RACINE, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, check=False, timeout=15,
    )
    return resultat.returncode == 0


def executer(plan: dict, client: GitHub, appliquer: bool) -> dict:
    candidats = verifier_plan(plan)
    depot = client.appel("")
    imposer(depot.get("full_name") == REPO_ATTENDU
            and depot.get("default_branch") == "main",
            "Dépôt GitHub inattendu.")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=RACINE,
        capture_output=True, text=True, check=True, timeout=15,
    ).stdout.strip()
    imposer(SHA.fullmatch(head) is not None and client.etat_ref("main") == head,
            "Main a changé depuis le contrôle : interrompre sans suppression.")
    branches = client.pages("/branches")
    ouvertes = client.pages("/pulls?state=open")
    eligibles, exclues = selectionner(
        candidats, branches, ouvertes, lambda x: est_ancetre(x, head)
    )
    resultat = {
        "version": VERSION,
        "mode": "suppression" if appliquer else "simulation",
        "main": head, "candidats": len(candidats),
        "admissibles": len(eligibles), "supprimees": [],
        "exclues": exclues, "erreurs": [],
    }
    if not appliquer:
        return resultat
    for item in eligibles:
        nom, sha = item["branche"], item["sha"]
        try:
            if client.etat_ref("main") != head:
                resultat["erreurs"].append(
                    {"branche": nom, "raison": "main_modifie"})
                break
            if client.etat_ref(nom) != sha:
                resultat["exclues"].append(
                    {"branche": nom, "raison": "ref_modifie"})
                continue
            if not est_ancetre(sha, head):
                resultat["exclues"].append(
                    {"branche": nom, "raison": "preuve_ancetre_perdue"})
                continue
            client.supprimer(nom)
            resultat["supprimees"].append(nom)
        except NettoyageRefuse as exc:
            resultat["erreurs"].append(
                {"branche": nom, "raison": str(exc)[:180]})
    return resultat


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--appliquer", action="store_true")
    parser.add_argument("--rapport", type=Path, required=True)
    args = parser.parse_args()
    try:
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        bilan = executer(plan, GitHub(os.getenv("GH_TOKEN", "")), args.appliquer)
    except (NettoyageRefuse, OSError, ValueError, TypeError,
            KeyError, subprocess.SubprocessError) as exc:
        print(f"Suppression refusée : {exc}", file=sys.stderr)
        return 1
    args.rapport.parent.mkdir(parents=True, exist_ok=True)
    args.rapport.write_text(
        json.dumps(bilan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "candidats": bilan["candidats"],
        "admissibles": bilan["admissibles"],
        "supprimees": len(bilan["supprimees"]),
        "exclues": len(bilan["exclues"]),
        "erreurs": len(bilan["erreurs"]),
    }, ensure_ascii=False))
    return 1 if bilan["erreurs"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
