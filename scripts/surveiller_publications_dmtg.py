"""Surveillance bornée des publications publiques relatives au chantier DMTG.

Les cinq pages officielles fournissent des signatures documentaires. Une
évolution déclenche une relecture, sans attester un recrutement, une diffusion
de microdonnées ou une avancée du projet. Aucun fichier fiscal n'est récupéré.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from scripts.surveiller_programmes_scientifiques import (
    SurveillanceInvalide, collecter, empreinte_document, verifier_etat,
)

RACINE = Path(__file__).resolve().parents[1]
CATALOGUE = Path("institutionnel/programmes_scientifiques/sources_veille_dmtg_v1.json")
ETAT = Path("institutionnel/programmes_scientifiques/etat_veille_dmtg_v1.json")
DOMAINES = frozenset({
    "www.impots.gouv.fr", "impots.gouv.fr",
    "questions.assemblee-nationale.fr", "www.senat.fr",
})
IDENTIFIANT = re.compile(r"^[a-z][a-z0-9_]{3,70}$")
TAILLE_MAX = 3_000_000
NATURES = frozenset({
    "index_statistiques", "catalogue_recettes", "catalogue_mutations",
    "reponse_ministerielle", "rapport_parlementaire",
})


def autoriser_adresse(url: object) -> str:
    """Refuser origines non officielles, protocoles en clair et identifiants."""
    if not isinstance(url, str) or len(url) > 2048:
        raise SurveillanceInvalide("Adresse publique invalide")
    parts = urlsplit(url)
    if (
        parts.scheme != "https" or parts.hostname not in DOMAINES
        or parts.username or parts.password or parts.fragment
        or parts.port not in (None, 443) or not parts.path.startswith("/")
    ):
        raise SurveillanceInvalide("Origine de publication interdite")
    return url


class RedirectionsOfficielles(HTTPRedirectHandler):
    """Accepter uniquement les redirections internes au périmètre public."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        autoriser_adresse(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def valider_catalogue(catalogue: object) -> list[dict]:
    if not isinstance(catalogue, dict) or catalogue.get("version") != 1:
        raise SurveillanceInvalide("Version de catalogue DMTG inconnue")
    sources = catalogue.get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= 12:
        raise SurveillanceInvalide("Périmètre documentaire invalide")
    ids = set()
    adresses = set()
    for source in sources:
        if not isinstance(source, dict):
            raise SurveillanceInvalide("Entrée documentaire mal formée")
        uid = source.get("id")
        if not isinstance(uid, str) or not IDENTIFIANT.fullmatch(uid) or uid in ids:
            raise SurveillanceInvalide("Identifiant de document absent ou répété")
        ids.add(uid)
        adresse = autoriser_adresse(source.get("url"))
        if adresse in adresses:
            raise SurveillanceInvalide("Adresse officielle en double")
        adresses.add(adresse)
        if (source.get("programme") != "dmtg_2026"
                or source.get("format") != "html"
                or source.get("nature_document") not in NATURES):
            raise SurveillanceInvalide("Type de pièce incompatible")
        if not isinstance(source.get("motif"), str) or not source["motif"].strip():
            raise SurveillanceInvalide("Motif de surveillance absent")
    return sources


def consulter(source: dict) -> tuple[bytes, str]:
    url = autoriser_adresse(source["url"])
    req = Request(
        url,
        headers={
            "User-Agent": "FRONTIERE-veille-DMTG/1.0 (observations publiques)",
            "Accept": "text/html, application/xhtml+xml",
        },
    )
    with build_opener(RedirectionsOfficielles).open(req, timeout=25) as rep:
        autoriser_adresse(rep.geturl())
        media = rep.headers.get("Content-Type", "").split(";")[0].lower().strip()
        if rep.status != 200 or media not in {
            "text/html", "application/xhtml+xml"
        }:
            raise SurveillanceInvalide("Réponse inattendue ou contenu non HTML")
        data = rep.read(TAILLE_MAX + 1)
    if not data or len(data) > TAILLE_MAX:
        raise SurveillanceInvalide("Document vide ou excédant le plafond")
    # Vérifier ici que la réponse contient un corps éditorial suffisant pour
    # éviter d'archiver silencieusement une page de protection minimaliste.
    empreinte_document(data, "html")
    return data, media


def lancer(racine: Path, *, acquerir=consulter,
           moment: datetime | None = None) -> tuple[dict, dict]:
    catalogue = json.loads((racine / CATALOGUE).read_text(encoding="utf-8"))
    etat = json.loads((racine / ETAT).read_text(encoding="utf-8"))
    sources = valider_catalogue(catalogue)
    observations = verifier_etat(etat)
    if not set(observations).issubset({s["id"] for s in sources}):
        raise SurveillanceInvalide("Source historique absente du catalogue")
    for source in sources:
        precedente = observations.get(source["id"])
        if precedente and (
            precedente.get("url") != source["url"]
            or precedente.get("programme") != source["programme"]
            or precedente.get("nature_document") != source["nature_document"]
        ):
            raise SurveillanceInvalide("Filiation documentaire modifiée : revue nécessaire")
    suivant, bilan = collecter(
        sources, etat, moment or datetime.now(timezone.utc), acquerir=acquerir
    )
    bilan["interpretation_probatoire"] = (
        "Signature technique uniquement : aucun état de recrutement, "
        "d'extraction ou de production n'est déduit."
    )
    return suivant, bilan


def resume(bilan: dict) -> str:
    lignes = [
        "## FRONTIÈRE — surveillance documentaire DMTG",
        f"Relevé : {bilan['controle_le']}",
        f"Sources consultées : {bilan['succes']}/{bilan['points_controles']}; "
        f"échecs : {bilan['echecs']}.",
        "Les modifications appellent une lecture de la nouvelle pièce officielle. "
        "Aucun résultat opérationnel n'est inféré.",
        "",
        "| Source | Observation |",
        "| --- | --- |",
    ]
    for entree in bilan["controles"]:
        lignes.append(f"| {entree['source_id']} | {entree['etat']} |")
    return "\n".join(lignes) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--racine", type=Path, default=RACINE)
    parser.add_argument("--bilan-json", type=Path)
    parser.add_argument("--bilan-markdown", type=Path)
    args = parser.parse_args()
    try:
        actuel = json.loads((args.racine / ETAT).read_text(encoding="utf-8"))
        nouvel, bilan = lancer(args.racine)
        if nouvel != actuel:
            (args.racine / ETAT).write_text(
                json.dumps(nouvel, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        if args.bilan_json:
            args.bilan_json.parent.mkdir(parents=True, exist_ok=True)
            args.bilan_json.write_text(
                json.dumps(bilan, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        if args.bilan_markdown:
            args.bilan_markdown.parent.mkdir(parents=True, exist_ok=True)
            args.bilan_markdown.write_text(resume(bilan), encoding="utf-8")
        print(resume(bilan))
        return 2 if bilan["echecs"] else 0
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        print(f"Relevé DMTG interrompu : {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
