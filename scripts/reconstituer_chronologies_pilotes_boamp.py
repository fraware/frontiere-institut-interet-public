"""Reconstituer les jalons documentaires, distincts de la mobilisation effective.

Les champs proviennent exclusivement des octets des notices BOAMP vérifiées.
Les dates de publication, de décision d'attribution et d'émission du contrat
ne sont pas interchangeables ; aucune date d'exécution n'est présumée.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path

try:
    from scripts.collecter_notices_pilotes_boamp import verifier_capture
    from scripts.preparer_dossiers_pilotes_boamp import lire_cas
    from scripts.qualifier_captures_notices_boamp import ecrire
except ModuleNotFoundError:
    from collecter_notices_pilotes_boamp import verifier_capture
    from preparer_dossiers_pilotes_boamp import lire_cas
    from qualifier_captures_notices_boamp import ecrire

VERSION = "chronologie-documentaire-pilotes-v1"
RACINE = "/EFORMS/ContractAwardNotice/ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/efext:EformsExtension/efac:NoticeResult"


class ChronologieInvalide(ValueError):
    """Contradiction documentaire ou format non contrôlable."""


def elements(obj):
    """Un élément XML transformé en JSON devient tantôt objet, tantôt liste."""
    if obj is None:
        return []
    if isinstance(obj, dict):
        return [obj]
    if isinstance(obj, list) and all(isinstance(x, dict) for x in obj):
        return obj
    raise ChronologieInvalide("Structure des résultats de marchés non reconnue.")


def identite(obj):
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict) and isinstance(obj.get("#text"), str):
        return obj["#text"]
    raise ChronologieInvalide("Identifiant de lot, contrat ou résultat incorrect.")


def champ_date(obj, nom):
    if obj is None:
        return None
    if not isinstance(obj, str) or len(obj) < 10:
        raise ChronologieInvalide(f"Date de {nom} incorrecte.")
    try:
        jour = date.fromisoformat(obj[:10])
    except ValueError as exc:
        raise ChronologieInvalide(f"Date de {nom} illisible.") from exc
    if jour.isoformat() != obj[:10]:
        raise ChronologieInvalide(f"Date de {nom} non canonique.")
    return jour.isoformat()


def chemin(obj, champs):
    for cle in champs:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(cle)
    return obj


def analyser_attribution(notice):
    brut = notice.get("donnees")
    if not isinstance(brut, str):
        raise ChronologieInvalide("Formulaire officiel d'attribution absent.")
    try:
        donnees = json.loads(brut)
    except json.JSONDecodeError as exc:
        raise ChronologieInvalide("Formulaire officiel d'attribution illisible.") from exc
    racine = chemin(donnees, ["EFORMS", "ContractAwardNotice"])
    if not isinstance(racine, dict):
        raise ChronologieInvalide("ContractAwardNotice absent du formulaire d'attribution.")
    ensemble = chemin(racine, [
        "ext:UBLExtensions", "ext:UBLExtension", "ext:ExtensionContent",
        "efext:EformsExtension", "efac:NoticeResult",
    ])
    if not isinstance(ensemble, dict):
        raise ChronologieInvalide("NoticeResult officiel absent.")
    contrats = []
    for numero, contrat in enumerate(elements(ensemble.get("efac:SettledContract"))):
        code = identite(contrat.get("cbc:ID"))
        attribution = champ_date(contrat.get("cbc:AwardDate"), "décision d'attribution")
        emission = champ_date(contrat.get("cbc:IssueDate"), "émission du contrat")
        if attribution and emission and attribution > emission:
            raise ChronologieInvalide("Émission du contrat antérieure à l'attribution.")
        contrats.append({
            "identifiant_contrat": code,
            "date_attribution_declaree": attribution,
            "date_emission_contrat_declaree": emission,
            "origine_date_attribution": RACINE + (
                f"/efac:SettledContract/{numero}/cbc:AwardDate"
            ),
            "origine_date_emission": RACINE + (
                f"/efac:SettledContract/{numero}/cbc:IssueDate"
            ),
            "date_debut_execution": None,
            "date_premiere_contribution_utile": None,
        })
    lots = []
    for numero, resultat in enumerate(elements(ensemble.get("efac:LotResult"))):
        code_lot = identite(chemin(resultat, ["efac:TenderLot", "cbc:ID"]))
        code = identite(chemin(resultat, ["cbc:TenderResultCode", "#text"]))
        motif = chemin(resultat, ["efac:DecisionReason", "efbc:DecisionReasonCode", "#text"])
        if motif is not None and not isinstance(motif, str):
            raise ChronologieInvalide("Motif de non-attribution illisible.")
        lots.append({
            "identifiant_lot": code_lot,
            "code_resultat_officiel": code,
            "statut_lot": (
                "attribue" if code == "selec-w" else
                "non_attribue" if code == "clos-nw" else "indetermine"
            ),
            "motif_officiel": motif,
            "origine_resultat": RACINE + (
                f"/efac:LotResult/{numero}/cbc:TenderResultCode/#text"
            ),
            "contrat_reference": (
                identite(chemin(resultat, ["efac:SettledContract", "cbc:ID"]))
                if resultat.get("efac:SettledContract") else None
            ),
        })
    if len({x["identifiant_lot"] for x in lots}) != len(lots):
        raise ChronologieInvalide("Plusieurs résultats non distingués pour un lot.")
    return {"contrats": contrats, "resultats_par_lot": lots}


def produire(captures: Path, registre: Path):
    original = verifier_capture(captures)
    if hashlib.sha256(registre.read_bytes()).hexdigest() != original["sha256_registre"]:
        raise ChronologieInvalide("Le registre a changé depuis la capture.")
    cas = lire_cas(registre)
    references = {x["identifiant"]: x for x in original["cas"]}
    if len(cas) != len(references) or set(references) != {x["identifiant"] for x in cas}:
        raise ChronologieInvalide("Inventaire des avis et registre non identiques.")
    resultat = []
    for entree in cas:
        code = entree["identifiant"]
        origine = references[code]
        chronologie = {
            "avis": code,
            "date_parution_reference": entree["date_attendue"],
            "empreinte_reponse": origine["sha256_reponse_http"],
            "avis_anterieurs": [],
            "nature_documentaire": None,
            "contrats": [],
            "resultats_par_lot": [],
            "execution_observee": False,
            "contribution_utile_observee": False,
            "deficit_competences_etabli": False,
        }
        if origine["etat_observation"] == "notice_retrouvee_et_identifiee":
            brut = json.loads((captures / origine["fichier_reponse"]).read_bytes())
            notice = brut["results"][0]
            chronologie["nature_documentaire"] = notice.get("nature")
            liens = notice.get("annonce_lie") or []
            if not isinstance(liens, list) or any(not isinstance(x, str) for x in liens):
                raise ChronologieInvalide("Références d'avis liés invalides.")
            chronologie["avis_anterieurs"] = liens
            if notice.get("nature") == "ATTRIBUTION":
                chronologie.update(analyser_attribution(notice))
        resultat.append(chronologie)
    return {
        "version": VERSION,
        "capture_observee_le": original["observe_le"],
        "nombre_cas": len(resultat),
        "lots_attribues": sum(
            x["statut_lot"] == "attribue" for r in resultat for x in r["resultats_par_lot"]
        ),
        "lots_non_attribues": sum(
            x["statut_lot"] == "non_attribue" for r in resultat for x in r["resultats_par_lot"]
        ),
        "cas": resultat,
        "delais_besoin_vers_contribution_mesurables": 0,
        "avertissement": (
            "Une date d'attribution n'est ni une date d'entrée en vigueur "
            "ni une date de livraison. Les dates de première contribution "
            "utile et les causes de déficit de compétence restent inconnues."
        ),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--captures", type=Path, required=True)
    p.add_argument("--registre", type=Path,
                   default=Path("evaluation/cas_pilotes_boamp_v1.json"))
    p.add_argument("--sortie", type=Path, required=True)
    args = p.parse_args()
    try:
        rapport = produire(args.captures, args.registre)
        ecrire(rapport, args.sortie)
        print(json.dumps({
            "cas": rapport["nombre_cas"],
            "lots_attribues": rapport["lots_attribues"],
            "lots_non_attribues": rapport["lots_non_attribues"],
            "delais_utiles": rapport["delais_besoin_vers_contribution_mesurables"],
        }, ensure_ascii=False))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        p.exit(1, f"Chronologie documentaire interrompue : {exc}\n")


if __name__ == "__main__":
    main()
