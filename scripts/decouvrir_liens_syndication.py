"""Découvrir des liens RSS/Atom déclarés sur des pages institutionnelles connues.

La découverte ne valide ni le format ni la légitimité d'un nouveau flux :
aucune adresse découverte n'est téléchargée ou activée automatiquement.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

RACINE = Path(__file__).resolve().parents[1]
CONFIG = RACINE / "institutionnel/canaux_publics/sites_verifies_v1.json"
SORTIE = RACINE / "institutionnel/canaux_publics/decouvertes_sites.json"
HOTES = frozenset({
    "anr.fr", "www.economie.gouv.fr", "www.ecologie.gouv.fr",
    "www.ccsd.cnrs.fr", "lejournal.cnrs.fr",
})
MAX_OCTETS = 800_000
MAX_LIENS = 100
FORMAT_SYNDICATION = {"application/rss+xml", "application/atom+xml"}
ID = re.compile(r"^[a-z0-9_]{3,65}$")


class DecouverteInvalide(ValueError):
    """Un site ou un document ne respecte pas le périmètre de collecte."""


def verifier_config(config: object) -> list[dict]:
    """Contrôler la liste fermée des sites réellement autorisés."""
    if not isinstance(config, dict) or config.get("version") != "canaux-web-verifies-v1":
        raise DecouverteInvalide("Version de catalogue incorrecte")
    pages = config.get("pages")
    if not isinstance(pages, list) or not 1 <= len(pages) <= 20:
        raise DecouverteInvalide("Nombre de pages incorrect")
    vus = set()
    for page in pages:
        if not isinstance(page, dict):
            raise DecouverteInvalide("Page non structurée")
        pid = page.get("id")
        if not isinstance(pid, str) or not ID.fullmatch(pid) or pid in vus:
            raise DecouverteInvalide("Identifiant de page absent ou répété")
        vus.add(pid)
        hote = page.get("hote")
        if hote not in HOTES:
            raise DecouverteInvalide("Hôte inconnu")
        p = urlsplit(page.get("url", ""))
        if (p.scheme != "https" or p.hostname != hote or p.port not in (None, 443)
                or p.username or p.password or p.fragment or len(page["url"]) > 1200):
            raise DecouverteInvalide("URL officielle hors périmètre")
        if not isinstance(page.get("organisme"), str) or not page["organisme"].strip():
            raise DecouverteInvalide("Organisme non renseigné")
    return pages


def normaliser_lien(base: str, relatif: str, hote: str) -> str | None:
    """Ne conserver que les liens HTTPS du même hôte explicitement référencé."""
    if not isinstance(relatif, str) or not relatif.strip() or len(relatif) > 1500:
        return None
    if relatif.lstrip().startswith(("#", "javascript:", "data:")):
        return None
    url = urljoin(base, relatif.strip())
    p = urlsplit(url)
    if (p.scheme != "https" or p.hostname != hote or p.port not in (None, 443)
            or p.username or p.password):
        return None
    return urlunsplit((p.scheme, p.netloc, p.path, p.query, ""))


class LiensSyndication(HTMLParser):
    """Lire des déclarations de flux ou liens publics explicitement évocateurs."""

    def __init__(self, url: str, hote: str):
        super().__init__(convert_charrefs=True)
        self.url = url
        self.hote = hote
        self.resultat: dict[str, dict] = {}
        self._ancre: dict | None = None

    def _ajouter(self, lien: str, raison: str, libelle: str) -> None:
        normalise = normaliser_lien(self.url, lien, self.hote)
        page_courante = normaliser_lien(self.url, self.url, self.hote)
        if normalise is None or normalise == page_courante or len(self.resultat) >= MAX_LIENS:
            return
        self.resultat.setdefault(normalise, {
            "url": normalise, "methode": raison, "libelle": libelle.strip()[:180],
            "format_confirme": False, "contenu_telecharge": False,
        })

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "link":
            types = (a.get("type") or "").lower().split(";")[0].strip()
            relations = (a.get("rel") or "").lower().split()
            if "alternate" in relations and types in FORMAT_SYNDICATION:
                self._ajouter(a.get("href") or "", "lien_alternatif_html", a.get("title") or "")
        if tag == "a":
            self._ancre = {"href": a.get("href") or "", "texte": ""}

    def handle_data(self, data: str) -> None:
        if self._ancre is not None:
            self._ancre["texte"] = (self._ancre["texte"] + data)[:200]

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._ancre is not None:
            href = self._ancre["href"]
            titre = self._ancre["texte"].strip()
            chemin = urlsplit(href).path.lower()
            flux_explicitement_declare = (
                "rss" in chemin or "atom" in chemin or chemin.endswith("/feed/")
                or "flux rss" in titre.lower() or "flux atom" in titre.lower()
            )
            if flux_explicitement_declare:
                self._ajouter(href, "lien_html_evoquant_flux", titre)
            self._ancre = None


class RedirectionControlee(HTTPRedirectHandler):
    """Tolérer une redirection HTTPS sur le même hôte seulement."""

    def __init__(self, hote: str):
        super().__init__()
        self.hote = hote

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if normaliser_lien(req.full_url, newurl, self.hote) is None:
            raise DecouverteInvalide("Redirection hors hôte officiel")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def lire_page(page: dict) -> str:
    """Lire le HTML borné depuis un site officiel connu, sans requête de flux."""
    request = Request(page["url"], headers={
        "User-Agent": "FRONTIERE-decouverte-canaux-publics/1.0",
        "Accept": "text/html,application/xhtml+xml",
    })
    with build_opener(RedirectionControlee(page["hote"])).open(request, timeout=24) as response:
        if response.status != 200 or urlsplit(response.geturl()).hostname != page["hote"]:
            raise DecouverteInvalide("Réponse inattendue")
        ctype = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if ctype not in {"text/html", "application/xhtml+xml"}:
            raise DecouverteInvalide("Document non HTML")
        octets = response.read(MAX_OCTETS + 1)
        if len(octets) > MAX_OCTETS:
            raise DecouverteInvalide("Page supérieure au plafond")
        encodage = response.headers.get_content_charset() or "utf-8"
    try:
        return octets.decode(encodage)
    except (UnicodeDecodeError, LookupError) as exc:
        raise DecouverteInvalide("Encodage HTML incorrect") from exc


def analyser(page: dict, html: str) -> list[dict]:
    """Extraire les candidats déclarés sans les ouvrir."""
    if not isinstance(html, str) or len(html.encode("utf-8")) > MAX_OCTETS:
        raise DecouverteInvalide("Contenu HTML incorrect ou excessif")
    lecteur = LiensSyndication(page["url"], page["hote"])
    lecteur.feed(html)
    lecteur.close()
    return [lecteur.resultat[url] for url in sorted(lecteur.resultat)]


def executer(config: dict, ancien: dict, *, recuperer=lire_page,
             instant: str | None = None) -> dict:
    """Conserver par site l'index précédent lors d'une indisponibilité."""
    sites = verifier_config(config)
    if not isinstance(ancien, dict) or ancien.get("version") not in (None, "decouverte-canaux-v1"):
        raise DecouverteInvalide("Ancien inventaire illisible")
    precedents = ancien.get("sites", [])
    if not isinstance(precedents, list) or any(not isinstance(x, dict) for x in precedents):
        raise DecouverteInvalide("Anciennes sources incorrectes")
    connus = {p.get("id"): p for p in precedents}
    instant = instant or datetime.now(timezone.utc).isoformat(timespec="seconds")
    reussites, echecs, candidats = 0, [], 0
    for site in sites:
        try:
            liens = analyser(site, recuperer(site))
            connus[site["id"]] = {
                "id": site["id"], "organisme": site["organisme"],
                "page_source": site["url"], "observe_le": instant,
                "candidats": liens, "aucune_absence_de_flux_prouvee": True,
            }
            reussites += 1
            candidats += len(liens)
        except (DecouverteInvalide, HTTPError, URLError, OSError, TimeoutError, ValueError) as exc:
            echecs.append({"id": site["id"], "motif":
                           "HTTP_" + str(exc.code) if isinstance(exc, HTTPError) else type(exc).__name__})
    if reussites == 0:
        raise DecouverteInvalide("Aucun site consultable : état antérieur préservé")
    return {
        "version": "decouverte-canaux-v1", "controle_le": instant,
        "sites": [connus[k] for k in sorted(connus)],
        "sites_reussis": reussites, "sites_en_echec": echecs,
        "liens_candidats_dans_les_sites_reussis": candidats,
        "formats_des_candidats_verifies": 0,
        "comptes_sociaux_authentifies_par_cette_collecte": 0,
        "couverture_nationale": False,
    }


def main() -> None:
    """Publier les liens candidats relevés sur des pages du registre fermé."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configuration", type=Path, default=CONFIG)
    parser.add_argument("--sortie", type=Path, default=SORTIE)
    args = parser.parse_args()
    try:
        conf = json.loads(args.configuration.read_text(encoding="utf-8"))
        precedent = json.loads(args.sortie.read_text(encoding="utf-8")) if args.sortie.exists() else {}
        resultat = executer(conf, precedent)
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        temp = args.sortie.with_suffix(".json.tmp")
        temp.write_text(json.dumps(resultat, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp.replace(args.sortie)
        print(json.dumps({k: v for k, v in resultat.items() if k != "sites"}, ensure_ascii=False))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Découverte non publiée : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
