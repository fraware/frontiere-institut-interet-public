"""Reconstituer les liens documentaires de 17 avis BOAMP et 16 établissements.

Entrées : l'archive officielle des 36 avis, son audit d'identités, et les
16 réponses administratives archivées. Aucune consultation réseau.
Les références CON-0001 et LOT-0001 ne valent que dans leur avis d'origine.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unicodedata

try:
    from scripts.auditer_identifiants_acheteurs_independants_boamp import auditer
    from scripts.extraire_references_boamp_decp import (
        chemin, elements, identite, identifiant_acheteur_14_non_qualifie,
    )
    from scripts.reconstituer_chronologies_pilotes_boamp import analyser_attribution
    from scripts.rapprocher_references_decp_boamp import lire_marches, reference_normalisee
    from scripts.verifier_identifiants_acheteurs_api_entreprises import (
        VERSION as VERSION_ADMIN, adresse as adresse_administrative,
        classer_reponse,
    )
except ModuleNotFoundError as exc:
    if exc.name != "scripts":
        raise
    from auditer_identifiants_acheteurs_independants_boamp import auditer
    from extraire_references_boamp_decp import (
        chemin, elements, identite, identifiant_acheteur_14_non_qualifie,
    )
    from reconstituer_chronologies_pilotes_boamp import analyser_attribution
    from rapprocher_references_decp_boamp import lire_marches, reference_normalisee
    from verifier_identifiants_acheteurs_api_entreprises import (
        VERSION as VERSION_ADMIN, adresse as adresse_administrative,
        classer_reponse,
    )

VERSION = "chaines-documentaires-acheteurs-17-avis-v1"
EMPREINTE = re.compile(r"[0-9a-f]{64}")
REFERENCE_COMPARABLE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{5,99}")



class ChaineInvalide(ValueError):
    """Une relation ou une provenance n'est pas démontrable par la source."""


def sha256(octets: bytes) -> str:
    return hashlib.sha256(octets).hexdigest()


def texte(obj: object) -> str | None:
    """Ne lire que les identifiants explicitement textuels."""
    val = identite(obj)
    return val[0] if val is not None else None


def nom_normalise(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).casefold()
    return " ".join(s.split())


def organisations_acheteur(racine: dict, siret: str) -> dict:
    """Localiser la compagnie rattachée à ContractingParty, sans fournisseur."""
    contractants = elements(racine.get("cac:ContractingParty"))
    if len(contractants) != 1:
        raise ChaineInvalide("Acheteur absent ou multiple")
    partie = chemin(contractants[0], "cac:Party")
    role = texte(chemin(partie, "cac:PartyIdentification", "cbc:ID"))
    organisations = chemin(
        racine, "ext:UBLExtensions", "ext:UBLExtension",
        "ext:ExtensionContent", "efext:EformsExtension",
        "efac:Organizations", "efac:Organization",
    )
    candidates = []
    for indice, org in enumerate(elements(organisations)):
        company = org.get("efac:Company")
        if not isinstance(company, dict):
            continue
        id_org = texte(chemin(company, "cac:PartyIdentification", "cbc:ID"))
        siret_org = texte(chemin(company, "cac:PartyLegalEntity", "cbc:CompanyID"))
        if role is not None and id_org == role and siret_org == siret:
            if (not isinstance(chemin(company, "cac:PartyLegalEntity", "cbc:CompanyID"), str)
                    and set(chemin(company, "cac:PartyLegalEntity", "cbc:CompanyID")) != {"#text"}):
                raise ChaineInvalide("Schéma de SIRET implicite contradictoire")
            nom = texte(chemin(company, "cac:PartyName", "cbc:Name"))
            candidates.append({
                "identifiant_organisation_dans_avis": role,
                "nom_organisation_dans_avis": nom,
                "index_organisation": indice,
            })
    if len(candidates) != 1:
        raise ChaineInvalide("Lien officiel acheteur-organisation ambigu")
    return candidates[0]


def declarations_lots(racine: dict) -> list[str]:
    lots = elements(racine.get("cac:ProcurementProjectLot"))
    identifiants = []
    for lot in lots:
        code = texte(lot.get("cbc:ID"))
        if not code or len(code) > 120 or code in identifiants:
            raise ChaineInvalide("Identifiant de lot absent, trop long ou répété")
        identifiants.append(code)
    return identifiants


def attributs_attribution(notice: dict, codes_lots: list[str]) -> dict:
    """Rattacher contrats et lots à l'intérieur de ce seul avis."""
    analyse = analyser_attribution(notice)
    contrats = analyse["contrats"]
    formulaires = json.loads(notice["donnees"])
    racine = chemin(formulaires, "EFORMS", "ContractAwardNotice")
    details = chemin(
        racine, "ext:UBLExtensions", "ext:UBLExtension",
        "ext:ExtensionContent", "efext:EformsExtension",
        "efac:NoticeResult", "efac:SettledContract",
    )
    documents = elements(details)
    references_documentaires = {}
    for indice, document in enumerate(documents):
        identifiant = texte(document.get("cbc:ID"))
        reference_externe = texte(chemin(
            document, "efac:ContractReference", "cbc:ID",
        ))
        if not identifiant or identifiant in references_documentaires:
            raise ChaineInvalide("Référence contractuelle locale dupliquée")
        references_documentaires[identifiant] = {
            "reference_contrat_declaree": reference_externe,
            "reference_contrat_comparable_decp": (
                bool(REFERENCE_COMPARABLE.fullmatch(reference_externe))
                if isinstance(reference_externe, str) else False
            ),
            "origine_reference_contrat": (
                "/donnees/EFORMS/ContractAwardNotice/ext:UBLExtensions/"
                "ext:UBLExtension/ext:ExtensionContent/efext:EformsExtension/"
                "efac:NoticeResult/efac:SettledContract/"
                + (str(indice) if isinstance(details, list) else "")
                + "/efac:ContractReference/cbc:ID"
                if reference_externe is not None else None
            ),
        }
    if set(references_documentaires) != {x["identifiant_contrat"] for x in contrats}:
        raise ChaineInvalide("Détail de contrat non concordant avec les résultats")
    ids_contrats = [c["identifiant_contrat"] for c in contrats]
    if len(ids_contrats) != len(set(ids_contrats)):
        raise ChaineInvalide("Référence contractuelle ambiguë dans l'avis")
    liens = []
    for lot in analyse["resultats_par_lot"]:
        if lot["identifiant_lot"] not in codes_lots:
            raise ChaineInvalide("Résultat pour un lot non déclaré")
        for contrat in lot["contrats_references"]:
            if contrat not in ids_contrats:
                raise ChaineInvalide("Référence de contrat sans définition dans l'avis")
            liens.append({
                "lot": lot["identifiant_lot"],
                "reference_contrat_locale": contrat,
                "lien_dans_meme_avis": True,
                "identite_contrat_decp_etablie": False,
            })
    return {
        "contrats_locaux": [{
            "reference_locale": c["identifiant_contrat"],
            "date_decision_attribution_declaree": c["date_attribution_declaree"],
            "date_emission_contrat_declaree": c["date_emission_contrat_declaree"],
            **references_documentaires[c["identifiant_contrat"]],
            "debut_execution_observe": False,
        } for c in contrats],
        "resultats_lots": [{
            "lot": l["identifiant_lot"],
            "statut": l["statut_lot"],
            "motif": l["motif_officiel"],
        } for l in analyse["resultats_par_lot"]],
        "relations_lot_contrat_dans_avis": liens,
    }


def produire(tirage: Path, releve: Path, audit_path: Path, administration: Path) -> dict:
    """Revérifier trois sources documentaires et produire les 17 chaînes."""
    audit_brut = audit_path.read_bytes()
    audit = json.loads(audit_brut)
    if audit != auditer(tirage, releve):
        raise ChaineInvalide("Audit BOAMP différent du recalcul des réponses primaires")
    admin_path = administration / "rapport.json"
    rapport_admin_brut = admin_path.read_bytes()
    rapport = json.loads(rapport_admin_brut)
    if (rapport.get("version") != VERSION_ADMIN
            or rapport.get("source_audit_boamp_sha256") != sha256(audit_brut)
            or rapport.get("nombre_identifiants_distincts") != 16
            or rapport.get("nombre_occurrences_identifiants") != 17
            or rapport.get("nombre_reponses_officielles_archivees") != 16):
        raise ChaineInvalide("Rapport administratif sans lien vérifiable avec BOAMP")
    fiches_admin = {}
    for source in rapport.get("identifiants", []):
        numero = source.get("identifiant_candidat")
        if not isinstance(numero, str) or not re.fullmatch(r"[0-9]{14}", numero):
            raise ChaineInvalide("Numéro administratif non conforme")
        if numero in fiches_admin:
            raise ChaineInvalide("Numéro administratif dupliqué")
        fichier = administration / (numero + ".json")
        if fichier.is_symlink() or not fichier.is_file():
            raise ChaineInvalide("Réponse administrative indisponible")
        octets = fichier.read_bytes()
        if (source.get("source_api") != adresse_administrative(numero)
                or source.get("fichier_reponse") != fichier.name
                or source.get("octets_reponse") != len(octets)
                or source.get("sha256_reponse") != sha256(octets)):
            raise ChaineInvalide("Réponse administrative ou provenance altérée")
        nouveau = classer_reponse(numero, octets)
        if any(source.get(k) != v for k, v in nouveau.items()):
            raise ChaineInvalide("Qualification de la réponse administrative altérée")
        fiches_admin[numero] = source
    if len(fiches_admin) != 16:
        raise ChaineInvalide("Inventaire administratif incomplet")
    dossiers = []
    compte = Counter()
    numeros_utilises = set()
    for fiche in audit["avis"]:
        if fiche["statut_identite"] != "identifiant_14_chiffres_sans_schema":
            continue
        numero = fiche["identite_acheteur"]
        if numero not in fiches_admin:
            raise ChaineInvalide("Établissement absent du contrôle administratif")
        numero_avis = fiche["avis"]
        fichier = releve / (numero_avis + ".json")
        octets = fichier.read_bytes()
        if fiche["sha256_reponse_http"] != sha256(octets):
            raise ChaineInvalide("Empreinte BOAMP différente de l'audit")
        enveloppe = json.loads(octets)
        notices = enveloppe.get("results", [])
        if len(notices) != 1 or notices[0].get("idweb") != numero_avis:
            raise ChaineInvalide("Identité d'avis BOAMP ambiguë")
        notice = notices[0]
        controle = identifiant_acheteur_14_non_qualifie(notice)
        if (controle is None or controle["identifiant_14_chiffres"] != numero
                or controle["chemin_preuve"] != fiche["champ_identite"]):
            raise ChaineInvalide("Lien entre l'acheteur et le SIRET non reproductible")
        data = json.loads(notice.get("donnees") or "null")
        if not isinstance(data, dict) or not isinstance(data.get("EFORMS"), dict):
            raise ChaineInvalide("Formulaire eForms attendu absent")
        formes = data["EFORMS"]
        if len(formes) != 1:
            raise ChaineInvalide("Plusieurs formulaires eForms")
        _, racine = next(iter(formes.items()))
        if not isinstance(racine, dict):
            raise ChaineInvalide("Formulaire illisible")
        org = organisations_acheteur(racine, numero)
        projet = texte(chemin(racine, "cac:ProcurementProject", "cbc:ID"))
        lots = declarations_lots(racine)
        nature = notice.get("nature")
        if nature not in {"APPEL_OFFRE", "ATTRIBUTION"}:
            raise ChaineInvalide("Nature de l'avis non étudiée")
        attribution = (
            attributs_attribution(notice, lots) if nature == "ATTRIBUTION"
            else {"contrats_locaux": [], "resultats_lots": [],
                  "relations_lot_contrat_dans_avis": []}
        )
        admin = fiches_admin[numero]
        admin_occurrence = [
            x for x in admin["avis_boamp"]
            if x.get("avis") == numero_avis
            and x.get("sha256_reponse_boamp") == fiche["sha256_reponse_http"]
            and x.get("champ_preuve_boamp") == fiche["champ_identite"]
        ]
        if len(admin_occurrence) != 1:
            raise ChaineInvalide("Lien entre archive BOAMP et réponse administrative absent")
        libelle = notice.get("nomacheteur")
        if not isinstance(libelle, str):
            raise ChaineInvalide("Dénomination acheteur absente")
        intitule_admin = admin.get("denomination_publique")
        if not isinstance(intitule_admin, str):
            raise ChaineInvalide("Dénomination administrative absente")
        chaines = {
            "avis_boamp": numero_avis,
            "empreinte_avis_boamp": sha256(octets),
            "date_parution": notice["dateparution"],
            "nature_avis": nature,
            "acheteur_libelle_boamp": libelle,
            "acheteur_organisation_boamp": org,
            "siret_chiffres_sans_schema_boamp": numero,
            "preuve_siret_dans_boamp": controle["chemin_preuve"],
            "denomination_unite_legale_api": intitule_admin,
            "preuve_etablissement_exact_api": admin["chemin_siret"],
            "sha256_reponse_api": admin["sha256_reponse"],
            "presence_etablissement_exact_api": admin["siret_exact_dans_etablissement"],
            "libelles_identiques_apres_normalisation_minimale": (
                nom_normalise(libelle) == nom_normalise(intitule_admin)
            ),
            "reference_procedure_interne": projet,
            "chemin_reference_procedure": (
                "/donnees/EFORMS/*/cac:ProcurementProject/cbc:ID"
                if projet is not None else None
            ),
            "reference_dossier_avis": texte(racine.get("cbc:ContractFolderID")),
            "lots_declares_dans_avis": lots,
            **attribution,
            "role_contractant_juridiquement_confirme": False,
            "identite_contrat_decp_etablie": False,
            "premiere_contribution_utile_observee": False,
        }
        dossiers.append(chaines)
        numeros_utilises.add(numero)
        compte["avis"] += 1
        compte["attributions"] += nature == "ATTRIBUTION"
        compte["references_procedure"] += projet is not None
        compte["lots_declares"] += len(lots)
        compte["resultats_lots"] += len(attribution["resultats_lots"])
        compte["contrats_locaux"] += len(attribution["contrats_locaux"])
        compte["liens_lot_contrat"] += len(attribution["relations_lot_contrat_dans_avis"])
        compte["denominations_egales_normalisation_stricte"] += (
            chaines["libelles_identiques_apres_normalisation_minimale"]
        )
    if (compte["avis"] != 17 or len(numeros_utilises) != 16
            or set(fiches_admin) != numeros_utilises):
        raise ChaineInvalide("Population documentaire modifiée")
    return {
        "version": VERSION,
        "sha256_audit_boamp": sha256(audit_brut),
        "sha256_rapport_administratif": sha256(rapport_admin_brut),
        "mesures": dict(sorted(compte.items())),
        "nombre_siret_distincts": len(numeros_utilises),
        "liaisons_contractuelles_decp_prouvees": 0,
        "validations_juridiques_du_role_acheteur": 0,
        "preuves_execution": 0,
        "dossiers": dossiers,
        "avertissement": (
            "La déclaration BOAMP et la recherche administrative partagent un "
            "numéro exact d'établissement ; la dénomination et le rôle juridique "
            "de chaque acheteur demandent un contrôle spécifique. Les références "
            "de lot et de contrat n'ont de portée démontrée qu'au sein de l'avis. "
            "Aucun identifiant de contrat DECP ni délai de contribution n'est établi."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tirage", type=Path, required=True)
    parser.add_argument("--releve", type=Path, required=True)
    parser.add_argument("--audit-boamp", type=Path, required=True)
    parser.add_argument("--administration", type=Path, required=True)
    parser.add_argument("--sortie", type=Path, required=True)
    args = parser.parse_args()
    try:
        rapport = produire(
            args.tirage, args.releve, args.audit_boamp, args.administration
        )
        if args.sortie.exists() or args.sortie.is_symlink():
            raise ChaineInvalide("Refus d'écraser un rapport précédent")
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        args.sortie.write_text(
            json.dumps(rapport, ensure_ascii=False, sort_keys=True,
                       indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "avis": rapport["mesures"]["avis"],
            "attributions": rapport["mesures"]["attributions"],
            "lots": rapport["mesures"]["lots_declares"],
            "liens_lot_contrat": rapport["mesures"]["liens_lot_contrat"],
            "relations_decp_prouvees": 0,
        }, ensure_ascii=False))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f"Reconstitution refusée : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
