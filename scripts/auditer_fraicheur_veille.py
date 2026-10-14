"""Auditer hors réseau la fraîcheur de la veille et, sur demande, ses procédures.

Le contrôle distingue le dernier relevé, la fraîcheur du contenu chez le
producteur et la dernière exécution GitHub Actions réussie. Il ne déduit
aucun besoin opérationnel de la présence d'un document dans une collecte.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
from typing import Any

RACINE = Path(__file__).resolve().parents[1]
POLITIQUE = Path("institutionnel/veille/controle_v1.json")
ORDRE = {"ok": 0, "attention": 1, "critique": 2}
CHEMIN_DATE = re.compile(r"^([a-z_]+)(?:\[(\d+)\])?$")
NOM_PROCEDURE = re.compile(r"^[a-z0-9][a-z0-9-]*\.yml$")


class PolitiqueInvalide(ValueError):
    """La politique de veille ou l'un de ses états est mal formé."""


def date_utc(valeur: Any) -> datetime:
    """Exiger une date ISO 8601 avec fuseau, sans conversion silencieuse."""
    if not isinstance(valeur, str):
        raise PolitiqueInvalide("Horodatage absent ou non textuel")
    try:
        date = datetime.fromisoformat(valeur.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PolitiqueInvalide("Horodatage ISO 8601 incorrect") from exc
    if date.tzinfo is None:
        raise PolitiqueInvalide("Horodatage sans fuseau")
    return date.astimezone(timezone.utc)


def valeur_date(objet: dict, chemin: str) -> Any:
    """Lire uniquement un chemin d'attributs et d'indices explicites."""
    actuel: Any = objet
    for morceau in chemin.split("."):
        motif = CHEMIN_DATE.fullmatch(morceau)
        if motif is None:
            raise PolitiqueInvalide("Chemin d'horodatage non autorisé")
        champ, indice = motif.groups()
        if not isinstance(actuel, dict) or champ not in actuel:
            raise PolitiqueInvalide("Champ d'horodatage absent")
        actuel = actuel[champ]
        if indice is not None:
            if not isinstance(actuel, list) or int(indice) >= len(actuel):
                raise PolitiqueInvalide("Indice d'horodatage absent")
            actuel = actuel[int(indice)]
    return actuel


def lire_politique(fichier: Path) -> dict:
    """Contrôler strictement les chemins, identités et retards configurés."""
    cfg = json.loads(fichier.read_text(encoding="utf-8"))
    if not isinstance(cfg, dict) or cfg.get("version") != 1:
        raise PolitiqueInvalide("Version de politique inconnue")
    collectes, procedures = cfg.get("collectes"), cfg.get("procedures")
    if (not isinstance(collectes, list) or not collectes or len(collectes) > 100
            or not isinstance(procedures, list) or len(procedures) > 100):
        raise PolitiqueInvalide("Listes de contrôles invalides")
    vus, procedures_vues = set(), set()
    for item in collectes:
        if not isinstance(item, dict):
            raise PolitiqueInvalide("Collecte mal formée")
        nom, chemin, seuil = item.get("id"), item.get("fichier"), item.get("retard_max_heures")
        if not isinstance(nom, str) or not re.fullmatch(r"[a-z][a-z0-9_]{1,50}", nom) or nom in vus:
            raise PolitiqueInvalide("Identifiant de collecte absent, invalide ou répété")
        vus.add(nom)
        if (not isinstance(chemin, str) or not chemin.startswith("institutionnel/")
                or not chemin.endswith(".json") or "\\" in chemin
                or any(x in {"", ".", ".."} for x in chemin.split("/"))):
            raise PolitiqueInvalide("Chemin de collecte interdit")
        if (not isinstance(item.get("horodatage"), str)
                or not all(CHEMIN_DATE.fullmatch(x) for x in item["horodatage"].split("."))):
            raise PolitiqueInvalide("Sélecteur d'horodatage interdit")
        if type(seuil) is not int or not 1 <= seuil <= 8760:
            raise PolitiqueInvalide("Fenêtre de fraîcheur incorrecte")
        if item.get("criticite") not in {"critique", "haute", "moyenne"}:
            raise PolitiqueInvalide("Criticité incorrecte")
        if item.get("controle") not in {"general", "flux", "referentiel", "deliberations"}:
            raise PolitiqueInvalide("Contrôle inconnu")
    for item in procedures:
        if not isinstance(item, dict):
            raise PolitiqueInvalide("Procédure mal formée")
        nom = item.get("fichier")
        if not isinstance(nom, str) or not NOM_PROCEDURE.fullmatch(nom) or nom in procedures_vues:
            raise PolitiqueInvalide("Nom de procédure invalide ou répété")
        procedures_vues.add(nom)
        seuil = item.get("retard_max_heures")
        if type(seuil) is not int or not 1 <= seuil <= 8760:
            raise PolitiqueInvalide("Délai de procédure invalide")
        if item.get("criticite") not in {"critique", "haute", "moyenne"}:
            raise PolitiqueInvalide("Criticité de procédure invalide")
    return cfg


def gravite(criticite: str) -> str:
    """Les canaux non critiques signalent une attention sans arrêter la veille."""
    return "critique" if criticite == "critique" else "attention"


def nouvel_etat(identifiant: str, nature: str) -> dict:
    return {"id": identifiant, "nature": nature, "statut": "ok", "age_heures": None, "alertes": []}


def alerter(resultat: dict, code: str, texte: str, niveau: str) -> None:
    resultat["alertes"].append({"code": code, "detail": texte, "niveau": niveau})
    if ORDRE[niveau] > ORDRE[resultat["statut"]]:
        resultat["statut"] = niveau


def anciennete(date: datetime, maintenant: datetime) -> float:
    """Un horodatage situé plus de quinze minutes dans le futur est incohérent."""
    retard = (maintenant - date).total_seconds() / 3600
    if retard < -0.25:
        raise PolitiqueInvalide("Date observée située dans le futur")
    return max(0.0, retard)


def auditer_collecte(racine: Path, entree: dict, maintenant: datetime) -> dict:
    resultat = nouvel_etat(entree["id"], "collecte")
    fichier = racine / entree["fichier"]
    try:
        donnees = json.loads(fichier.read_text(encoding="utf-8"))
        if not isinstance(donnees, dict):
            raise PolitiqueInvalide("État non structuré")
        dernier = date_utc(valeur_date(donnees, entree["horodatage"]))
        age = anciennete(dernier, maintenant)
        resultat["age_heures"] = round(age, 2)
        if age > entree["retard_max_heures"]:
            alerter(resultat, "RELEVE_RETARDE",
                    f"{age:.1f} h depuis le relevé ; limite {entree['retard_max_heures']} h",
                    gravite(entree["criticite"]))
        for champ in ("erreurs", "echecs"):
            elements = donnees.get(champ, [])
            if isinstance(elements, list) and elements:
                alerter(resultat, "RELEVE_PARTIEL",
                        f"{len(elements)} incidents consignés dans {champ}", "attention")
        if entree["controle"] == "deliberations":
            if donnees.get("couverture_exhaustive") is False:
                resultat["couverture"] = "non_exhaustive_declaree"
            if donnees.get("tour_du_releve_termine") is False:
                resultat["progression"] = "tour_incomplet"
        elif entree["controle"] == "referentiel":
            sources = donnees.get("sources")
            if not isinstance(sources, list) or not sources:
                raise PolitiqueInvalide("Liste des sources institutionnelles absente")
            if donnees.get("nombre_sources") != len(sources):
                raise PolitiqueInvalide("Incohérence du nombre de sources")
            for source in sources:
                identite = source.get("source_id")
                if source.get("erreur"):
                    alerter(resultat, "SOURCE_INDISPONIBLE",
                            f"{identite} : contrôle de la source en erreur",
                            gravite(source.get("criticite", "moyenne")))
                elif source.get("fraicheur", {}).get("statut") in {"A_REVOIR", "ERREUR", "INDETERMINE"}:
                    alerter(resultat, "CONTENU_A_REVOIR",
                            f"{identite} : fraîcheur du contenu ancienne ou indéterminée",
                            "attention")
        elif entree["controle"] == "flux":
            sources = donnees.get("sources")
            if not isinstance(sources, list) or not sources:
                raise PolitiqueInvalide("Liste des flux absente")
            ids = set()
            for source in sources:
                identite = source.get("id")
                if not isinstance(identite, str) or identite in ids:
                    raise PolitiqueInvalide("Identité de flux absente ou dupliquée")
                ids.add(identite)
                if not source.get("actif"):
                    continue
                cadence = source.get("cadence_heures")
                if type(cadence) is not int or cadence < 1:
                    raise PolitiqueInvalide("Cadence de flux invalide")
                succes = source.get("dernier_succes")
                if succes is None:
                    alerter(resultat, "FLUX_SANS_SUCCES",
                            f"{identite} : aucun succès daté", "attention")
                elif anciennete(date_utc(succes), maintenant) > max(48, 3 * cadence):
                    alerter(resultat, "FLUX_EN_RETARD",
                            f"{identite} : dernier succès trop ancien", "attention")
                if source.get("erreur"):
                    alerter(resultat, "FLUX_EN_ERREUR",
                            f"{identite} : {source['erreur']}", "attention")
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        alerter(resultat, "ETAT_ILLISIBLE", f"{type(exc).__name__}: {exc}",
                gravite(entree["criticite"]))
    return resultat


def interroger_procedure(repertoire: str, fichier: str) -> dict:
    """Consulter la seule API GitHub déclarée, sans interpréteur de commandes."""
    url = f"repos/{repertoire}/actions/workflows/{fichier}/runs?branch=main&per_page=30"
    commande = ["gh", "api", url]
    execution = subprocess.run(commande, capture_output=True, text=True,
                               timeout=25, check=False)
    if execution.returncode != 0:
        raise OSError(f"GitHub API indisponible pour {fichier} (code {execution.returncode})")
    resultat = json.loads(execution.stdout)
    if not isinstance(resultat, dict) or not isinstance(resultat.get("workflow_runs"), list):
        raise PolitiqueInvalide("Réponse GitHub sans liste d'exécutions")
    return resultat


def auditer_procedure(entree: dict, objet: dict, maintenant: datetime) -> dict:
    resultat = nouvel_etat(entree["fichier"], "procedure")
    executions = objet.get("workflow_runs")
    if not isinstance(executions, list):
        raise PolitiqueInvalide("Exécutions GitHub absentes")
    if not executions:
        alerter(resultat, "AUCUNE_EXECUTION", "Aucune exécution connue de GitHub Actions",
                gravite(entree["criticite"]))
        return resultat
    recents = sorted(executions, key=lambda x: str(x.get("created_at") or ""), reverse=True)
    dernier = recents[0]
    if dernier.get("status") == "completed" and dernier.get("conclusion") not in {"success", "skipped"}:
        alerter(resultat, "DERNIERE_EXECUTION_EN_ECHEC",
                "Dernière exécution terminée sans succès", "attention")
    reussies = [x for x in recents if x.get("status") == "completed"
                and x.get("conclusion") == "success"]
    if not reussies:
        alerter(resultat, "AUCUN_SUCCES",
                "Aucune réussite parmi les trente exécutions consultées",
                gravite(entree["criticite"]))
        return resultat
    date = date_utc(reussies[0].get("updated_at"))
    age = anciennete(date, maintenant)
    resultat["age_heures"] = round(age, 2)
    if age > entree["retard_max_heures"]:
        alerter(resultat, "PROCEDURE_RETARDEE",
                f"{age:.1f} h depuis la réussite ; limite {entree['retard_max_heures']} h",
                gravite(entree["criticite"]))
    return resultat


def produire_bilan(racine: Path, politique: dict, maintenant: datetime,
                   *, repertoire: str | None = None, interroger=interroger_procedure) -> dict:
    """Retourner un bilan déterministe ; aucune observation n'est écrite dans Git."""
    resultats = [auditer_collecte(racine, item, maintenant)
                 for item in politique["collectes"]]
    if repertoire is not None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repertoire):
            raise PolitiqueInvalide("Identité GitHub invalide")
        for entree in politique["procedures"]:
            try:
                objet = interroger(repertoire, entree["fichier"])
                resultat = auditer_procedure(entree, objet, maintenant)
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                resultat = nouvel_etat(entree["fichier"], "procedure")
                alerter(resultat, "CONTROLE_EXECUTION_IMPOSSIBLE",
                        f"{type(exc).__name__}: {exc}", gravite(entree["criticite"]))
            resultats.append(resultat)
    compte = {niveau: sum(x["statut"] == niveau for x in resultats) for niveau in ORDRE}
    return {
        "version": 1,
        "observe_le": maintenant.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "execution_procedures_verifiee": repertoire is not None,
        "nombre_controles": len(resultats),
        "statuts": compte,
        "controles": resultats,
        "couverture_nationale_garantie": False,
    }


def resume_markdown(bilan: dict) -> str:
    """Générer une table de suivi lisible dans les résultats GitHub Actions."""
    lignes = [
        "## FRONTIÈRE — état de la veille",
        f"Contrôle UTC : {bilan['observe_le']}. "
        "Ce suivi mesure la disponibilité des relevés, pas l'actualité scientifique exhaustive.",
        "",
        "| Contrôle | Type | Dernier succès/relevé (heures) | État |",
        "|---|---|---:|---|",
    ]
    for item in bilan["controles"]:
        age = "inconnu" if item["age_heures"] is None else str(item["age_heures"])
        lignes.append(f"| {item['id']} | {item['nature']} | {age} | {item['statut']} |")
        for alerte in item["alertes"]:
            lignes.append(f"  - **{alerte['code']}** ({item['id']}) : {alerte['detail']}")
    lignes.append("")
    lignes.append("Une collecte récente peut porter sur une source ancienne. Une collecte en retard "
                  "ne démontre aucune absence de besoin. Les incidents doivent être examinés dans "
                  "les états et les sources primaires.")
    return "\n".join(lignes) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--racine", type=Path, default=RACINE)
    parser.add_argument("--politique", type=Path, default=None)
    parser.add_argument("--repertoire-github", default=None,
                        help="Active la consultation des exécutions GitHub Actions.")
    parser.add_argument("--sortie-json", type=Path)
    parser.add_argument("--resume-markdown", type=Path)
    args = parser.parse_args()
    try:
        configuration = lire_politique(args.politique or args.racine / POLITIQUE)
        bilan = produire_bilan(args.racine, configuration, datetime.now(timezone.utc),
                               repertoire=args.repertoire_github)
    except (OSError, ValueError) as exc:
        print(f"Contrôle impossible : {type(exc).__name__}: {exc}")
        return 1
    texte = resume_markdown(bilan)
    print(texte)
    if args.sortie_json:
        args.sortie_json.parent.mkdir(parents=True, exist_ok=True)
        args.sortie_json.write_text(json.dumps(bilan, ensure_ascii=False, indent=2)
                                    + "\n", encoding="utf-8")
    if args.resume_markdown:
        args.resume_markdown.parent.mkdir(parents=True, exist_ok=True)
        args.resume_markdown.write_text(texte, encoding="utf-8")
    return 2 if bilan["statuts"]["critique"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
