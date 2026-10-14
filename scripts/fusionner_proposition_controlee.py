"""Fusion bornée d'une proposition de collecte déjà vérifiée.

Les contrôles du commit et des chemins sont d'abord exécutés par le flux GitHub
Actions appelant. Ce programme ajoute une attestation de concurrence au moment
de la fusion, refuse les changements de données communs ou de code sur main et
réessaie uniquement l'erreur transitoire documentée de GitHub.

Aucun réordonnancement de commits, aucune suppression des protections de main et
aucune fusion d'un commit différent de celui testé ne sont autorisés.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Callable

from scripts.publier_mise_a_jour_institutionnelle import (
    BRANCH, CHEMINS, PublicationRefusee, verifier_portee,
)

RACINE = Path(__file__).resolve().parents[1]
SHA = re.compile(r"^[0-9a-f]{40}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
CHANGEMENT_BASE = "Base branch was modified. Review and try the merge again."
MAX_TENTATIVES = 3


def commande(*arguments: str, racine: Path = RACINE) -> subprocess.CompletedProcess[str]:
    """Lancer git/gh sans interpréteur de commandes ni injection d'arguments."""
    if arguments[0] not in {"git", "gh"}:
        raise PublicationRefusee("Commande de fusion non autorisée")
    return subprocess.run(
        arguments, cwd=racine, capture_output=True, text=True, check=False,
        timeout=60,
    )


def sortie(*arguments: str, racine: Path = RACINE) -> str:
    resultat = commande(*arguments, racine=racine)
    if resultat.returncode:
        raise PublicationRefusee(
            f"Commande de vérification impossible ({arguments[0]} {arguments[1]}), "
            f"code {resultat.returncode}"
        )
    return resultat.stdout


def chemins_dangereux(chemins: set[str]) -> set[str]:
    """Refuser les modifications de main autres que documents et données.

    Des changements de code ou de configuration intervenus depuis le commit
    testé exigent une nouvelle intégration et de nouveaux contrôles.
    """
    return {
        chemin for chemin in chemins
        if not chemin.startswith(("institutionnel/", "docs/"))
    }


def valider_concurrence(
    source: str, attendue: str, branche: str, pr: dict,
    chemins_main: set[str],
) -> None:
    """Contrôler l'identité, la portée et la non-interférence des changements."""
    if source not in CHEMINS or not SHA.fullmatch(attendue):
        raise PublicationRefusee("Source ou empreinte de commit incorrecte")
    if not BRANCH.fullmatch(branche) or not branche.startswith(f"automatisation/{source}-"):
        raise PublicationRefusee("Branche automatique d'une autre source")
    if (pr.get("headRefName") != branche or pr.get("headRefOid") != attendue
            or pr.get("baseRefName") != "main"
            or pr.get("state") != "OPEN" or pr.get("isDraft") is not False):
        raise PublicationRefusee("Proposition modifiée, fermée, ou non admissible")
    documents = pr.get("files")
    if not isinstance(documents, list) or not documents:
        raise PublicationRefusee("Liste des fichiers de proposition absente")
    fichiers = []
    for item in documents:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise PublicationRefusee("Fichier de proposition mal formé")
        fichiers.append(item["path"])
    if len(fichiers) != len(set(fichiers)):
        raise PublicationRefusee("Chemins de proposition dupliqués")
    verifier_portee(source, fichiers)
    intersections = set(fichiers) & chemins_main
    if intersections:
        raise PublicationRefusee(
            "Chemins modifiés simultanément sur main : "
            + ", ".join(sorted(intersections)[:6])
        )
    dangereux = chemins_dangereux(chemins_main)
    if dangereux:
        raise PublicationRefusee(
            "Code ou configuration modifiés sur main depuis les contrôles : "
            + ", ".join(sorted(dangereux)[:6])
            + ". Nouvelle validation sur une base actualisée nécessaire."
        )


def examiner_proposition(
    repo: str, source: str, branche: str, attendue: str, racine: Path = RACINE,
) -> None:
    """Vérifier le commit et les changements de main jusqu'au dernier instant."""
    brut = sortie(
        "gh", "pr", "view", branche, "--repo", repo,
        "--json", "headRefName,headRefOid,baseRefName,state,isDraft,files",
        racine=racine,
    )
    try:
        pr = json.loads(brut)
    except json.JSONDecodeError as exc:
        raise PublicationRefusee("Métadonnées de proposition illisibles") from exc

    sortie("git", "fetch", "--quiet", "--no-tags", "origin", "main", branche, racine=racine)
    ancetre = sortie("git", "merge-base", attendue, "origin/main", racine=racine).strip()
    if not SHA.fullmatch(ancetre):
        raise PublicationRefusee("Ascendance Git absente")
    brut_chemins = sortie(
        "git", "diff", "--no-renames", "--name-only", "-z",
        ancetre, "origin/main", racine=racine,
    )
    changements_main = {p for p in brut_chemins.split("\0") if p}
    valider_concurrence(source, attendue, branche, pr, changements_main)


def fusionner_avec_reessais(
    repo: str, source: str, branche: str, attendue: str,
    *, verifier: Callable[[], None], fusionner: Callable[[], subprocess.CompletedProcess[str]],
    confirmer: Callable[[], bool],
    attendre: Callable[[int], None] = time.sleep,
    tentatives: int = MAX_TENTATIVES,
) -> int:
    """Réessayer exclusivement si GitHub signale une concurrence sur main."""
    if not REPO.fullmatch(repo) or source not in CHEMINS:
        raise PublicationRefusee("Dépôt ou source non conforme")
    if not SHA.fullmatch(attendue) or not BRANCH.fullmatch(branche):
        raise PublicationRefusee("Branche ou empreinte incorrecte")
    if tentatives not in {1, 2, 3}:
        raise PublicationRefusee("Nombre de tentatives non admissible")
    for indice in range(1, tentatives + 1):
        verifier()
        resultat = fusionner()
        if resultat.returncode == 0:
            if not confirmer():
                raise PublicationRefusee(
                    "Commande acceptée, sans preuve de fusion effective (file ou attente)"
                )
            return indice
        if CHANGEMENT_BASE not in resultat.stderr:
            raise PublicationRefusee(
                f"Fusion refusée pour une autre raison (code {resultat.returncode})"
            )
        if indice == tentatives:
            raise PublicationRefusee("Concurrence persistante après trois vérifications")
        attendre(3 * indice)
    raise AssertionError("Sortie de boucle inaccessible")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, choices=tuple(CHEMINS))
    parser.add_argument("--branche", required=True)
    parser.add_argument("--empreinte", required=True)
    args = parser.parse_args()
    depot = os.environ.get("GITHUB_REPOSITORY", "")
    if (os.environ.get("GITHUB_REF") != "refs/heads/main"
            or os.environ.get("GITHUB_EVENT_NAME") not in {
                "push", "schedule", "workflow_dispatch"
            } or not os.environ.get("GH_TOKEN")):
        parser.error("Fusion réservée à la procédure du dépôt principal sur main")

    try:
        n = fusionner_avec_reessais(
            depot, args.source, args.branche, args.empreinte,
            verifier=lambda: examiner_proposition(
                depot, args.source, args.branche, args.empreinte
            ),
            fusionner=lambda: commande(
                "gh", "pr", "merge", args.branche, "--repo", depot,
                "--squash", "--match-head-commit", args.empreinte,
                "--delete-branch",
            ),
            confirmer=lambda: json.loads(sortie(
                "gh", "pr", "view", args.branche, "--repo", depot,
                "--json", "state"
            )).get("state") == "MERGED",
        )
    except (PublicationRefusee, OSError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, f"Fusion contrôlée interrompue : {exc}\n")
    print(json.dumps({
        "source": args.source, "empreinte": args.empreinte,
        "fusion_effectuee": True, "nombre_tentatives": n
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
