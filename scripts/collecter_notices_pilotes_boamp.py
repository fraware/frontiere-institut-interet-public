"""Capturer les réponses officielles complètes pour les cas pilotes BOAMP.

Les octets HTTP sont conservés exactement tels que reçus, avec empreintes et
heure de capture. Un relevé ultérieur ne reconstitue pas l'état historique de
la source. Les pièces de consultation et la mobilisation ne sont pas déduites.
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
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

try:
    from scripts.preparer_dossiers_pilotes_boamp import lire_cas
except ModuleNotFoundError:
    from preparer_dossiers_pilotes_boamp import lire_cas


VERSION = "captures-notices-primaires-boamp-v1"
API = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records"
PLAFOND_OCTETS = 5_000_000


class CaptureInvalide(ValueError):
    """Réponse distante, registre ou capture incompatible avec la preuve attendue."""


class SansRedirection(HTTPRedirectHandler):
    """Empêcher le transport de quitter l'origine officielle."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CaptureInvalide("Une redirection du service officiel a été refusée.")


def adresse(identifiant: str) -> str:
    """Former exclusivement une interrogation exacte sur un identifiant validé."""
    import re
    if not re.fullmatch(r"[0-9]{2}-[0-9]{2,8}", identifiant):
        raise CaptureInvalide("Identifiant d'avis BOAMP incorrect.")
    return API + "?" + urlencode({
        "where": f'idweb = "{identifiant}"',
        "limit": 2,
    })


def obtenir_octets(url: str) -> bytes:
    """Récupérer les octets d'une réponse HTTP sans redirection ni pagination."""
    if not url.startswith(API + "?"):
        raise CaptureInvalide("Origine de l'interrogation non autorisée.")
    requete = Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "FRONTIERE-captures-pilotes/1.0",
    })
    with build_opener(SansRedirection).open(requete, timeout=35) as reponse:
        if reponse.status != 200:
            raise CaptureInvalide("La source officielle n'a pas renvoyé HTTP 200.")
        contenu = reponse.read(PLAFOND_OCTETS + 1)
    if len(contenu) > PLAFOND_OCTETS:
        raise CaptureInvalide("La réponse officielle dépasse le plafond d'octets.")
    return contenu


def qualifier(brut: bytes, identifiant: str, date_attendue: str) -> dict:
    """Distinguer une notice exacte, une réponse vide et une anomalie de source."""
    if not isinstance(brut, bytes) or len(brut) > PLAFOND_OCTETS or not brut:
        raise CaptureInvalide("Réponse absente, invalide ou trop volumineuse.")
    try:
        reponse = json.loads(brut)
    except (UnicodeDecodeError, json.JSONDecodeError) as erreur:
        raise CaptureInvalide("La réponse officielle ne contient pas de JSON valide.") from erreur
    if not isinstance(reponse, dict):
        raise CaptureInvalide("Enveloppe officielle incorrecte.")
    total, resultats = reponse.get("total_count"), reponse.get("results")
    if type(total) is not int or not isinstance(resultats, list):
        raise CaptureInvalide("Effectif et liste de résultats absents.")
    if total > 1 or total < 0 or len(resultats) != total:
        raise CaptureInvalide("Identifiant ambigu ou pagination incohérente.")
    if total == 0:
        return {
            "etat_observation": "non_retrouve_lors_de_ce_releve",
            "date_parution_reobservee": None,
            "etat_documentaire_reobserve": None,
            "nombre_champs_officiels": 0,
        }
    notice = resultats[0]
    if not isinstance(notice, dict) or notice.get("idweb") != identifiant:
        raise CaptureInvalide("Identifiant de la notice différent de la demande.")
    date_source = notice.get("dateparution")
    if not isinstance(date_source, str):
        raise CaptureInvalide("Date officielle absente ou mal formée.")
    try:
        verifiee = date.fromisoformat(date_source[:10])
    except ValueError as erreur:
        raise CaptureInvalide("Date officielle non interprétable.") from erreur
    if verifiee.isoformat() != date_attendue:
        raise CaptureInvalide("Date officielle différente de la référence pilote.")
    return {
        "etat_observation": "notice_retrouvee_et_identifiee",
        "date_parution_reobservee": date_source,
        "etat_documentaire_reobserve": notice.get("etat"),
        "nombre_champs_officiels": len(notice),
    }


def capturer(registre: Path, dossier: Path, obtenir=obtenir_octets,
             instant: datetime | None = None) -> dict:
    """Produire une capture indivisible des réponses des cas du registre.

    Une absence de notice est enregistrée comme observation manquante.
    Une réponse malformée, ambiguë ou contradictoire empêche toute publication.
    """
    observation = instant or datetime.now(timezone.utc)
    if observation.tzinfo is None or observation.utcoffset() is None:
        raise CaptureInvalide("L'instant de capture doit inclure un fuseau horaire.")
    observation = observation.astimezone(timezone.utc).isoformat()
    if not registre.is_file():
        raise CaptureInvalide("Registre des pilotes absent.")
    cas = lire_cas(registre)
    registre_sha = hashlib.sha256(registre.read_bytes()).hexdigest()
    if dossier.exists() or dossier.is_symlink():
        raise CaptureInvalide("Le dossier de sortie existe déjà.")
    dossier.parent.mkdir(parents=True, exist_ok=True)
    temporaire = Path(tempfile.mkdtemp(prefix=".captures-boamp-", dir=dossier.parent))
    try:
        fiches = []
        for fiche in cas:
            identifiant = fiche["identifiant"]
            url = adresse(identifiant)
            brut = obtenir(url)
            observation_cas = qualifier(brut, identifiant, fiche["date_attendue"])
            nom = identifiant + ".json"
            (temporaire / nom).write_bytes(brut)
            fiches.append({
                "identifiant": identifiant,
                "date_pilote_attendue": fiche["date_attendue"],
                "source_officielle_interrogee": url,
                "fichier_reponse": nom,
                "octets_reponse": len(brut),
                "sha256_reponse_http": hashlib.sha256(brut).hexdigest(),
                **observation_cas,
            })
        rapport = {
            "version": VERSION,
            "observe_le": observation,
            "registre_source": str(registre),
            "sha256_registre": registre_sha,
            "nombre_cas": len(cas),
            "nombre_notices_retrouvees": sum(
                x["etat_observation"] == "notice_retrouvee_et_identifiee"
                for x in fiches
            ),
            "cas": fiches,
            "pieces_de_consultation_obtenues": False,
            "besoins_de_competence_verifies": False,
            "capacites_mobilisables_verifiees": False,
            "historique_integral_des_avis_etabli": False,
        }
        (temporaire / "rapport.json").write_text(
            json.dumps(rapport, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        verifier_capture(temporaire)
        os.rename(temporaire, dossier)
        return rapport
    finally:
        if temporaire.exists():
            shutil.rmtree(temporaire)


def verifier_capture(dossier: Path) -> dict:
    """Rejouer la qualification à partir des octets archivés et des empreintes."""
    rapport = json.loads((dossier / "rapport.json").read_text(encoding="utf-8"))
    if rapport.get("version") != VERSION:
        raise CaptureInvalide("Version de capture inconnue.")
    fiches = rapport.get("cas")
    if not isinstance(fiches, list) or len(fiches) != rapport.get("nombre_cas"):
        raise CaptureInvalide("Inventaire de capture incohérent.")
    identifiants = set()
    for fiche in fiches:
        identifiant = fiche["identifiant"]
        if identifiant in identifiants:
            raise CaptureInvalide("Identifiant dupliqué dans la capture.")
        identifiants.add(identifiant)
        fichier = dossier / (identifiant + ".json")
        if fichier.is_symlink() or not fichier.is_file() or fiche["fichier_reponse"] != fichier.name:
            raise CaptureInvalide("Fichier de réponse absent ou chemin inattendu.")
        brut = fichier.read_bytes()
        if (len(brut) != fiche["octets_reponse"]
                or hashlib.sha256(brut).hexdigest() != fiche["sha256_reponse_http"]):
            raise CaptureInvalide("Empreinte ou taille de réponse incorrecte.")
        if fiche["source_officielle_interrogee"] != adresse(identifiant):
            raise CaptureInvalide("Adresse d'origine incohérente.")
        observation = qualifier(brut, identifiant, fiche["date_pilote_attendue"])
        if any(fiche.get(cle) != valeur for cle, valeur in observation.items()):
            raise CaptureInvalide("Qualification archivée incompatible avec la réponse.")
    if rapport["nombre_notices_retrouvees"] != sum(
        x["etat_observation"] == "notice_retrouvee_et_identifiee" for x in fiches
    ):
        raise CaptureInvalide("Effectif de notices retrouvées incohérent.")
    return rapport


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--registre", type=Path, default=Path("evaluation/cas_pilotes_boamp_v1.json"))
    p.add_argument("--sortie", type=Path, required=True)
    p.add_argument("--verifier", type=Path, help="Contrôler une capture existante sans collecte.")
    args = p.parse_args()
    try:
        if args.verifier:
            print(json.dumps({
                "version": VERSION,
                "cas_verifies": verifier_capture(args.verifier)["nombre_cas"],
            }, ensure_ascii=False))
        else:
            resultat = capturer(args.registre, args.sortie)
            print(json.dumps({
                "version": VERSION,
                "cas": resultat["nombre_cas"],
                "notices_retrouvees": resultat["nombre_notices_retrouvees"],
            }, ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError) as erreur:
        p.exit(1, f"Capture officielle interrompue : {type(erreur).__name__}: {erreur}\n")


if __name__ == "__main__":
    main()
