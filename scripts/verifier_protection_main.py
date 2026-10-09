"""Auditer sans privilège d'administration les règles effectives de main.

Le contrôle distingue le réglage proposé, le statut public de la branche et
les règles actives lisibles. Il ne modifie aucune protection administrative.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO = "fraware/frontiere-institut-interet-public"
BRANCHE = "main"
VERIFICATIONS = frozenset({"Python 3.11", "Python 3.12", "Conteneur"})
APPLICATION_CI = 15368
RACINE = Path(__file__).resolve().parents[1]
MODELE = RACINE / "gouvernance/regle_protection_main_v1.json"


class ErreurProtection(ValueError):
    """Incohérence de règles ou réponse GitHub inaccessible."""


def verifier_modele(regle: dict) -> dict:
    """Vérifier la politique désirée sans la confondre avec une règle active."""
    if not isinstance(regle, dict):
        raise ErreurProtection("Le modèle de règle doit être un objet JSON.")
    if regle.get("target") != "branch" or regle.get("enforcement") != "active":
        raise ErreurProtection("Une règle de branche active est indispensable.")
    ref = regle.get("conditions", {}).get("ref_name", {})
    if ref.get("include") != ["refs/heads/main"] or ref.get("exclude") != []:
        raise ErreurProtection("La politique doit viser uniquement main.")
    if regle.get("bypass_actors") != []:
        raise ErreurProtection("Aucun contournement permanent n'est prévu.")
    rules = regle.get("rules")
    if not isinstance(rules, list):
        raise ErreurProtection("Liste des contrôles absente.")
    types = [item.get("type") for item in rules if isinstance(item, dict)]
    if len(set(types)) != len(rules):
        raise ErreurProtection("Règle vide ou répétée.")
    for required in ("deletion", "non_fast_forward", "required_linear_history",
                     "pull_request", "required_status_checks"):
        if required not in types:
            raise ErreurProtection(f"Protection manquante : {required}.")
    pr = next(item["parameters"] for item in rules if item["type"] == "pull_request")
    if (pr.get("required_approving_review_count") != 0
            or pr.get("allowed_merge_methods") != ["squash"]
            or pr.get("required_review_thread_resolution") is not True):
        raise ErreurProtection("Méthode de fusion ou politique de revue inattendue.")
    controle = next(item["parameters"] for item in rules if item["type"] == "required_status_checks")
    checks = controle.get("required_status_checks", [])
    if (not isinstance(checks, list)
            or {x.get("context") for x in checks if isinstance(x, dict)} != VERIFICATIONS
            or len(checks) != len(VERIFICATIONS)
            or not all(x.get("integration_id") == APPLICATION_CI for x in checks)):
        raise ErreurProtection("Les trois vérifications doivent provenir de GitHub Actions.")
    if controle.get("strict_required_status_checks_policy") is not False:
        raise ErreurProtection("La politique initiale doit rester non stricte pendant la réception.")
    return {
        "modele_structurellement_conforme": True,
        "verifications_prevues": sorted(VERIFICATIONS),
        "source_verifications": "GitHub Actions (identifiant 15368)",
        "protection_effectivement_active": False,
    }


def _recevoir(url: str) -> object:
    """Effectuer exclusivement une lecture JSON vers l'API GitHub publique."""
    if not url.startswith(f"https://api.github.com/repos/{REPO}/"):
        raise ErreurProtection("Adresse de lecture GitHub non autorisée.")
    entetes = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "frontiere-protection-main",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    jeton = os.environ.get("GITHUB_TOKEN")
    if jeton:
        entetes["Authorization"] = f"Bearer {jeton}"
    try:
        with urlopen(Request(url, headers=entetes), timeout=12) as resultat:
            return json.load(resultat)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise ErreurProtection(
            "Lecture GitHub impossible : statut administratif et règles non attestés."
        ) from exc


def lire_github() -> tuple[dict, list[dict]]:
    base = f"https://api.github.com/repos/{REPO}"
    branche = _recevoir(base + "/branches/main")
    if not isinstance(branche, dict):
        raise ErreurProtection("Réponse sur la branche incorrecte.")
    sommaire = _recevoir(base + "/rulesets?includes_parents=true&per_page=100")
    if not isinstance(sommaire, list):
        raise ErreurProtection("Réponse sur les règles incorrecte.")
    # Au-delà d'une page, le contrôle doit refuser une conclusion d'exhaustivité.
    if len(sommaire) == 100:
        raise ErreurProtection("Nombre de règles nécessitant une pagination supplémentaire.")
    details = []
    for item in sommaire:
        if not isinstance(item, dict) or not isinstance(item.get("id"), int):
            raise ErreurProtection("Identification d'une règle impossible.")
        if item.get("enforcement") != "active":
            continue
        complet = _recevoir(base + "/rulesets/" + str(item["id"]))
        if not isinstance(complet, dict):
            raise ErreurProtection("Détails de règle illisibles.")
        details.append(complet)
    return branche, details


def _cible_main(regle: dict) -> bool:
    """Ne reconnaître que les désignations explicites, sans inventer un filtre."""
    critere = regle.get("conditions", {}).get("ref_name", {})
    inclusions = critere.get("include", [])
    exclusions = critere.get("exclude", [])
    return (isinstance(inclusions, list) and isinstance(exclusions, list)
            and ("refs/heads/main" in inclusions or "~DEFAULT_BRANCH" in inclusions)
            and not any(x in exclusions for x in ("refs/heads/main", "~DEFAULT_BRANCH", "~ALL")))


def evaluer_github(branche: dict, regles: list[dict]) -> dict:
    """Vérifier seulement les propriétés réellement attestées par l'API."""
    if branche.get("name") != BRANCHE or type(branche.get("protected")) is not bool:
        raise ErreurProtection("L'état de main n'est pas vérifiable.")
    applicables = [r for r in regles if r.get("enforcement") == "active" and _cible_main(r)]
    types = {item.get("type") for r in applicables for item in r.get("rules", [])}
    checks: dict[str, bool] = {}
    mr_obligatoire = False
    bypass_observe = True
    for r in applicables:
        if "bypass_actors" not in r:
            bypass_observe = False
        elif r["bypass_actors"]:
            bypass_observe = False
        for item in r.get("rules", []):
            if item.get("type") == "pull_request":
                mr_obligatoire = True
            if item.get("type") == "required_status_checks":
                for ch in item.get("parameters", {}).get("required_status_checks", []):
                    if isinstance(ch, dict) and ch.get("context") in VERIFICATIONS:
                        checks[ch["context"]] = ch.get("integration_id") == APPLICATION_CI
    preuves = {
        "branche_main_protegee": branche["protected"],
        "regles_actives_lisibles": len(applicables),
        "suppression_interdite": "deletion" in types,
        "poussee_forcee_interdite": "non_fast_forward" in types,
        "proposition_obligatoire": mr_obligatoire,
        "historique_lineaire": "required_linear_history" in types,
        "verifications_obligatoires_github_actions": (
            sorted(k for k, value in checks.items() if value)
        ),
        "absence_contournement_attestee": bypass_observe and bool(applicables),
        "origine_de_protection_classique_inspectable": False,
    }
    preuves["conformite_regles_lisibles"] = all((
        preuves["branche_main_protegee"],
        preuves["suppression_interdite"],
        preuves["poussee_forcee_interdite"],
        preuves["proposition_obligatoire"],
        preuves["historique_lineaire"],
        set(preuves["verifications_obligatoires_github_actions"]) == VERIFICATIONS,
    ))
    preuves["audit_complet"] = (
        preuves["conformite_regles_lisibles"]
        and preuves["absence_contournement_attestee"]
    )
    return preuves


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exiger", action="store_true",
                        help="Exiger les protections publiquement vérifiables.")
    parser.add_argument("--exiger-integral", action="store_true",
                        help="Exiger aussi une liste de contournement complète, accessible aux administrateurs.")
    parser.add_argument("--modele-seulement", action="store_true",
                        help="Examiner la politique proposée sans accès réseau.")
    args = parser.parse_args()
    if args.modele_seulement and (args.exiger or args.exiger_integral):
        parser.error("La validation de la protection active exige une lecture de GitHub.")
    try:
        projet = json.loads(MODELE.read_text(encoding="utf-8"))
        proposition = verifier_modele(projet)
        if args.modele_seulement:
            resultat = proposition
        else:
            branche, regles = lire_github()
            resultat = {
                "version_schema": "verification-protection-main-v1",
                "proposition": proposition,
                "etat_actuel": evaluer_github(branche, regles),
            }
    except (OSError, UnicodeError, json.JSONDecodeError, ErreurProtection) as exc:
        parser.exit(2, f"Contrôle non établi : {exc}\n")
    print(json.dumps(resultat, ensure_ascii=False, indent=2))
    if not args.modele_seulement:
        actif = resultat["etat_actuel"]
        if args.exiger and not actif["conformite_regles_lisibles"]:
            parser.exit(1, "Les protections publiquement vérifiables sont incomplètes.\n")
        if args.exiger_integral and not actif["audit_complet"]:
            parser.exit(1, "La liste des contournements n'est pas intégralement attestée.\n")


if __name__ == "__main__":
    main()
