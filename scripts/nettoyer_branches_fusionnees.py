"""Nettoyage borné des références de branches issues de PR déjà fusionnées.

Le plan est une liste figée de triplets (branche, révision, numéro de PR).
Une suppression n'est admissible que si la PR est fusionnée, si le commit
de tête et la branche courante correspondent exactement aux éléments du
plan et si aucune PR ouverte n'utilise cette branche. Le script n'efface
aucune branche provenant d'une PR fermée sans fusion ni sans PR connue.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

REPO_ATTENDU = "fraware/frontiere-institut-interet-public"
PLAN_VERSION = "frontiere-nettoyage-branche-fusionnee-v1"
SHA = re.compile(r"^[0-9a-f]{40}$")
BRANCHE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_./-]{0,180}$")
LIMITE_SUPPRESSIONS = 325
CHEMIN_PLAN = Path(__file__).resolve().parents[1] / (
    "institutionnel/maintenance/branches_fusionnees_2026-10-17.json"
)


class NettoyageRefuse(ValueError):
    """Plan ou état GitHub incompatible avec une suppression sûre."""


def imposer(ok: bool, message: str) -> None:
    if not ok:
        raise NettoyageRefuse(message)


def verifier_plan(plan: dict) -> list[dict]:
    """Valider un inventaire fermé ; jamais de sélection par simple préfixe."""
    imposer(isinstance(plan, dict)
            and plan.get("version") == PLAN_VERSION
            and plan.get("repository") == REPO_ATTENDU,
            "Version ou dépôt inattendu.")
    items = plan.get("candidats")
    imposer(isinstance(items, list) and 0 < len(items) <= LIMITE_SUPPRESSIONS,
            "Taille de plan hors limites.")
    noms: set[str] = set()
    for item in items:
        imposer(isinstance(item, dict)
                and set(item) == {"branche", "sha", "pr"},
                "Objet de suppression invalide.")
        nom, sha, numero = item["branche"], item["sha"], item["pr"]
        imposer(isinstance(nom, str) and BRANCHE.fullmatch(nom) is not None
                and nom not in {"main", "master"} and not nom.startswith("refs/")
                and not nom.startswith("/") and not nom.endswith("/")
                and ".." not in nom and "//" not in nom and "\\" not in nom
                and isinstance(sha, str) and SHA.fullmatch(sha) is not None
                and type(numero) is int and numero > 0
                and nom not in noms,
                "Nom, SHA ou PR de branche invalide, répété ou protégé.")
        noms.add(nom)
    return items


def selectionner(candidats: list[dict], branches: list[dict],
                fermees: list[dict], ouvertes: list[dict],
                branche_defaut: str) -> tuple[list[dict], list[dict]]:
    """Retenir exclusivement les têtes exactes de PR réellement fusionnées."""
    refs = {b["name"]: b for b in branches}
    pr_fermees = {p["number"]: p for p in fermees}
    noms_ouverts = {
        p["head"]["ref"] for p in ouvertes
        if p.get("head", {}).get("repo", {}).get("full_name") == REPO_ATTENDU
    }
    a_supprimer: list[dict] = []
    exclus: list[dict] = []
    for candidat in candidats:
        nom, sha, numero = (
            candidat["branche"], candidat["sha"], candidat["pr"])
        raison = None
        b = refs.get(nom)
        p = pr_fermees.get(numero)
        if nom == branche_defaut:
            raison = "branche_par_defaut"
        elif nom in noms_ouverts:
            raison = "pr_ouverte"
        elif b is None:
            raison = "branche_absente"
        elif b.get("protected") is not False:
            raison = "protection_non_exclue"
        elif b.get("commit", {}).get("sha") != sha:
            raison = "sha_branche_modifie"
        elif p is None or not p.get("merged_at"):
            raison = "fusion_non_verifiee"
        elif (p.get("head", {}).get("ref") != nom
              or p.get("head", {}).get("sha") != sha
              or p.get("head", {}).get("repo", {}).get("full_name") != REPO_ATTENDU):
            raison = "pr_ou_sha_incompatible"
        if raison:
            exclus.append({"branche": nom, "raison": raison})
        else:
            a_supprimer.append(candidat)
    return a_supprimer, exclus


class GitHub:
    """Interface REST minimale, bornée à un dépôt public déterminé."""

    def __init__(self, jeton: str):
        imposer(bool(jeton), "Jeton GitHub manquant.")
        self.jeton = jeton
        self.racine = f"https://api.github.com/repos/{REPO_ATTENDU}"

    def appel(self, chemin: str, methode: str = "GET"):
        imposer(chemin.startswith("/") and "://" not in chemin
                and ".." not in chemin, "Chemin API invalide.")
        request = Request(self.racine + chemin, method=methode, headers={
            "Authorization": f"Bearer {self.jeton}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "frontiere-hygiene-ref/1.0",
        })
        try:
            with urlopen(request, timeout=25) as response:
                octets = response.read(8_000_000)
                return json.loads(octets) if octets else None
        except HTTPError as exc:
            if methode == "GET" and exc.code == 404:
                return None
            raise NettoyageRefuse(
                f"GitHub {methode} {chemin.split('?')[0]} : HTTP {exc.code}"
            ) from exc
        except URLError as exc:
            raise NettoyageRefuse("GitHub inaccessible.") from exc

    def pages(self, chemin: str) -> list[dict]:
        """Parcourir toute la pagination au lieu de supposer cent références."""
        resultats = []
        for page in range(1, 21):
            sep = "&" if "?" in chemin else "?"
            p = self.appel(f"{chemin}{sep}per_page=100&page={page}")
            imposer(isinstance(p, list), "Pagination GitHub inattendue.")
            resultats.extend(p)
            if len(p) < 100:
                return resultats
        raise NettoyageRefuse("Plus de 2 000 objets : inventaire incomplet.")

    def etat_ref(self, nom: str) -> str | None:
        ref = self.appel("/git/ref/heads/" + quote(nom, safe="/"))
        return ref.get("object", {}).get("sha") if ref else None

    def supprimer(self, nom: str) -> None:
        self.appel("/git/refs/heads/" + quote(nom, safe="/"), "DELETE")


def executer(plan: dict, client: GitHub, appliquer: bool) -> dict:
    """Contrôler le manifeste vivant et supprimer uniquement en mode explicite."""
    candidats = verifier_plan(plan)
    depot = client.appel("")
    imposer(isinstance(depot, dict)
            and depot.get("full_name") == REPO_ATTENDU
            and depot.get("default_branch") == "main",
            "Identité ou branche principale du dépôt modifiée.")
    branches = client.pages("/branches")
    ouvertes = client.pages("/pulls?state=open")
    fermees = client.pages("/pulls?state=closed")
    acceptes, exclus = selectionner(
        candidats, branches, fermees, ouvertes, depot["default_branch"])
    # Ne jamais interpréter un inventaire partiel comme absence de branches.
    imposer(len(acceptes) + len(exclus) == len(candidats),
            "Inventaire partiel.")
    rapport = {
        "version": PLAN_VERSION,
        "depot": REPO_ATTENDU,
        "mode": "suppression" if appliquer else "simulation",
        "branches_avant": len(branches),
        "candidats": len(candidats),
        "admissibles": len(acceptes),
        "supprimees": [],
        "exclues": exclus,
        "erreurs": [],
    }
    if not appliquer:
        return rapport
    for item in acceptes:
        nom, sha = item["branche"], item["sha"]
        try:
            if client.etat_ref(nom) != sha:
                rapport["exclues"].append(
                    {"branche": nom, "raison": "ref_modifiee_ou_absente"})
                continue
            client.supprimer(nom)
            rapport["supprimees"].append(nom)
        except NettoyageRefuse as exc:
            rapport["erreurs"].append(
                {"branche": nom, "erreur": str(exc)[:180]})
    return rapport


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=CHEMIN_PLAN)
    parser.add_argument("--appliquer", action="store_true")
    parser.add_argument("--rapport", required=True, type=Path)
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        result = executer(plan, GitHub(os.getenv("GH_TOKEN", "")), args.appliquer)
    except (NettoyageRefuse, OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Nettoyage refusé : {exc}", file=sys.stderr)
        return 1
    args.rapport.parent.mkdir(parents=True, exist_ok=True)
    args.rapport.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "mode": result["mode"], "candidats": result["candidats"],
        "admissibles": result["admissibles"],
        "supprimees": len(result["supprimees"]),
        "exclues": len(result["exclues"]),
        "erreurs": len(result["erreurs"]),
    }, ensure_ascii=False))
    return 1 if result["erreurs"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
