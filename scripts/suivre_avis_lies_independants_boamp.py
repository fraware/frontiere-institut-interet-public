"""Vérifier les avis explicitement cités par les 17 notices BOAMP indépendantes.

Les 36 réponses originales sont contrôlées contre leurs empreintes ; seules
les références explicites annonce_lie conduisent à des requêtes supplémentaires.
Un lien annoncé n'établit ni l'identité juridique du marché ni une pénurie.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from urllib.error import HTTPError, URLError
from zipfile import ZipFile, BadZipFile

try:
    from scripts.collecter_notices_pilotes_boamp import adresse, obtenir_octets
    from scripts.rapprocher_references_decp_boamp import reference_normalisee
    from scripts.extraire_references_boamp_decp import identifiant_acheteur_14_non_qualifie
except ModuleNotFoundError as exc:
    if exc.name != "scripts":
        raise
    from collecter_notices_pilotes_boamp import adresse, obtenir_octets
    from rapprocher_references_decp_boamp import reference_normalisee
    from extraire_references_boamp_decp import identifiant_acheteur_14_non_qualifie

VERSION = "suivi-avis-lies-17-boamp-v1"
SOURCE_VERSION = "chaines-documentaires-acheteurs-17-avis-v1"
CODE = re.compile(r"[0-9]{2}-[0-9]{2,8}")
EMP = re.compile(r"[0-9a-f]{64}")
MAX_LIENS = 12
MAX_OCTETS = 5_000_000
RACINE_RELEVE = "releve-issues-36/"


class LiensInvalides(ValueError):
    """Preuve primaire ou rattachement contradictoire."""


def sha(octets: bytes) -> str:
    return hashlib.sha256(octets).hexdigest()


def lire_json(brut: bytes):
    if not isinstance(brut, bytes) or not 0 < len(brut) <= MAX_OCTETS:
        raise LiensInvalides("Réponse absente ou excessive")
    try:
        return json.loads(brut)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LiensInvalides("Réponse non JSON") from exc


def date_jour(valeur: object) -> str:
    if not isinstance(valeur, str) or len(valeur) < 10:
        raise LiensInvalides("Date documentaire absente")
    try:
        jour = date.fromisoformat(valeur[:10])
    except ValueError as exc:
        raise LiensInvalides("Date documentaire invalide") from exc
    if jour.isoformat() != valeur[:10]:
        raise LiensInvalides("Date documentaire non canonique")
    return jour.isoformat()


def projet(notice: dict) -> str | None:
    """Extraire exclusivement l'identifiant du projet dans le formulaire eForms."""
    brut = notice.get("donnees")
    if not isinstance(brut, str):
        return None
    try:
        d = json.loads(brut)
    except json.JSONDecodeError as exc:
        raise LiensInvalides("Formulaire eForms illisible") from exc
    formes = d.get("EFORMS") if isinstance(d, dict) else None
    if not isinstance(formes, dict) or len(formes) != 1:
        return None
    racine = next(iter(formes.values()))
    if not isinstance(racine, dict):
        return None
    affaire = racine.get("cac:ProcurementProject")
    if not isinstance(affaire, dict):
        return None
    ident = affaire.get("cbc:ID")
    if isinstance(ident, dict) and set(ident) <= {"#text", "@schemeName"}:
        ident = ident.get("#text")
    return ident if isinstance(ident, str) and 0 < len(ident) <= 200 else None


def identifiant_acheteur(notice: dict) -> str | None:
    resultat = identifiant_acheteur_14_non_qualifie(notice)
    if resultat is None:
        return None
    return resultat["identifiant_14_chiffres"]


def sources(archive: Path, chaines: Path) -> tuple[list[dict], str]:
    """Ne retenir que des avis rattachés aux octets du tirage indépendant."""
    brut_chaines = chaines.read_bytes()
    rapport = lire_json(brut_chaines)
    if (rapport.get("version") != SOURCE_VERSION
            or len(rapport.get("dossiers", [])) != 17
            or rapport.get("nombre_siret_distincts") != 16):
        raise LiensInvalides("Rapport des 17 avis non conforme")
    origines = rapport["dossiers"]
    with ZipFile(archive) as zipf:
        manifeste = lire_json(zipf.read(RACINE_RELEVE + "rapport.json"))
        fiches = manifeste.get("cas", [])
        if len(fiches) != 36 or len({f["avis"] for f in fiches}) != 36:
            raise LiensInvalides("Manifeste historique des 36 avis incorrect")
        preuves = {f["avis"]: f for f in fiches}
        liens = []
        codes_origines = set()
        references = set()
        for dossier in origines:
            code = dossier.get("avis_boamp")
            if (not isinstance(code, str) or CODE.fullmatch(code) is None
                    or code in codes_origines or code not in preuves):
                raise LiensInvalides("Avis source manquant ou répété")
            codes_origines.add(code)
            fiche = preuves[code]
            octets = zipf.read(RACINE_RELEVE + code + ".json")
            if (sha(octets) != dossier.get("empreinte_avis_boamp")
                    or sha(octets) != fiche.get("sha256_reponse_http")
                    or len(octets) != fiche.get("octets_reponse_http")):
                raise LiensInvalides("Empreinte ou volume primaire BOAMP incompatible")
            resultat = lire_json(octets)
            if (not isinstance(resultat, dict)
                    or resultat.get("total_count") != 1
                    or not isinstance(resultat.get("results"), list)
                    or len(resultat["results"]) != 1):
                raise LiensInvalides("Avis source BOAMP non identifié")
            avis = resultat["results"][0]
            if avis.get("idweb") != code:
                raise LiensInvalides("Identifiant source discordant")
            date_source = date_jour(avis.get("dateparution"))
            avant = avis.get("annonce_lie")
            if avant is None:
                continue
            if not isinstance(avant, list):
                raise LiensInvalides("Références d'avis liées incorrectes")
            for ref in avant:
                if (not isinstance(ref, str) or CODE.fullmatch(ref) is None
                        or ref == code or (code, ref) in references):
                    raise LiensInvalides("Avis antérieur mal référencé")
                references.add((code, ref))
                liens.append({
                    "avis_source": code,
                    "avis_lie": ref,
                    "date_parution_source": date_source,
                    "nature_source": avis.get("nature"),
                    "empreinte_source": sha(octets),
                    "reference_procedure_source": projet(avis),
                    "numero_acheteur_source": dossier["siret_chiffres_sans_schema_boamp"],
                    "lien_explicite_boamp": True,
                })
        if len(codes_origines) != 17 or len(liens) > MAX_LIENS:
            raise LiensInvalides("Population de liens incorrecte")
    return sorted(liens, key=lambda x: (x["avis_source"], x["avis_lie"])), sha(brut_chaines)


def classifier_reponse(brut: bytes, cible: dict) -> dict:
    """Classer la preuve de l'avis cité sans égalité juridique automatique."""
    enveloppe = lire_json(brut)
    if not isinstance(enveloppe, dict):
        raise LiensInvalides("Enveloppe officielle liée invalide")
    total = enveloppe.get("total_count")
    results = enveloppe.get("results")
    if type(total) is not int or total not in (0, 1) or not isinstance(results, list):
        raise LiensInvalides("Résultat de recherche DILA ambigu")
    if len(results) != total:
        raise LiensInvalides("Nombre d'avis liés contradictoire")
    if total == 0:
        return {
            "statut_recherche": "non_retrouve_dans_la_reponse",
            "date_parution_avis_lie": None,
            "nature_avis_lie": None,
            "reference_procedure_avis_lie": None,
            "correspondance_reference_procedure": "non_comparable",
            "numero_acheteur_avis_lie": None,
            "concordance_numero_acheteur": "non_comparable",
            "acte_contractuel_obtenu": False,
            "identite_juridique_procedure_demontree": False,
        }
    avis = results[0]
    if not isinstance(avis, dict) or avis.get("idweb") != cible["avis_lie"]:
        raise LiensInvalides("Avis lié ne correspond pas au numéro recherché")
    publication = date_jour(avis.get("dateparution"))
    if publication > cible["date_parution_source"]:
        raise LiensInvalides("Avis antérieur publié après l'avis qui le cite")
    autre_ref = projet(avis)
    origine_ref = cible["reference_procedure_source"]
    if not autre_ref or not origine_ref:
        ref_statut = "non_comparable"
    elif reference_normalisee(autre_ref) is None or reference_normalisee(origine_ref) is None:
        ref_statut = "non_comparable"
    elif reference_normalisee(autre_ref) == reference_normalisee(origine_ref):
        ref_statut = "reference_interne_concordante"
    else:
        ref_statut = "references_internes_distinctes"
    autre_numero = identifiant_acheteur(avis)
    source_numero = cible["numero_acheteur_source"]
    if not autre_numero or not source_numero:
        acheteur = "non_comparable"
    elif autre_numero == source_numero:
        acheteur = "numeros_identiques_sans_preuve_role_juridique"
    else:
        acheteur = "numeros_differents"
    return {
        "statut_recherche": "avis_officiel_retrouve",
        "date_parution_avis_lie": publication,
        "nature_avis_lie": avis.get("nature"),
        "reference_procedure_avis_lie": autre_ref,
        "correspondance_reference_procedure": ref_statut,
        "numero_acheteur_avis_lie": autre_numero,
        "concordance_numero_acheteur": acheteur,
        "acte_contractuel_obtenu": False,
        "identite_juridique_procedure_demontree": False,
    }


def verifier_archive(dossier: Path, archive: Path, chaines: Path) -> dict:
    cibles, empreinte_rapport = sources(archive, chaines)
    rapport = lire_json((dossier / "rapport.json").read_bytes())
    if (rapport.get("version") != VERSION
            or rapport.get("sha256_chaines_originales") != empreinte_rapport
            or rapport.get("nombre_liens_explicites") != len(cibles)):
        raise LiensInvalides("Provenance ou quantité de liens incohérente")
    cas = rapport.get("avis_lies")
    if not isinstance(cas, list) or len(cas) != len(cibles):
        raise LiensInvalides("Inventaire d'avis liés incomplet")
    for cible, fiche in zip(cibles, cas):
        if any(fiche.get(k) != v for k, v in cible.items()):
            raise LiensInvalides("Preuve source de liaison modifiée")
        code = cible["avis_lie"]
        fichier = dossier / (code + ".json")
        if (fichier.is_symlink() or not fichier.is_file()
                or fiche.get("fichier_reponse") != fichier.name
                or fiche.get("url_officielle") != adresse(code)):
            raise LiensInvalides("Fichier lié ou origine absents")
        octets = fichier.read_bytes()
        if fiche.get("octets") != len(octets) or fiche.get("sha256") != sha(octets):
            raise LiensInvalides("Empreinte de réponse liée altérée")
        qualification = classifier_reponse(octets, cible)
        if any(fiche.get(k) != v for k, v in qualification.items()):
            raise LiensInvalides("Qualification liée modifiée")
    if rapport.get("nombre_retrouves") != sum(
        x["statut_recherche"] == "avis_officiel_retrouve" for x in cas
    ):
        raise LiensInvalides("Nombre d'avis retrouvés incorrect")
    return rapport


def capturer(archive: Path, chaines: Path, sortie: Path, *,
             obtenir=obtenir_octets, instant: datetime | None = None) -> dict:
    cibles, empreinte_rapport = sources(archive, chaines)
    now = instant or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise LiensInvalides("Horodatage sans fuseau")
    if sortie.exists() or sortie.is_symlink():
        raise LiensInvalides("Destination existante")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=".lies-boamp-", dir=sortie.parent))
    try:
        fiches = []
        for cible in cibles:
            code = cible["avis_lie"]
            brut = obtenir(adresse(code))
            observation = classifier_reponse(brut, cible)
            (temp / (code + ".json")).write_bytes(brut)
            fiches.append({
                **cible, "url_officielle": adresse(code),
                "fichier_reponse": code + ".json",
                "octets": len(brut), "sha256": sha(brut),
                **observation,
            })
        rapport = {
            "version": VERSION,
            "observe_le": now.astimezone(timezone.utc).isoformat(),
            "sha256_chaines_originales": empreinte_rapport,
            "nombre_avis_sources": 17,
            "nombre_liens_explicites": len(cibles),
            "nombre_retrouves": sum(
                x["statut_recherche"] == "avis_officiel_retrouve" for x in fiches
            ),
            "avis_lies": fiches,
            "nombre_identites_juridiques_confirmees": 0,
            "nombre_actes_contractuels_obtenus": 0,
            "limite": (
                "Un avis lié démontre une référence officielle, non l'identité "
                "juridique de la procédure ou l'accès au contrat. L'absence d'un "
                "lien explicite ne signifie pas absence d'avis antérieur."
            ),
        }
        (temp / "rapport.json").write_text(
            json.dumps(rapport, ensure_ascii=False, sort_keys=True,
                       indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        verifier_archive(temp, archive, chaines)
        temp.rename(sortie)
        return rapport
    finally:
        if temp.exists():
            shutil.rmtree(temp)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive-boamp", required=True, type=Path)
    p.add_argument("--chaines", required=True, type=Path)
    p.add_argument("--sortie", type=Path)
    p.add_argument("--verifier", type=Path)
    a = p.parse_args()
    try:
        if bool(a.sortie) == bool(a.verifier):
            raise LiensInvalides("Choisir collecte ou vérification")
        r = (verifier_archive(a.verifier, a.archive_boamp, a.chaines)
             if a.verifier else capturer(a.archive_boamp, a.chaines, a.sortie))
        print(json.dumps({
            "liens": r["nombre_liens_explicites"],
            "retrouves": r["nombre_retrouves"],
            "contrats_identifies": r["nombre_actes_contractuels_obtenus"],
        }, ensure_ascii=False))
    except (OSError, ValueError, TypeError, KeyError, BadZipFile,
            HTTPError, URLError) as exc:
        p.exit(1, f"Enquête sur les avis liés interrompue : {exc}\n")


if __name__ == "__main__":
    main()
