"""Surveiller les empreintes de publications ANR officielles sans inférer leurs effets.

Chaque consultation fournit une observation technique. Une modification déclenche
une proposition de relecture, jamais une transition automatique de statut d'un
projet. Les échecs n'effacent aucune empreinte déjà acquise.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from typing import Callable
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

RACINE = Path(__file__).resolve().parents[1]
SOURCES = Path("institutionnel/programmes_scientifiques/sources_v1.json")
ETAT = Path("institutionnel/programmes_scientifiques/etat_observations.json")
PLAFOND_OCTETS = 3_000_000
HISTORIQUE_MAX = 25
DOMAINES = frozenset({"anr.fr", "www.anr.fr"})
IDENTIFIANT = re.compile(r"^[a-z][a-z0-9_]{3,70}$")
EMPREINTE = re.compile(r"^[0-9a-f]{64}$")


class SurveillanceInvalide(ValueError):
    """Un contrat de source ou une observation est inexploitable."""


def adresse_autorisee(url: object) -> str:
    """Refuser toute origine ou redirection externe au producteur public."""
    if not isinstance(url, str) or len(url) > 2048:
        raise SurveillanceInvalide("Adresse absente ou trop longue")
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.hostname not in DOMAINES
            or parts.username or parts.password or parts.port not in (None, 443)
            or parts.fragment or not parts.path.startswith("/")):
        raise SurveillanceInvalide("Origine, port ou adresse interdits")
    return url


class RedirectionsANR(HTTPRedirectHandler):
    """N'accepter que les réorientations HTTPS entre hôtes officiels ANR."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        adresse_autorisee(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def charger_sources(document: object) -> list[dict]:
    if not isinstance(document, dict) or document.get("version") != 1:
        raise SurveillanceInvalide("Version de catalogue inconnue")
    sources = document.get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= 30:
        raise SurveillanceInvalide("Nombre de points d'observation invalide")
    identifiants = set()
    for item in sources:
        if not isinstance(item, dict):
            raise SurveillanceInvalide("Source mal formée")
        identifiant = item.get("id")
        if (not isinstance(identifiant, str)
                or not IDENTIFIANT.fullmatch(identifiant)
                or identifiant in identifiants):
            raise SurveillanceInvalide("Identifiant absent ou répété")
        identifiants.add(identifiant)
        if (not isinstance(item.get("programme"), str)
                or not IDENTIFIANT.fullmatch(item["programme"])):
            raise SurveillanceInvalide("Programme non identifié")
        if item.get("format") not in {"html", "pdf"}:
            raise SurveillanceInvalide("Format non autorisé")
        if item.get("nature_document") not in {
            "appel", "communique_selection", "liste_selection", "index_selections"
        }:
            raise SurveillanceInvalide("Nature documentaire non prise en charge")
        adresse_autorisee(item.get("url"))
    return sources


def obtenir(source: dict) -> tuple[bytes, str]:
    """Effectuer une seule lecture HTTPS bornée, sans ressources incluses."""
    url = adresse_autorisee(source["url"])
    req = Request(
        url,
        headers={
            "User-Agent": "FRONTIERE-veille-programmes/1.0 (contact institutionnel)",
            "Accept": "text/html, application/pdf",
        },
    )
    with build_opener(RedirectionsANR).open(req, timeout=25) as reponse:
        adresse_autorisee(reponse.geturl())
        if reponse.status != 200:
            raise SurveillanceInvalide("Réponse HTTP inattendue")
        contenu = reponse.read(PLAFOND_OCTETS + 1)
        media = reponse.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if not contenu or len(contenu) > PLAFOND_OCTETS:
        raise SurveillanceInvalide("Contenu vide ou supérieur au plafond")
    if source["format"] == "pdf":
        if media != "application/pdf" or not contenu.startswith(b"%PDF-"):
            raise SurveillanceInvalide("Document PDF non confirmé")
    elif media not in {"text/html", "application/xhtml+xml"}:
        raise SurveillanceInvalide("Type de page HTML inattendu")
    return contenu, media


class TextePage(HTMLParser):
    """Extraire le corps éditorial en ignorant menus, scripts et pied de page.

    Lorsque <article> ou <main> est présent, privilégier ce texte. Un repli
    vers le contenu restant évite d'exiger une structure HTML particulière.
    """

    EXCLUS = frozenset({"script", "style", "noscript", "svg", "nav", "footer", "header"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.exclus = 0
        self.main = 0
        self.article = 0
        self.morceaux: list[str] = []
        self.contenu_main: list[str] = []
        self.contenu_article: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self.EXCLUS:
            self.exclus += 1
        if tag == "main":
            self.main += 1
        if tag == "article":
            self.article += 1
        if tag == "a" and not self.exclus:
            # Un lien vers une pièce officielle peut changer sans modification
            # du libellé affiché. Inclure sa cible parmi les preuves de version.
            for nom, valeur in attrs:
                if (nom == "href" and isinstance(valeur, str)
                        and len(valeur) <= 2048
                        and (
                            valeur.startswith("/fileadmin/")
                            or valeur.startswith("https://anr.fr/fileadmin/")
                            or valeur.startswith("https://www.anr.fr/fileadmin/")
                        )):
                    cible = f"[piece_officielle:{valeur}]"
                    self.morceaux.append(cible)
                    if self.main:
                        self.contenu_main.append(cible)
                    if self.article:
                        self.contenu_article.append(cible)
                    break

    def handle_endtag(self, tag: str) -> None:
        if tag in self.EXCLUS and self.exclus:
            self.exclus -= 1
        if tag == "main" and self.main:
            self.main -= 1
        if tag == "article" and self.article:
            self.article -= 1

    def handle_data(self, data: str) -> None:
        if self.exclus or not data.strip():
            return
        self.morceaux.append(data)
        if self.main:
            self.contenu_main.append(data)
        if self.article:
            self.contenu_article.append(data)

    def texte_utile(self) -> str:
        """Conserver le segment substantiel le plus spécifique."""
        for fragments in (
            self.contenu_article, self.contenu_main, self.morceaux
        ):
            normalise = " ".join(
                unicodedata.normalize("NFKC", " ".join(fragments)).split()
            )
            if len(normalise) >= 80:
                return normalise
        raise SurveillanceInvalide("Page insuffisamment informative")

def empreinte_document(contenu: bytes, format_source: str) -> str:
    """Calculer un condensé de PDF brut ou de texte HTML normalisé."""
    if format_source == "pdf":
        if not contenu.startswith(b"%PDF-"):
            raise SurveillanceInvalide("Signature PDF absente")
        matiere = contenu
    elif format_source == "html":
        try:
            texte = contenu.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise SurveillanceInvalide("Page non décodable en UTF-8") from exc
        analyseur = TextePage()
        analyseur.feed(texte)
        matiere = analyseur.texte_utile().encode("utf-8")
    else:
        raise SurveillanceInvalide("Format de contenu inconnu")
    return hashlib.sha256(matiere).hexdigest()


def verifier_etat(document: object) -> dict[str, dict]:
    if not isinstance(document, dict) or document.get("version") != 1:
        raise SurveillanceInvalide("Version d'état inconnue")
    items = document.get("observations")
    if not isinstance(items, list) or len(items) > 30:
        raise SurveillanceInvalide("Registre d'observations invalide")
    valeurs = {}
    for item in items:
        if not isinstance(item, dict):
            raise SurveillanceInvalide("Observation mal formée")
        identifiant, digest = item.get("source_id"), item.get("empreinte")
        if (not isinstance(identifiant, str) or not IDENTIFIANT.fullmatch(identifiant)
                or identifiant in valeurs or not isinstance(digest, str)
                or not EMPREINTE.fullmatch(digest)):
            raise SurveillanceInvalide("Observation sans origine ou empreinte")
        historique = item.get("historique", [])
        if not isinstance(historique, list) or len(historique) > HISTORIQUE_MAX:
            raise SurveillanceInvalide("Historique incompatible")
        valeurs[identifiant] = item
    return valeurs


def collecter(
    sources: list[dict], precedent: dict, moment: datetime,
    *, acquerir: Callable[[dict], tuple[bytes, str]] = obtenir,
) -> tuple[dict, dict]:
    """Observer les cinq sources en conservant l'historique et les erreurs."""
    if moment.tzinfo is None:
        raise SurveillanceInvalide("Instant de collecte sans fuseau")
    ancien = verifier_etat(precedent)
    autorises = {item["id"] for item in sources}
    if not set(ancien).issubset(autorises):
        raise SurveillanceInvalide("Observation historique sans source autorisée")
    courant = {k: dict(v) for k, v in ancien.items()}
    changements, controles = [], []
    horodatage = moment.astimezone(timezone.utc).isoformat(timespec="seconds")
    for source in sources:
        identifiant = source["id"]
        try:
            contenu, media = acquerir(source)
            digest = empreinte_document(contenu, source["format"])
            precedente = ancien.get(identifiant)
            if precedente and precedente.get("url") != source["url"]:
                raise SurveillanceInvalide("Adresse modifiée : validation requise")
            etat = "identique"
            if precedente is None:
                etat = "premiere_observation"
                courant[identifiant] = {
                    "source_id": identifiant,
                    "programme": source["programme"],
                    "nature_document": source["nature_document"],
                    "url": source["url"],
                    "format": source["format"],
                    "empreinte": digest,
                    "observe_initialement_le": horodatage,
                    "dernier_changement_le": horodatage,
                    "historique": [],
                }
            elif precedente["empreinte"] != digest:
                etat = "modification_a_requalifier"
                historique = list(precedente.get("historique", []))
                historique.append({
                    "observe_le": horodatage,
                    "empreinte_avant": precedente["empreinte"],
                    "empreinte_apres": digest,
                })
                courant[identifiant] = {
                    **precedente,
                    "empreinte": digest,
                    "dernier_changement_le": horodatage,
                    "historique": historique[-HISTORIQUE_MAX:],
                }
            if etat != "identique":
                changements.append({"source_id": identifiant, "statut": etat})
            controles.append({"source_id": identifiant, "etat": etat,
                              "format_recu": media, "octets": len(contenu),
                              "empreinte": digest})
        except (HTTPError, URLError, TimeoutError, OSError, ValueError,
                UnicodeDecodeError) as exc:
            controles.append({"source_id": identifiant, "etat": "echec_observation",
                              "cause": type(exc).__name__})
            # Le dernier contenu confirmé n'est jamais effacé.
    nouvel_etat = {
        "version": 1,
        "observations": [courant[x] for x in sorted(courant)],
    }
    bilan = {
        "version": 1,
        "controle_le": horodatage,
        "points_controles": len(sources),
        "succes": sum(item["etat"] != "echec_observation" for item in controles),
        "echecs": sum(item["etat"] == "echec_observation" for item in controles),
        "modifications_documentaires": changements,
        "transitions_institutionnelles_inferees": 0,
        "controles": controles,
    }
    return nouvel_etat, bilan


def resume(bilan: dict) -> str:
    lignes = [
        "## FRONTIÈRE — suivi documentaire des programmes ANR",
        f"Contrôle {bilan['controle_le']} ; "
        f"{bilan['succes']}/{bilan['points_controles']} points accessibles.",
        "Une modification du texte ou du PDF indique une nouvelle lecture "
        "à effectuer, jamais un financement ni un impact constaté.",
        "",
        "| Publication | État |",
        "| --- | --- |",
    ]
    lignes.extend(f"| {item['source_id']} | {item['etat']} |"
                  for item in bilan["controles"])
    return "\n".join(lignes) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--racine", type=Path, default=RACINE)
    parser.add_argument("--bilan-json", type=Path)
    parser.add_argument("--bilan-markdown", type=Path)
    args = parser.parse_args()
    try:
        cfg = json.loads((args.racine / SOURCES).read_text(encoding="utf-8"))
        ancien = json.loads((args.racine / ETAT).read_text(encoding="utf-8"))
        sources = charger_sources(cfg)
        prochain, bilan = collecter(sources, ancien, datetime.now(timezone.utc))
        cible = args.racine / ETAT
        if prochain != ancien:
            cible.write_text(json.dumps(prochain, ensure_ascii=False, indent=2)
                             + "\n", encoding="utf-8")
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
    except (OSError, ValueError, TypeError) as exc:
        print(f"Surveillance impossible : {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
