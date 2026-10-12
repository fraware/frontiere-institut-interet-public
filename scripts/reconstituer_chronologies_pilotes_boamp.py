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

VERSION = "chronologie-documentaire-pilotes-v2"
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



def lire_statistiques_soumissions(resultat: dict, origine_lot: str) -> list[dict]:
    """Conserver l'effectif et le type exact des soumissions déclarées.

    Le code t-esubm concerne les seules soumissions électroniques. Le code
    tenders a une autre portée : ces deux dénominateurs ne sont pas sommés.
    """
    valeurs = elements(resultat.get("efac:ReceivedSubmissionsStatistics"))
    observations, codes = [], {}
    for indice, statistique in enumerate(valeurs):
        code = identite(chemin(statistique, [
            "efbc:StatisticsCode", "#text",
        ]))
        nombre = statistique.get("efbc:StatisticsNumeric")
        if type(nombre) is int:
            total = nombre
        elif isinstance(nombre, str) and nombre.isascii() and nombre.isdecimal():
            total = int(nombre)
        else:
            raise ChronologieInvalide("Effectif de soumissions non entier ou absent.")
        if total < 0:
            raise ChronologieInvalide("Effectif de soumissions négatif.")
        origine_statistique = origine_lot + "/efac:ReceivedSubmissionsStatistics" + (
            f"/{indice}" if isinstance(resultat.get("efac:ReceivedSubmissionsStatistics"), list)
            else ""
        )
        origine_effectif = origine_statistique + "/efbc:StatisticsNumeric"
        origine_code = origine_statistique + "/efbc:StatisticsCode/#text"
        if code in codes:
            precedente = observations[codes[code]]
            if precedente["effectif_declare"] != total:
                raise ChronologieInvalide(
                    "Statistiques contradictoires pour le même code officiel."
                )
            precedente.setdefault("occurrences_identiques", []).append({
                "origine_effectif": origine_effectif, "origine_code": origine_code,
            })
            continue
        codes[code] = len(observations)
        observations.append({
            "code_statistique_officiel": code,
            "effectif_declare": total,
            "portee_de_la_mesure": (
                "soumissions_electroniques" if code == "t-esubm" else
                "soumissions_tous_canaux_declares" if code == "tenders"
                else "code_non_interprete"
            ),
            "origine_effectif": origine_effectif,
            "origine_code": origine_code,
        })
    return observations



def qualifier_effectifs_soumissions(statistiques: list[dict]) -> dict:
    """Séparer absence totale d'offres, absence électronique et inconnue.

    'tenders' compte les offres reçues ; 't-esubm' ne renseigne que le
    canal électronique. Le motif légal de non-attribution est une autre
    variable et ne doit jamais être déduit de ces compteurs.
    """
    mesures = {x["code_statistique_officiel"]: x for x in statistiques}
    total = mesures.get("tenders")
    electronique = mesures.get("t-esubm")
    if total and electronique and electronique["effectif_declare"] > total["effectif_declare"]:
        raise ChronologieInvalide(
            "Plus de soumissions électroniques que de soumissions totales."
        )
    if total:
        categorie = (
            "zero_offre_totale_declaree" if total["effectif_declare"] == 0
            else "offres_totales_positives"
        )
        observation = total
    elif electronique:
        categorie = (
            "zero_soumission_electronique_total_inconnu"
            if electronique["effectif_declare"] == 0
            else "soumissions_electroniques_positives_total_inconnu"
        )
        observation = electronique
    else:
        categorie = "effectif_total_inconnu"
        observation = None
    return {
        "qualification_effectif": categorie,
        "effectif_utilise": observation["effectif_declare"] if observation else None,
        "code_mesure_utilise": observation["code_statistique_officiel"] if observation else None,
        "origine_effectif": observation["origine_effectif"] if observation else None,
        "motif_officiel_non_deduit_des_effectifs": True,
    }

def regrouper_resultats_par_lot(resultats: list[dict]) -> list[dict]:
    """Réunir les décisions compatibles d'un lot sans additionner ses offres.

    Plusieurs contrats peuvent être attribués au même lot. Les différents
    enregistrements 'LotResult' ne constituent pas plusieurs lots.
    """
    groupes: dict[str, dict] = {}
    for resultat in resultats:
        cle = resultat["identifiant_lot"]
        if cle not in groupes:
            groupes[cle] = {
                **resultat,
                "contrats_references": list(resultat["contrats_references"]),
                "statistiques_soumissions": [
                    {**x, "occurrences_identiques": list(x.get("occurrences_identiques", []))}
                    for x in resultat["statistiques_soumissions"]
                ],
                "origines_resultats": [resultat["origine_resultat"]],
                "nombre_decisions_par_lot": 1,
            }
            continue
        ancien = groupes[cle]
        if (ancien["code_resultat_officiel"] != resultat["code_resultat_officiel"]
                or ancien["motif_officiel"] != resultat["motif_officiel"]):
            raise ChronologieInvalide(
                "Plusieurs décisions contradictoires pour le même lot."
            )
        references = resultat["contrats_references"]
        if set(references) & set(ancien["contrats_references"]):
            raise ChronologieInvalide(
                "Référence de contrat répétée entre résultats du même lot."
            )
        ancien["contrats_references"].extend(references)
        ancien["contrat_reference"] = (
            ancien["contrats_references"][0]
            if len(ancien["contrats_references"]) == 1 else None
        )
        mesures = {
            x["code_statistique_officiel"]: x
            for x in ancien["statistiques_soumissions"]
        }
        for entree in resultat["statistiques_soumissions"]:
            code = entree["code_statistique_officiel"]
            if code not in mesures:
                ajout = {**entree, "occurrences_identiques": list(
                    entree.get("occurrences_identiques", [])
                )}
                ancien["statistiques_soumissions"].append(ajout)
                mesures[code] = ajout
                continue
            precedent = mesures[code]
            if precedent["effectif_declare"] != entree["effectif_declare"]:
                raise ChronologieInvalide(
                    "Mesures de soumission contradictoires entre décisions d'un lot."
                )
            precedent["occurrences_identiques"].append({
                "origine_code": entree["origine_code"],
                "origine_effectif": entree["origine_effectif"],
            })
            precedent["occurrences_identiques"].extend(
                entree.get("occurrences_identiques", [])
            )
        ancien["origines_resultats"].append(resultat["origine_resultat"])
        ancien["nombre_decisions_par_lot"] += 1
    return list(groupes.values())

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
        origine_contrat = RACINE + "/efac:SettledContract" + (
            f"/{numero}" if isinstance(ensemble.get("efac:SettledContract"), list) else ""
        )
        contrats.append({
            "identifiant_contrat": code,
            "date_attribution_declaree": attribution,
            "date_emission_contrat_declaree": emission,
            "origine_date_attribution": origine_contrat + "/cbc:AwardDate",
            "origine_date_emission": origine_contrat + "/cbc:IssueDate",
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
        origine_lot = RACINE + "/efac:LotResult" + (
            f"/{numero}" if isinstance(ensemble.get("efac:LotResult"), list) else ""
        )
        soumissions = lire_statistiques_soumissions(resultat, origine_lot)
        if motif == "no-rece" and any(x["effectif_declare"] > 0 for x in soumissions):
            raise ChronologieInvalide(
                "Avis contradictoire : non-attribution sans offre mais statistique positive."
            )
        references_contrats = [
            identite(c.get("cbc:ID"))
            for c in elements(resultat.get("efac:SettledContract"))
        ]
        if len(references_contrats) != len(set(references_contrats)):
            raise ChronologieInvalide("Contrat référencé plusieurs fois pour un même lot.")
        lots.append({
            "identifiant_lot": code_lot,
            "statistiques_soumissions": soumissions,
            "contrats_references": references_contrats,
            "code_resultat_officiel": code,
            "statut_lot": (
                "attribue" if code == "selec-w" else
                "non_attribue" if code == "clos-nw" else "indetermine"
            ),
            "motif_officiel": motif,
            "origine_resultat": origine_lot + "/cbc:TenderResultCode/#text",
            "contrat_reference": (
                references_contrats[0] if len(references_contrats) == 1 else None
            ),
        })
    lots_regroupes = regrouper_resultats_par_lot(lots)
    for lot in lots_regroupes:
        lot["observation_effectifs_soumissions"] = qualifier_effectifs_soumissions(
            lot["statistiques_soumissions"]
        )
    return {
        "contrats": contrats,
        "resultats_par_lot": lots_regroupes,
    }


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
        "lots_avec_motif_absence_offres": sum(
            x["motif_officiel"] == "no-rece"
            for r in resultat for x in r["resultats_par_lot"]
        ),
        "statistiques_par_code": dict(sorted(Counter(
            s["code_statistique_officiel"]
            for r in resultat for lot in r["resultats_par_lot"]
            for s in lot["statistiques_soumissions"]
        ).items())),
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
            "lots_motif_sans_offre": rapport["lots_avec_motif_absence_offres"],
            "codes_soumissions": rapport["statistiques_par_code"],
            "delais_utiles": rapport["delais_besoin_vers_contribution_mesurables"],
        }, ensure_ascii=False))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        p.exit(1, f"Chronologie documentaire interrompue : {exc}\n")


if __name__ == "__main__":
    main()
