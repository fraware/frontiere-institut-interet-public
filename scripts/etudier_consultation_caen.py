"""Reconstituer la consultation initiale du marché radar de Caen.

Ne relie deux notices que par identité interne, acheteur et chronologie
concordants. L'avis initial et le résultat final sont conservés séparément.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path

try:
    from scripts.collecter_notices_pilotes_boamp import adresse, obtenir_octets, qualifier, verifier_capture
    from scripts.capturer_avis_amont_boamp import normaliser
    from scripts.qualifier_captures_notices_boamp import ecrire
except ModuleNotFoundError:
    from collecter_notices_pilotes_boamp import adresse, obtenir_octets, qualifier, verifier_capture
    from capturer_avis_amont_boamp import normaliser
    from qualifier_captures_notices_boamp import ecrire

INITIAL = "25-67330"
ATTRIBUTION = "26-30147"
DATE_INITIAL = "2025-06-18"
VERSION = "consultation-caen-radar-v1"


class ConsultationInvalide(ValueError):
    """Identification, provenance ou structure non conforme."""


def texte(obj):
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict) and isinstance(obj.get("#text"), str):
        return obj["#text"]
    return None


def chemin(obj, *cles):
    for cle in cles:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(cle)
    return obj


def une_liste(obj):
    if obj is None:
        return []
    if isinstance(obj, dict):
        return [obj]
    if isinstance(obj, list) and all(isinstance(i, dict) for i in obj):
        return obj
    raise ConsultationInvalide("Structure du lot incorrecte.")


def informations(notice):
    if not isinstance(notice.get("donnees"), str):
        raise ConsultationInvalide("Document eForms complet absent.")
    racine = json.loads(notice["donnees"])
    eforms = racine.get("EFORMS")
    if not isinstance(eforms, dict):
        raise ConsultationInvalide("Document eForms absent.")
    if len(eforms) != 1:
        raise ConsultationInvalide("Nombre de racines eForms inattendu.")
    genre, corps = next(iter(eforms.items()))
    if genre not in ("ContractNotice", "ContractAwardNotice") or not isinstance(corps, dict):
        raise ConsultationInvalide("Nature du document eForms incompatible.")
    projet = chemin(corps, "cac:ProcurementProject")
    identifiant = normaliser(texte(projet.get("cbc:ID"))) if isinstance(projet, dict) else None
    if not identifiant:
        raise ConsultationInvalide("Référence interne du marché absente.")
    return {"genre": genre, "corps": corps, "identifiant": identifiant,
            "procedure": texte(corps.get("cbc:ContractFolderID"))}


def champs_selectifs(obj, chemin_source=""):
    """Champs publiés utiles à l'examen du calendrier et du prix.

    Aucune conversion ne crée une date, un montant ni un score absent.
    """
    noms = {
        "cbc:EndDate", "cbc:EndTime", "cbc:StartDate",
        "cbc:DurationMeasure", "cbc:EstimatedOverallContractAmount",
        "cbc:MaximumValueAmount", "cbc:MinimumValueAmount",
        "cbc:CalculationExpression", "cbc:Description",
        "cbc:RequiredFinancialGuarantee", "cbc:ParticipationPercent",
    }
    donnees = []
    if isinstance(obj, dict):
        for cle, valeur in obj.items():
            origine = chemin_source + "/" + cle.replace("~", "~0").replace("/", "~1")
            if cle in noms:
                x = texte(valeur)
                if x is not None and x.strip():
                    donnees.append({"chemin_source": origine, "champ": cle, "valeur": x})
            donnees.extend(champs_selectifs(valeur, origine))
    elif isinstance(obj, list):
        for index, valeur in enumerate(obj):
            donnees.extend(champs_selectifs(valeur, chemin_source + "/" + str(index)))
    return donnees


def analyser(initial, attribution):
    if initial.get("idweb") != INITIAL or attribution.get("idweb") != ATTRIBUTION:
        raise ConsultationInvalide("Identifiants de publication incompatibles.")
    if initial.get("dateparution") != DATE_INITIAL:
        raise ConsultationInvalide("Date officielle initiale différente du registre.")
    informations_initial = informations(initial)
    informations_fin = informations(attribution)
    if informations_initial["genre"] != "ContractNotice" or informations_fin["genre"] != "ContractAwardNotice":
        raise ConsultationInvalide("Formulaires initiaux et d'attribution inversés.")
    if informations_initial["identifiant"] != informations_fin["identifiant"]:
        raise ConsultationInvalide("Référence interne de marché contradictoire.")
    if normaliser(initial.get("nomacheteur")) != normaliser(attribution.get("nomacheteur")):
        raise ConsultationInvalide("Acheteurs incompatibles.")
    if date.fromisoformat(initial["dateparution"]) >= date.fromisoformat(attribution["dateparution"]):
        raise ConsultationInvalide("Chronologie de publication invalide.")
    corps = informations_initial["corps"]
    lots = []
    vus = set()
    for index, lot in enumerate(une_liste(corps.get("cac:ProcurementProjectLot"))):
        numero = texte(lot.get("cbc:ID"))
        if numero in vus or not numero:
            raise ConsultationInvalide("Numéros de lot invalides ou dupliqués.")
        vus.add(numero)
        projet = lot.get("cac:ProcurementProject", {})
        lots.append({
            "numero": numero,
            "intitule": texte(projet.get("cbc:Name")) if isinstance(projet, dict) else None,
            "champs_publies": champs_selectifs(lot, f"/EFORMS/ContractNotice/cac:ProcurementProjectLot"
                                              + (f"/{index}" if isinstance(corps["cac:ProcurementProjectLot"], list) else "")),
            "cahier_des_charges_integral_obtenu": False,
            "budget_propre_au_lot_etabli": False,
            "raison_de_non_reponse_etablie": False,
        })
    if {x["numero"] for x in lots} != {"LOT-0001", "LOT-0002"}:
        raise ConsultationInvalide("Lots initialement publiés non identiques aux deux attendus.")
    return {
        "version": VERSION, "avis_initial": INITIAL, "avis_attribution": ATTRIBUTION,
        "publication_initiale": initial["dateparution"],
        "publication_attribution": attribution["dateparution"],
        "identifiant_interne_commun": informations_initial["identifiant"],
        "identifiant_procedure_initiale": informations_initial["procedure"],
        "identifiant_procedure_attribution": informations_fin["procedure"],
        "meme_identifiant_procedure": (
            informations_initial["procedure"] == informations_fin["procedure"]
            if informations_initial["procedure"] and informations_fin["procedure"] else None
        ),
        "date_limite_reponse_annonce": initial.get("datelimitereponse"),
        "champs_calendrier_ensemble": champs_selectifs(
            corps.get("cac:TenderingProcess"),
            "/EFORMS/ContractNotice/cac:TenderingProcess",
        ),
        "lots": lots, "nombre_lots": len(lots),
        "preuve_republication_du_lot_2": False,
        "mise_en_oeuvre_ou_premiere_contribution_etablie": False,
        "interpretation": (
            "Les critères et dates sont ceux publiés dans l'avis initial, pas ceux "
            "d'un cahier des charges intégral. La même référence interne n'atteste "
            "pas à elle seule la réception d'une prestation."
        ),
    }


def produire(captures: Path, sortie: Path, obtenir=obtenir_octets):
    verification = verifier_capture(captures)
    fiche = next((x for x in verification["cas"] if x["identifiant"] == ATTRIBUTION), None)
    if fiche is None or fiche["etat_observation"] != "notice_retrouvee_et_identifiee":
        raise ConsultationInvalide("Avis d'attribution vérifié manquant.")
    brut_attr = (captures / fiche["fichier_reponse"]).read_bytes()
    attribution = json.loads(brut_attr)["results"][0]
    brut = obtenir(adresse(INITIAL))
    etat = qualifier(brut, INITIAL, DATE_INITIAL)
    if etat["etat_observation"] != "notice_retrouvee_et_identifiee":
        raise ConsultationInvalide("Avis initial non retrouvé au relevé.")
    initial = json.loads(brut)["results"][0]
    resultat = analyser(initial, attribution)
    resultat.update({
        "source_officielle_initiale": adresse(INITIAL),
        "sha256_reponse_initiale": hashlib.sha256(brut).hexdigest(),
        "sha256_reponse_attribution": hashlib.sha256(brut_attr).hexdigest(),
        "nombre_octets_initial": len(brut),
        "capture_effectuee_le": datetime.now(timezone.utc).isoformat(),
        "document_initial_capture": INITIAL + ".json",
    })
    if sortie.exists() or sortie.is_symlink():
        raise ConsultationInvalide("Dossier de sortie existant.")
    sortie.mkdir(parents=True)
    try:
        (sortie / (INITIAL + ".json")).write_bytes(brut)
        ecrire(resultat, sortie / "chronologie-consultation.json")
    except Exception:
        (sortie / (INITIAL + ".json")).unlink(missing_ok=True)
        (sortie / "chronologie-consultation.json").unlink(missing_ok=True)
        sortie.rmdir()
        raise
    return resultat


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--captures", type=Path, required=True)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args()
    try:
        rapport = produire(a.captures, a.sortie)
        print(json.dumps({
            "avis_initial": rapport["avis_initial"], "date": rapport["publication_initiale"],
            "lots": rapport["nombre_lots"], "procedure_identique": rapport["meme_identifiant_procedure"],
        }, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as erreur:
        p.exit(1, f"Consultation initiale Caen non validée : {erreur}\n")


if __name__ == "__main__":
    main()
