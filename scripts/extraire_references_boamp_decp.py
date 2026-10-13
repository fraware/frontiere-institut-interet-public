"""Extraire, depuis des captures BOAMP vérifiées, les seules clés DECP explicites.

Le rapprochement d'une référence interne de projet et d'un SIRET d'acheteur
constitue une piste documentaire, jamais une identité de contrat démontrée.
L'extraction est fermée aux structures eForms dont les rôles sont vérifiables.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

try:
    from scripts.collecter_notices_pilotes_boamp import verifier_capture
except ModuleNotFoundError:
    from collecter_notices_pilotes_boamp import verifier_capture

VERSION = "references-boamp-decp-v1"
SIRET = re.compile(r"[0-9]{14}")
SCHEMES = {"SIRET", "FR-SIRET", "FR:SIRET", "FR_SIRET"}
IDENTIFIANT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,99}")


class ExtractionInvalide(ValueError):
    """Source officielle, rôle d'organisation ou identité inutilisable."""


def chemin(obj: object, *cles: str) -> object:
    """Lire une suite explicite de clés, sans recherche textuelle globale."""
    for cle in cles:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(cle)
    return obj


def elements(obj: object) -> list[dict]:
    """Accepter la cardinalité objet/liste des convertisseurs XML vers JSON."""
    if obj is None:
        return []
    if isinstance(obj, dict):
        return [obj]
    if isinstance(obj, list) and all(isinstance(x, dict) for x in obj):
        return obj
    raise ExtractionInvalide("Cardinalité documentaire non prise en charge")


def identite(obj: object) -> tuple[str, str | None] | None:
    """Restituer la valeur et son schéma sans convertir un identifiant de rôle."""
    if isinstance(obj, str):
        return (obj, None) if obj.strip() == obj and obj else None
    if isinstance(obj, dict):
        texte = obj.get("#text")
        if not isinstance(texte, str) or not texte or texte != texte.strip():
            return None
        schema = obj.get("@schemeID", obj.get("@schemeName"))
        if schema is not None and not isinstance(schema, str):
            return None
        return texte, schema
    return None


def siret_qualifie(obj: object) -> str | None:
    """Reconnaître un SIRET déclaré comme tel, jamais un entier isolé."""
    valeur = identite(obj)
    if valeur is None:
        return None
    texte, schema = valeur
    if schema is None or schema.upper() not in SCHEMES:
        return None
    return texte if SIRET.fullmatch(texte) else None


def repertoire_organisations(racine: dict) -> list[tuple[str, str, str]]:
    """Associer les organisations de l'extension à leur identité déclarée."""
    ext = chemin(
        racine, "ext:UBLExtensions", "ext:UBLExtension",
        "ext:ExtensionContent", "efext:EformsExtension",
        "efac:Organizations", "efac:Organization",
    )
    organisations = []
    for indice, organisation in enumerate(elements(ext)):
        company = chemin(organisation, "efac:Company")
        if not isinstance(company, dict):
            continue
        id_org = identite(chemin(
            company, "cac:PartyIdentification", "cbc:ID",
        ))
        siret = siret_qualifie(chemin(
            company, "cac:PartyLegalEntity", "cbc:CompanyID",
        ))
        if id_org is None or siret is None:
            continue
        origine = (
            "/ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/"
            "efext:EformsExtension/efac:Organizations/efac:Organization"
        )
        if isinstance(ext, list):
            origine += f"/{indice}"
        organisations.append((
            id_org[0], siret,
            origine + "/efac:Company/cac:PartyLegalEntity/cbc:CompanyID",
        ))
    return organisations


def references_notice(notice: dict) -> tuple[list[dict], str]:
    """Identifier strictement l'acheteur de la procédure eForms.

    Aucune identité n'est inférée de nom, de titre, de titulaire ou d'un nombre
    trouvé ailleurs dans le formulaire. Une pluralité de parties bloque le lien.
    """
    brut = notice.get("donnees")
    if not isinstance(brut, str) or len(brut) > 5_000_000:
        return [], "formulaire_absent_ou_invalide"
    try:
        structure = json.loads(brut)
    except json.JSONDecodeError:
        return [], "formulaire_absent_ou_invalide"
    eforms = structure.get("EFORMS") if isinstance(structure, dict) else None
    if not isinstance(eforms, dict) or len(eforms) != 1:
        return [], "format_non_pris_en_charge"
    nom_formulaire, racine = next(iter(eforms.items()))
    if not isinstance(racine, dict) or not isinstance(nom_formulaire, str):
        return [], "structure_eforms_incorrecte"
    projet = identite(chemin(racine, "cac:ProcurementProject", "cbc:ID"))
    if projet is None or not IDENTIFIANT.fullmatch(projet[0]):
        return [], "reference_projet_absente_ou_ambigue"

    contractants = elements(racine.get("cac:ContractingParty"))
    if len(contractants) != 1:
        return [], "acheteurs_multiples_ou_absents"
    partie = chemin(contractants[0], "cac:Party")
    if not isinstance(partie, dict):
        return [], "identite_acheteur_absente"

    # Le rôle acheteur est défini par ContractingParty, pas par la présence
    # d'un numéro français dans les organisations ou parmi les titulaires.
    prefixe = f"/results/0/donnees/EFORMS/{nom_formulaire}"
    origine_acheteur = prefixe + "/cac:ContractingParty/cac:Party"
    direct = siret_qualifie(chemin(
        partie, "cac:PartyLegalEntity", "cbc:CompanyID",
    ))
    if direct is not None:
        siret, preuve = direct, (
            origine_acheteur + "/cac:PartyLegalEntity/cbc:CompanyID"
        )
    else:
        identifiant_acheteur = identite(chemin(
            partie, "cac:PartyIdentification", "cbc:ID",
        ))
        if identifiant_acheteur is None:
            return [], "organisation_acheteuse_non_identifiable"
        # Cas où le SIRET est déclaré directement sur PartyIdentification.
        siret = siret_qualifie(chemin(
            partie, "cac:PartyIdentification", "cbc:ID",
        ))
        if siret is not None:
            preuve = origine_acheteur + "/cac:PartyIdentification/cbc:ID"
        else:
            correspondances = [
                (numero, origine)
                for org, numero, origine in repertoire_organisations(racine)
                if org == identifiant_acheteur[0]
            ]
            if len(correspondances) != 1:
                return [], "rattachement_organisation_non_univoque"
            siret, preuve_locale = correspondances[0]
            preuve = prefixe + preuve_locale

    chemin_projet = prefixe + "/cac:ProcurementProject/cbc:ID"
    return [{
        "acheteur_siret": siret,
        "id_marche": projet[0],
        "chemin_preuve": chemin_projet,
        "chemin_preuve_siret": preuve,
        "type_reference": "identifiant_interne_projet_eforms",
        "identite_contrat_etablie": False,
    }], "reference_couple_explicitement_extraite"


def produire(captures: Path) -> dict:
    """Revalider les octets officiels, puis qualifier chaque avis séparément."""
    rapport = verifier_capture(captures)
    resultats, exclusions = [], []
    for fiche in rapport["cas"]:
        code = fiche["identifiant"]
        if fiche["etat_observation"] != "notice_retrouvee_et_identifiee":
            exclusions.append({"id_boamp": code, "raison": "avis_non_retrouve"})
            continue
        path = captures / fiche["fichier_reponse"]
        octets = path.read_bytes()
        if hashlib.sha256(octets).hexdigest() != fiche["sha256_reponse_http"]:
            raise ExtractionInvalide("Capture modifiée depuis sa vérification")
        donnees = json.loads(octets)
        if (donnees.get("total_count") != 1 or
                donnees["results"][0].get("idweb") != code):
            raise ExtractionInvalide("Réponse officielle ambiguë")
        refs, statut = references_notice(donnees["results"][0])
        if not refs:
            exclusions.append({"id_boamp": code, "raison": statut,
                               "sha256_reponse_http": fiche["sha256_reponse_http"]})
            continue
        resultats.append({
            "id_boamp": code,
            "url_source": fiche["source_officielle_interrogee"],
            "sha256_reponse_http": fiche["sha256_reponse_http"],
            "references": refs,
            "controle_emp_reponse_officielle": True,
            "continuite_juridique_etablie": False,
        })
    return {
        "version": VERSION,
        "avis": resultats,
        "exclusions": exclusions,
        "nombre_avis_controles": rapport["nombre_cas"],
        "identites_contractuelles_juridiques_etablies": 0,
        "preuve_references": "octets_et_chemins_controles_sans_filiation_juridique",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--sortie", type=Path, required=True)
    args = parser.parse_args()
    try:
        resultat = produire(args.captures)
        if args.sortie.exists() or args.sortie.is_symlink():
            raise ExtractionInvalide("Refus d'écraser le relevé existant")
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        args.sortie.write_text(
            json.dumps(resultat, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "avis": resultat["nombre_avis_controles"],
            "references": len(resultat["avis"]),
            "exclusions": len(resultat["exclusions"]),
        }, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Extraction BOAMP refusée : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
