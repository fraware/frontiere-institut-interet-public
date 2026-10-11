"""Capturer les avis BOAMP explicitement antérieurs aux rectificatifs pilotes.

Une liaison explicite est observée, jamais assimilée à la preuve qu'une
consultation initiale avait un contenu ou une date déterminés à l'avance.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

try:
    from scripts.collecter_notices_pilotes_boamp import (
        adresse, obtenir_octets, verifier_capture,
    )
    from scripts.qualifier_captures_notices_boamp import liens_avis
except ModuleNotFoundError:
    from collecter_notices_pilotes_boamp import (
        adresse, obtenir_octets, verifier_capture,
    )
    from qualifier_captures_notices_boamp import liens_avis

VERSION = "avis-anterieurs-rectificatifs-pilotes-v1"
MAX_LIENS = 12


class LienInvalide(ValueError):
    """Lien déclaré ou réponse officielle non qualifiable."""


def date_stricte(valeur):
    if not isinstance(valeur, str) or len(valeur) < 10:
        raise LienInvalide("Date de publication manquante.")
    try:
        jour = date.fromisoformat(valeur[:10])
    except ValueError as erreur:
        raise LienInvalide("Date de publication incorrecte.") from erreur
    if jour.isoformat() != valeur[:10]:
        raise LienInvalide("Date de publication non canonique.")
    return jour.isoformat()


def origine_liens(principaux: Path):
    rapport = verifier_capture(principaux)
    liens = {}
    for fiche in rapport["cas"]:
        if fiche["etat_observation"] != "notice_retrouvee_et_identifiee":
            continue
        parent = json.loads((principaux / fiche["fichier_reponse"]).read_bytes())["results"][0]
        if parent.get("etat") != "RECTIFICATIF":
            continue
        references = liens_avis(parent.get("annonce_lie"))
        parution = date_stricte(parent.get("dateparution"))
        for identifiant in references:
            if identifiant == fiche["identifiant"]:
                raise LienInvalide("Un rectificatif se référence lui-même.")
            if identifiant in liens:
                raise LienInvalide("Avis antérieur référencé plusieurs fois.")
            liens[identifiant] = {
                "avis_rectificatif": fiche["identifiant"],
                "date_rectificatif": parution,
                "empreinte_parent": fiche["sha256_reponse_http"],
            }
    if len(liens) > MAX_LIENS:
        raise LienInvalide("Trop d'avis à suivre dans une seule capture.")
    return rapport, liens


def qualifier_reponse(brut: bytes, identifiant: str, parent: dict):
    if not isinstance(brut, bytes) or not brut or len(brut) > 5_000_000:
        raise LienInvalide("Réponse liée vide ou trop volumineuse.")
    try:
        enveloppe = json.loads(brut)
    except (UnicodeDecodeError, json.JSONDecodeError) as erreur:
        raise LienInvalide("Réponse liée non JSON.") from erreur
    if not isinstance(enveloppe, dict):
        raise LienInvalide("Enveloppe liée incorrecte.")
    total, items = enveloppe.get("total_count"), enveloppe.get("results")
    if type(total) is not int or total not in (0, 1) or not isinstance(items, list):
        raise LienInvalide("Nombre d'avis liés incorrect.")
    if len(items) != total:
        raise LienInvalide("Pagination des avis liés contradictoire.")
    if not total:
        return {"etat_recherche": "non_retrouve_lors_du_releve",
                "date_parution": None, "etat_documentaire": None,
                "nature_documentaire": None}
    fiche = items[0]
    if not isinstance(fiche, dict) or fiche.get("idweb") != identifiant:
        raise LienInvalide("Identifiant d'avis lié contradictoire.")
    parution = date_stricte(fiche.get("dateparution"))
    if parution > parent["date_rectificatif"]:
        raise LienInvalide("Avis prétendument antérieur publié après le rectificatif.")
    return {
        "etat_recherche": "notice_retrouvee",
        "date_parution": parution,
        "etat_documentaire": fiche.get("etat"),
        "nature_documentaire": fiche.get("nature"),
    }


def verifier_lies(dossier: Path, principaux: Path):
    _, parents = origine_liens(principaux)
    rapport = json.loads((dossier / "rapport.json").read_text(encoding="utf-8"))
    if rapport.get("version") != VERSION or set(parents) != {
        x["identifiant"] for x in rapport["avis"]
    } or len(parents) != len(rapport["avis"]):
        raise LienInvalide("Inventaire de suivi incohérent.")
    for fiche in rapport["avis"]:
        code = fiche["identifiant"]
        attendu = parents[code]
        if any(fiche.get(k) != v for k, v in attendu.items()):
            raise LienInvalide("Référence du rectificatif modifiée.")
        if fiche.get("url_officielle") != adresse(code):
            raise LienInvalide("Interrogation liée incohérente.")
        chemin = dossier / (code + ".json")
        if chemin.is_symlink() or not chemin.is_file() or fiche.get("fichier") != chemin.name:
            raise LienInvalide("Fichier lié absent ou chemin incorrect.")
        brut = chemin.read_bytes()
        if (fiche.get("octets") != len(brut)
                or fiche.get("sha256") != hashlib.sha256(brut).hexdigest()):
            raise LienInvalide("Archive d'avis lié corrompue.")
        observation = qualifier_reponse(brut, code, attendu)
        if any(fiche.get(k) != valeur for k, valeur in observation.items()):
            raise LienInvalide("Interprétation d'avis lié incohérente.")
    return rapport


def capturer_lies(principaux: Path, sortie: Path, obtenir=obtenir_octets,
                  instant: datetime | None = None):
    observation = instant or datetime.now(timezone.utc)
    if observation.tzinfo is None or observation.utcoffset() is None:
        raise LienInvalide("Horodatage sans fuseau.")
    original, parents = origine_liens(principaux)
    if sortie.exists() or sortie.is_symlink():
        raise LienInvalide("Le dossier existe déjà.")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    temporaire = Path(tempfile.mkdtemp(prefix=".avis-lies-", dir=sortie.parent))
    try:
        fiches = []
        for code, parent in sorted(parents.items()):
            brut = obtenir(adresse(code))
            qualification = qualifier_reponse(brut, code, parent)
            (temporaire / (code + ".json")).write_bytes(brut)
            fiches.append({
                "identifiant": code, **parent,
                "url_officielle": adresse(code), "fichier": code + ".json",
                "octets": len(brut), "sha256": hashlib.sha256(brut).hexdigest(),
                **qualification,
            })
        rapport = {
            "version": VERSION,
            "observe_le": observation.astimezone(timezone.utc).isoformat(),
            "capture_origine_observee_le": original["observe_le"],
            "avis_lies_deja_qualifies": False,
            "avis": fiches,
            "nombre_retrouves": sum(x["etat_recherche"] == "notice_retrouvee" for x in fiches),
            "origine_du_besoin_etablie": False,
            "premiere_contribution_utile_etablie": False,
        }
        (temporaire / "rapport.json").write_text(
            json.dumps(rapport, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        verifier_lies(temporaire, principaux)
        os.rename(temporaire, sortie)
        return rapport
    finally:
        if temporaire.exists():
            shutil.rmtree(temporaire)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--principaux", type=Path, required=True)
    p.add_argument("--sortie", type=Path)
    p.add_argument("--verifier", type=Path)
    a = p.parse_args()
    try:
        if a.verifier:
            bilan = verifier_lies(a.verifier, a.principaux)
        elif a.sortie:
            bilan = capturer_lies(a.principaux, a.sortie)
        else:
            raise LienInvalide("Une sortie ou une vérification doit être indiquée.")
        print(json.dumps({
            "liens": len(bilan["avis"]), "retrouves": bilan["nombre_retrouves"],
        }, ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        p.exit(1, f"Suivi des rectificatifs interrompu : {exc}\n")


if __name__ == "__main__":
    main()
