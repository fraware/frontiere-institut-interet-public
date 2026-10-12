"""Collecter des signaux publics institutionnels RSS/Atom et Bluesky.

Les signaux sont des publications observées, non des besoins internes établis.
Toute source réseau doit figurer dans un catalogue fermé. Les erreurs de collecte
préservent les observations précédentes et figurent au bilan du cycle.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import html
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET

RACINE = Path(__file__).resolve().parents[1]
DOSSIER = RACINE / "institutionnel" / "flux_publics"
CONFIG = DOSSIER / "sources_v1.json"
INDEX = DOSSIER / "observations.json"
ETAT = DOSSIER / "etat_collecte.json"
API_BSKY = "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"
MAX_REPONSE = 2_000_000
MAX_ELEMENTS_SOURCE = 100
MAX_OBSERVATIONS = 25_000
DOMAINES_AUTORISES = frozenset({"anr.fr", "www.service-public.gouv.fr", "public.api.bsky.app"})
IDENTITE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,60}$")


class CollecteInvalide(ValueError):
    """Une source, un lot ou une publication ne satisfait pas au contrat."""


class SansRedirection(HTTPRedirectHandler):
    """Bloquer les redirections, y compris vers une adresse réseau privée."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CollecteInvalide("Redirection imprévue")


def empreinte(obj: object) -> str:
    """Produire une empreinte déterministe d'un objet JSON."""
    brut = json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(brut).hexdigest()


def _texte(obj: object, taille: int = 700) -> str:
    if not isinstance(obj, str):
        return ""
    return " ".join(html.unescape(re.sub(r"<[^>]{0,200}>", " ", obj)).split())[:taille]


def _adresse(url: object, domaine: str) -> str:
    if not isinstance(url, str) or len(url) > 2048:
        raise CollecteInvalide("URL incorrecte")
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.hostname != domaine
            or parts.username or parts.password or parts.port not in (None, 443)
            or parts.fragment):
        raise CollecteInvalide("URL hors origine autorisée")
    return url


def verifier_sources(document: object) -> list[dict]:
    """Contrôler un catalogue explicite, sans découverte réseau arbitraire."""
    if not isinstance(document, dict) or document.get("version") != 1:
        raise CollecteInvalide("Version des sources non reconnue")
    sources = document.get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= 200:
        raise CollecteInvalide("Nombre de sources incorrect")
    vus = set()
    for src in sources:
        if not isinstance(src, dict):
            raise CollecteInvalide("Source mal formée")
        identifiant = src.get("id")
        if not isinstance(identifiant, str) or not IDENTITE.fullmatch(identifiant):
            raise CollecteInvalide("Identifiant de source invalide")
        if identifiant in vus:
            raise CollecteInvalide("Identifiant de source répété")
        vus.add(identifiant)
        if type(src.get("active")) is not bool:
            raise CollecteInvalide("Activation non booléenne")
        if (type(src.get("cadence_heures")) is not int
                or not 1 <= src["cadence_heures"] <= 168):
            raise CollecteInvalide("Cadence incorrecte")
        if not _texte(src.get("nom")) or not _texte(src.get("categorie")):
            raise CollecteInvalide("Nom ou catégorie manquants")
        domaine = src.get("domaine")
        if not isinstance(domaine, str) or domaine not in DOMAINES_AUTORISES:
            raise CollecteInvalide("Domaine hors liste des éditeurs publics autorisés")
        if src.get("type") == "rss":
            _adresse(src.get("url"), domaine)
        elif src.get("type") == "bluesky":
            if domaine != "public.api.bsky.app":
                raise CollecteInvalide("AppView Bluesky inattendue")
            acteur = src.get("acteur")
            did = src.get("did")
            if (not isinstance(acteur, str)
                    or not re.fullmatch(r"[a-zA-Z0-9.-]{4,150}", acteur)
                    or not isinstance(did, str)
                    or not re.fullmatch(r"did:plc:[a-z2-7]{24}", did)):
                raise CollecteInvalide("Identité sociale non conforme")
        else:
            raise CollecteInvalide("Type de source non pris en charge")
    return sources


def adresse_requete(source: dict) -> str:
    """Émettre uniquement l'URL fixe du catalogue ou l'appel social prévu."""
    if source["type"] == "rss":
        return _adresse(source["url"], source["domaine"])
    return API_BSKY + "?" + urlencode({
        "actor": source["did"], "limit": MAX_ELEMENTS_SOURCE,
        "filter": "posts_no_replies",
    })


def obtenir(source: dict, url: str) -> bytes:
    """Lire un volume borné, sans suivre de redirection ni de lien de publication."""
    if url != adresse_requete(source):
        raise CollecteInvalide("La requête diffère de l'adresse autorisée")
    entetes = {"Accept": "application/xml, application/rss+xml, application/atom+xml, application/json",
               "User-Agent": "FRONTIERE-veille-publique/1.0"}
    with build_opener(SansRedirection).open(
        Request(url, headers=entetes), timeout=25
    ) as reponse:
        if reponse.status != 200 or reponse.geturl() != url:
            raise CollecteInvalide("Réponse inattendue")
        contenu = reponse.read(MAX_REPONSE + 1)
    if len(contenu) > MAX_REPONSE:
        raise CollecteInvalide("Réponse supérieure au plafond")
    return contenu


def _date(valeur: object) -> str | None:
    if not isinstance(valeur, str) or not valeur.strip():
        return None
    try:
        dt = datetime.fromisoformat(valeur.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = parsedate_to_datetime(valeur)
        except (ValueError, TypeError, IndexError):
            return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def _element(parent: ET.Element, nom: str) -> str:
    for item in parent:
        if item.tag.rsplit("}", 1)[-1] == nom:
            return "".join(item.itertext()).strip()
    return ""


def extraire_syndication(contenu: bytes, source: dict) -> list[dict]:
    """Accepter les formats RSS 2.0 et Atom publics, sans entités DTD."""
    if b"<!DOCTYPE" in contenu.upper() or b"<!ENTITY" in contenu.upper():
        raise CollecteInvalide("DTD et entités XML interdites")
    try:
        racine = ET.fromstring(contenu)
    except ET.ParseError as exc:
        raise CollecteInvalide("Flux XML incorrect") from exc
    forme = racine.tag.rsplit("}", 1)[-1].lower()
    if forme not in {"rss", "feed"}:
        raise CollecteInvalide("Format XML non pris en charge")
    atom = forme == "feed"
    entrees = (
        [e for e in racine if e.tag.rsplit("}", 1)[-1] == "entry"]
        if atom else racine.findall("./channel/item")
    )
    if len(entrees) > 1000:
        raise CollecteInvalide("Trop d'entrées pour un seul flux")
    resultats = []
    for item in entrees[:MAX_ELEMENTS_SOURCE]:
        titre = _texte(_element(item, "title"), 260)
        lien = _element(item, "link")
        if atom:
            lien = next((
                e.attrib.get("href", "") for e in item
                if e.tag.rsplit("}", 1)[-1] == "link"
                and e.attrib.get("rel", "alternate") == "alternate"
            ), "")
        cle = _element(item, "id" if atom else "guid") or lien
        if not cle or not titre:
            continue
        # Lien conservé comme une référence, jamais suivi par le collecteur.
        p = urlsplit(lien)
        lien_public = (
            lien if p.scheme == "https" and p.hostname
            and not p.username and not p.password and len(lien) <= 2048
            else None
        )
        date = _date(_element(item, "updated" if atom else "pubDate"))
        texte = _texte(_element(item, "summary" if atom else "description"), 500)
        resultats.append({
            "cle_distante": _texte(cle, 900), "titre": titre,
            "description": texte, "lien": lien_public, "date_publication": date,
        })
    return resultats


def extraire_bluesky(contenu: bytes, source: dict) -> list[dict]:
    """Conserver seulement les publications de l'auteur DID officiel déclaré."""
    try:
        document = json.loads(contenu)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollecteInvalide("Réponse sociale JSON illisible") from exc
    if not isinstance(document, dict) or not isinstance(document.get("feed"), list):
        raise CollecteInvalide("Liste sociale absente")
    elements = document["feed"]
    if len(elements) > MAX_ELEMENTS_SOURCE:
        raise CollecteInvalide("Nombre de publications inattendu")
    resultats = []
    for entree in elements:
        if not isinstance(entree, dict) or entree.get("reason"):
            continue  # Ne pas attribuer un repartage à l'institution.
        post = entree.get("post")
        if not isinstance(post, dict) or not isinstance(post.get("author"), dict):
            continue
        if post["author"].get("did") != source["did"]:
            continue
        record = post.get("record")
        uri = post.get("uri")
        if not isinstance(record, dict) or not isinstance(uri, str):
            continue
        prefixe = "at://" + source["did"] + "/app.bsky.feed.post/"
        if not uri.startswith(prefixe):
            continue
        identifiant = uri[len(prefixe):]
        if not re.fullmatch(r"[a-zA-Z0-9]{4,100}", identifiant):
            continue
        contenu_post = _texte(record.get("text"), 700)
        if not contenu_post:
            continue
        resultats.append({
            "cle_distante": uri,
            "titre": contenu_post[:260],
            "description": contenu_post[:500],
            "lien": "https://bsky.app/profile/" + quote(source["acteur"]) + "/post/" + identifiant,
            "date_publication": _date(record.get("createdAt")),
        })
    return resultats


def normaliser(source: dict, entree: dict, horodatage: str) -> dict:
    """Calculer une identité stable et une empreinte de la version observée."""
    identite = empreinte([source["id"], entree["cle_distante"]])
    noyau = {
        "source_id": source["id"], "identifiant_publication": identite,
        "categorie_source": source["categorie"],
        "nature_signal": "publication_publique_non_qualifiee",
        "titre": entree["titre"], "description": entree["description"],
        "lien": entree["lien"], "date_publication": entree["date_publication"],
    }
    return {
        **noyau, "empreinte_contenu": empreinte(noyau),
        "observe_initialement_le": horodatage, "mis_a_jour_le": horodatage,
        "nombre_revisions": 0,
    }


def executer(
    catalogue: dict, ancien_index: dict, ancien_etat: dict,
    telecharger=obtenir, horodatage: str | None = None,
) -> tuple[dict, dict]:
    """Enregistrer les entrées sans effacer une source indisponible."""
    sources = verifier_sources(catalogue)
    date_cycle = horodatage or datetime.now(timezone.utc).isoformat(timespec="seconds")
    if _date(date_cycle) is None:
        raise CollecteInvalide("Horodatage invalide")
    if not isinstance(ancien_index, dict) or ancien_index.get("version") not in (None, 1):
        raise CollecteInvalide("Ancien index invalide")
    anciens = ancien_index.get("observations", [])
    if not isinstance(anciens, list):
        raise CollecteInvalide("Ancien index illisible")
    index = {}
    for entree in anciens:
        if not isinstance(entree, dict) or not isinstance(entree.get("identifiant_publication"), str):
            raise CollecteInvalide("Ancienne publication mal formée")
        identifiant = entree["identifiant_publication"]
        if identifiant in index:
            raise CollecteInvalide("Ancien identifiant répété")
        index[identifiant] = entree
    if len(index) > MAX_OBSERVATIONS:
        raise CollecteInvalide("Ancien index dépasse la limite")
    precedents = {
        src["id"]: src for src in ancien_etat.get("sources", [])
    } if isinstance(ancien_etat, dict) else {}
    bilans = []
    reussites = nouvelles = revisions = 0
    for src in sources:
        etat = {
            "id": src["id"], "nom": src["nom"],
            "cadence_heures": src["cadence_heures"], "actif": src["active"],
            "etat": "inactif" if not src["active"] else "echec",
            "dernier_succes": precedents.get(src["id"], {}).get("dernier_succes"),
            "elements_lus": 0, "nouveaux": 0, "revisions": 0,
            "erreur": None,
        }
        if not src["active"]:
            bilans.append(etat)
            continue
        try:
            url = adresse_requete(src)
            brut = telecharger(src, url)
            if not isinstance(brut, bytes) or len(brut) > MAX_REPONSE:
                raise CollecteInvalide("Réponse non bornée")
            elements = (
                extraire_syndication(brut, src)
                if src["type"] == "rss" else extraire_bluesky(brut, src)
            )
            etat["elements_lus"] = len(elements)
            for element in elements:
                courant = normaliser(src, element, date_cycle)
                identifiant = courant["identifiant_publication"]
                precedent = index.get(identifiant)
                if precedent is None:
                    if len(index) >= MAX_OBSERVATIONS:
                        raise CollecteInvalide("Index plein : migration externe nécessaire")
                    index[identifiant] = courant
                    nouvelles += 1
                    etat["nouveaux"] += 1
                elif precedent.get("empreinte_contenu") != courant["empreinte_contenu"]:
                    courant["observe_initialement_le"] = precedent["observe_initialement_le"]
                    courant["nombre_revisions"] = precedent.get("nombre_revisions", 0) + 1
                    index[identifiant] = courant
                    revisions += 1
                    etat["revisions"] += 1
            etat["etat"] = "succes"
            etat["dernier_succes"] = date_cycle
            reussites += 1
        except (CollecteInvalide, HTTPError, URLError, TimeoutError, OSError,
                UnicodeDecodeError, ValueError, ET.ParseError) as exc:
            etat["erreur"] = ("HTTP_" + str(exc.code)) if isinstance(exc, HTTPError) else type(exc).__name__
        bilans.append(etat)
    if not reussites:
        raise CollecteInvalide("Aucune source récupérée : aucun état écrasé")
    return (
        {"version": 1, "observations": [
            index[key] for key in sorted(index)
        ]},
        {
            "version": 1, "cycle_le": date_cycle,
            "sources": bilans, "sources_reussies": reussites,
            "sources_en_echec": sum(s["etat"] == "echec" for s in bilans),
            "nouveaux_signaux": nouvelles, "revisions": revisions,
            "nombre_signaux_distincts": len(index),
            "couverture_exhaustive_des_besoins_publics": False,
            "qualification_de_besoins_effectuee": False,
        },
    )


def _charger(chemin: Path, defaut: dict) -> dict:
    if not chemin.exists():
        return defaut
    return json.loads(chemin.read_text(encoding="utf-8"))


def _ecrire(chemin: Path, contenu: dict) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temp = chemin.with_name(chemin.name + ".temp")
    temp.write_text(
        json.dumps(contenu, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp.replace(chemin)


def main() -> None:
    """Collecter les sources inscrites au registre depuis la racine du dépôt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configuration", type=Path, default=CONFIG)
    parser.add_argument("--index", type=Path, default=INDEX)
    parser.add_argument("--etat", type=Path, default=ETAT)
    args = parser.parse_args()
    try:
        index, bilan = executer(
            _charger(args.configuration, {}),
            _charger(args.index, {"version": 1, "observations": []}),
            _charger(args.etat, {"version": 1, "sources": []}),
        )
        _ecrire(args.index, index)
        _ecrire(args.etat, bilan)
        print(json.dumps(bilan, ensure_ascii=False, indent=2))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Veille publique interrompue : {type(exc).__name__}\n")


if __name__ == "__main__":
    main()
