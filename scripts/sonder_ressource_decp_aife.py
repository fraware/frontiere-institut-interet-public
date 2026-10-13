"""Prélever un petit fichier JSON DECP officiel, puis lancer son ingestion bornée.

L'URL du fichier provient exclusivement de la fiche API officielle AIFE, et
l'identifiant de ressource est recoupé avec le registre local déjà observé.
Aucun domaine arbitraire et aucune redirection vers un tiers ne sont suivis.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

if __package__:
    from scripts.collecter_catalogues_decp import telecharger as telecharger_catalogue
    from scripts.ingerer_fichier_decp_json import RACINE, traiter_fichier, DocumentDECPInvalide
else:
    from collecter_catalogues_decp import telecharger as telecharger_catalogue
    from ingerer_fichier_decp_json import RACINE, traiter_fichier, DocumentDECPInvalide

ETAT = RACINE / "institutionnel/decp/etat_ressources.json"
SORTIE = RACINE / "institutionnel/decp/sonde_aife_json.json"
SOURCE = "aife_api_decp"
PLAFOND_OCTETS = 1_500_000
DOMAINES_FICHIERS = frozenset({"static.data.gouv.fr", "www.data.gouv.fr"})


class SondeDECPInvalide(ValueError):
    """Une ressource n'est pas admissible au relevé réel limité."""


def _url_officielle(url: object) -> str:
    if not isinstance(url, str) or len(url) > 2000:
        raise SondeDECPInvalide("Adresse de ressource invalide")
    p = urlsplit(url)
    if (
        p.scheme != "https" or p.hostname not in DOMAINES_FICHIERS
        or p.username or p.password or p.port not in (None, 443)
        or p.fragment
    ):
        raise SondeDECPInvalide("Origine de fichier hors domaine public autorisé")
    return url


class RedirectionsRestreintes(HTTPRedirectHandler):
    """Refuser les destinations non autorisées, y compris lors d'une redirection."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _url_officielle(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def choisir_ressource(etat: dict, fiche: dict) -> dict:
    """Choisir une ressource JSON récente déjà recensée et encore publiée."""
    if not isinstance(etat, dict) or not isinstance(fiche, dict):
        raise SondeDECPInvalide("Registre ou fiche incorrecte")
    catalogue = next(
        (x for x in etat.get("catalogues", [])
         if isinstance(x, dict) and x.get("source_id") == SOURCE),
        None,
    )
    if catalogue is None:
        raise SondeDECPInvalide("Catalogue AIFE absent de l'état local")
    ressources = fiche.get("resources")
    if not isinstance(ressources, list):
        raise SondeDECPInvalide("Ressources absentes de la fiche officielle")
    distantes = {
        x["id"]: x for x in ressources
        if isinstance(x, dict) and isinstance(x.get("id"), str)
    }
    for connu in catalogue.get("ressources_recentes", []):
        rid = connu.get("id")
        actuel = distantes.get(rid)
        if (
            actuel is not None
            and str(actuel.get("format", "")).lower() == "json"
            and connu.get("format") == "json"
            and isinstance(connu.get("taille_octets_declaree"), int)
            and 0 < connu["taille_octets_declaree"] <= PLAFOND_OCTETS
            and type(actuel.get("filesize")) is int
            and 0 < actuel["filesize"] <= PLAFOND_OCTETS
            and actuel["filesize"] == connu["taille_octets_declaree"]
        ):
            lien = _url_officielle(actuel.get("url"))
            return {
                "id": rid, "url": lien, "titre": connu.get("titre"),
                "taille_octets_declaree": actuel["filesize"],
            }
    raise SondeDECPInvalide("Aucun fichier JSON admissible et confirmé disponible")


def recevoir_fichier(ressource: dict, cible: Path) -> int:
    """Récupérer un fichier public limité, sans écriture partielle en destination."""
    url = _url_officielle(ressource["url"])
    requete = Request(url, headers={
        "User-Agent": "FRONTIERE-observation-DECP/1.0",
        "Accept": "application/json,application/octet-stream",
    })
    compte = 0
    with build_opener(RedirectionsRestreintes()).open(requete, timeout=45) as reponse:
        if reponse.status != 200:
            raise SondeDECPInvalide("Statut HTTP de ressource non conforme")
        _url_officielle(reponse.geturl())
        with cible.open("wb") as sortie:
            while True:
                morceau = reponse.read(min(65536, PLAFOND_OCTETS - compte + 1))
                if not morceau:
                    break
                compte += len(morceau)
                if compte > PLAFOND_OCTETS:
                    raise SondeDECPInvalide("Réponse supérieure au plafond")
                sortie.write(morceau)
    if compte == 0:
        raise SondeDECPInvalide("Fichier vide")
    return compte


def diagnostiquer_structure(chemin: Path) -> dict:
    """Décrire seulement la structure d'un petit fichier, sans publier son contenu."""
    if chemin.stat().st_size > PLAFOND_OCTETS:
        raise SondeDECPInvalide("Fichier de diagnostic hors plafond")
    with chemin.open("r", encoding="utf-8-sig") as flux:
        doc = json.load(flux)
    if isinstance(doc, dict):
        return {
            "type": "objet",
            "champs_racine": sorted(doc)[:30],
            "types_racine": {
                str(cle)[:100]: type(valeur).__name__
                for cle, valeur in sorted(doc.items())[:30]
            },
            "types_sous_marches": (
                {str(cle)[:100]: type(valeur).__name__
                 for cle, valeur in doc["marches"].items()}
                if isinstance(doc.get("marches"), dict) else {}
            ),
        }
    return {"type": type(doc).__name__}


def executer(etat: dict, fiche: dict, recuperer=recevoir_fichier) -> dict:
    """Comparer les métadonnées et produire un bilan sur le fichier téléchargé."""
    selection = choisir_ressource(etat, fiche)
    with tempfile.TemporaryDirectory(prefix="frontiere-decp-") as dossier:
        chemin = Path(dossier) / "aife.json"
        taille = recuperer(selection, chemin)
        if taille != selection["taille_octets_declaree"] or chemin.stat().st_size != taille:
            raise SondeDECPInvalide("Taille du fichier différente du catalogue")
        try:
            resultat = traiter_fichier(
                chemin, source_id=SOURCE, ressource_id=selection["id"],
                limite_extraits=50,
            )
        except DocumentDECPInvalide as exc:
            try:
                structure = diagnostiquer_structure(chemin)
            except (OSError, ValueError, UnicodeError):
                structure = {"type": "structure_inaccessible"}
            raise SondeDECPInvalide(
                "Enveloppe JSON non prise en charge ; structure : "
                + json.dumps(structure, ensure_ascii=False, sort_keys=True)
            ) from exc
    resultat["page_catalogue"] = "https://www.data.gouv.fr/datasets/api-decp"
    resultat["titre_fichier"] = selection["titre"]
    resultat["type_essai"] = "sonde_reelle_bornee_non_exhaustive"
    resultat["telechargement_integral_du_catalogue"] = False
    return resultat


def main() -> None:
    """Lire les métadonnées et interroger le seul catalogue AIFE référencé."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--etat", type=Path, default=ETAT)
    p.add_argument("--sortie", type=Path, default=SORTIE)
    args = p.parse_args()
    try:
        etat = json.loads(args.etat.read_text(encoding="utf-8"))
        source = {
            "url": "https://www.data.gouv.fr/api/1/datasets/api-decp/"
        }
        fiche = telecharger_catalogue(source)
        rapport = executer(etat, fiche)
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        temp = args.sortie.with_name(args.sortie.name + ".tmp")
        temp.write_text(
            json.dumps(rapport, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
            + "\n", encoding="utf-8",
        )
        temp.replace(args.sortie)
        print(json.dumps(
            {cle: valeur for cle, valeur in rapport.items() if cle != "marches_extraits"},
            ensure_ascii=False, sort_keys=True,
        ))
    except (OSError, ValueError, HTTPError, URLError) as exc:
        p.exit(1, f"Sonde DECP refusée : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
