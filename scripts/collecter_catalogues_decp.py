"""Inventorier les ressources DECP officielles sans télécharger les marchés eux-mêmes.

Le relevé porte sur des métadonnées d'attribution, jamais sur des besoins
administratifs prospectifs. Les erreurs d'un catalogue ne remplacent pas son
dernier relevé réussi.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

RACINE = Path(__file__).resolve().parents[1]
CONFIG = RACINE / "institutionnel/decp/sources_v1.json"
ETAT = RACINE / "institutionnel/decp/etat_ressources.json"
URLS = frozenset({
    "https://www.data.gouv.fr/api/1/datasets/donnees-essentielles-de-la-commande-publique-fichiers-consolides/",
    "https://www.data.gouv.fr/api/1/datasets/donnees-essentielles-de-la-commande-publique-transmises-via-le-pes-marche-depuis-2024/",
})
MAX_OCTETS = 32_000_000
MAX_RESSOURCES = 30_000
IDENTIFIANT = re.compile(r"^[a-z0-9_]{5,90}$")


class ErreurDECP(ValueError):
    """Le document distant ne permet pas un relevé fiable."""


class RefuserRedirection(HTTPRedirectHandler):
    """Interdire toute redirection hors de l'URL officielle configurée."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ErreurDECP("Redirection distante inattendue")


def _texte(valeur: object, taille: int = 220) -> str:
    return valeur.strip()[:taille] if isinstance(valeur, str) else ""


def _date_iso(valeur: object) -> str | None:
    if not isinstance(valeur, str) or not valeur.strip():
        return None
    try:
        dt = datetime.fromisoformat(valeur.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.isoformat() if dt.tzinfo is not None else None


def verifier_catalogue(configuration: dict) -> list[dict]:
    """Limiter les téléchargements de métadonnées aux deux origines vérifiées."""
    if not isinstance(configuration, dict) or configuration.get("version") != "decp-metadonnees-v1":
        raise ErreurDECP("Version du registre inconnue")
    sources = configuration.get("sources")
    if not isinstance(sources, list) or len(sources) != 2:
        raise ErreurDECP("Deux sources officielles sont attendues")
    vus = set()
    for source in sources:
        if not isinstance(source, dict):
            raise ErreurDECP("Source non structurée")
        identifiant = source.get("id")
        if not isinstance(identifiant, str) or not IDENTIFIANT.fullmatch(identifiant):
            raise ErreurDECP("Identifiant de source mal formé")
        if identifiant in vus:
            raise ErreurDECP("Source répétée")
        vus.add(identifiant)
        if source.get("url") not in URLS:
            raise ErreurDECP("URL absente de la liste fermée")
        if (type(source.get("limite_ressources_indexees")) is not int
                or not 1 <= source["limite_ressources_indexees"] <= 200):
            raise ErreurDECP("Limite de ressources incorrecte")
        if not _texte(source.get("producteur")) or not _texte(source.get("type_observation")):
            raise ErreurDECP("Provenance ou portée manquante")
        p = urlsplit(source.get("page", ""))
        if p.scheme != "https" or p.hostname != "www.data.gouv.fr":
            raise ErreurDECP("Page de référence incorrecte")
    return sources


def telecharger(source: dict) -> dict:
    """Accéder à la fiche JSON officielle et jamais aux URLs des ressources."""
    url = source["url"]
    if url not in URLS:
        raise ErreurDECP("URL non autorisée")
    demande = Request(url, headers={
        "User-Agent": "FRONTIERE-catalogue-DECP/1.0",
        "Accept": "application/json",
    })
    with build_opener(RefuserRedirection).open(demande, timeout=55) as response:
        if response.status != 200 or response.geturl() != url:
            raise ErreurDECP("Réponse HTTP inattendue")
        contenu = response.read(MAX_OCTETS + 1)
    if len(contenu) > MAX_OCTETS:
        raise ErreurDECP("Catalogue de métadonnées trop volumineux")
    try:
        resultat = json.loads(contenu)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ErreurDECP("Réponse JSON incorrecte") from exc
    if not isinstance(resultat, dict):
        raise ErreurDECP("Fiche non structurée")
    return resultat


def _licence(valeur: object) -> str | None:
    if isinstance(valeur, dict):
        valeur = valeur.get("id")
    return _texte(valeur, 80) or None


def reduire_fiche(source: dict, fiche: dict) -> dict:
    """Conserver des métadonnées bornées et une empreinte de TOUT le catalogue."""
    ressources = fiche.get("resources")
    if not isinstance(ressources, list) or len(ressources) > MAX_RESSOURCES:
        raise ErreurDECP("Inventaire de ressources absent ou excessif")
    identifiant_jeu = _texte(fiche.get("id"), 100)
    if not identifiant_jeu:
        raise ErreurDECP("Identifiant du jeu inconnu")
    connus = set()
    inventaire = []
    formats = Counter()
    for ressource in ressources:
        if not isinstance(ressource, dict):
            raise ErreurDECP("Ressource mal formée")
        rid = _texte(ressource.get("id"), 120)
        if not rid or rid in connus:
            raise ErreurDECP("Identifiant de ressource absent ou répété")
        connus.add(rid)
        fmt = _texte(ressource.get("format"), 30).lower() or "inconnu"
        formats[fmt] += 1
        taille = ressource.get("filesize")
        if type(taille) is not int or taille < 0:
            taille = None
        inventaire.append({
            "id": rid,
            "titre": _texte(ressource.get("title"), 220),
            "format": fmt,
            "taille_octets_declaree": taille,
            "modifie_le": _date_iso(ressource.get("last_modified")),
        })
    # L'empreinte couvre TOUS les identifiants et champs ci-dessus,
    # même si l'échantillon publié est limité.
    trie = sorted(inventaire, key=lambda r: r["id"])
    canon = json.dumps(trie, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    empreinte = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    recents = sorted(
        inventaire, key=lambda r: (r["modifie_le"] or "", r["id"]), reverse=True
    )[:source["limite_ressources_indexees"]]
    return {
        "source_id": source["id"], "jeu_id": identifiant_jeu,
        "type_observation": source["type_observation"],
        "page": source["page"], "titre": _texte(fiche.get("title")),
        "licence_declaree": _licence(fiche.get("license")),
        "actualise_le": _date_iso(fiche.get("last_update")),
        "nombre_ressources_total": len(inventaire),
        "nombre_ressources_indexees": len(recents),
        "nombre_ressources_non_detaillees": len(inventaire) - len(recents),
        "formats": dict(sorted(formats.items())),
        "empreinte_inventaire_complet": empreinte,
        "ressources_recentes": recents,
        "contenu_des_fichiers_telecharge": False,
        "completude_des_marches_etablie": False,
        "nouveaux_besoins_prospectifs_deduits": 0,
    }


def executer(config: dict, ancien: dict, *, recuperer=telecharger, instant: str | None = None) -> dict:
    """Préserver chaque dernière observation réussie si une source échoue."""
    sources = verifier_catalogue(config)
    if not isinstance(ancien, dict) or ancien.get("version") not in (None, "decp-metadonnees-v1"):
        raise ErreurDECP("Ancien état invalide")
    precedents = ancien.get("catalogues", [])
    if not isinstance(precedents, list) or any(not isinstance(p, dict) for p in precedents):
        raise ErreurDECP("Anciens catalogues invalides")
    connus = {p.get("source_id"): p for p in precedents}
    if len(connus) != len(precedents):
        raise ErreurDECP("Anciennes sources répétées")
    releve = instant or datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not _date_iso(releve):
        raise ErreurDECP("Horodatage du cycle incorrect")
    reussites, echecs, changemens = 0, [], 0
    for source in sources:
        try:
            nouveau = reduire_fiche(source, recuperer(source))
            precedent = connus.get(source["id"])
            if precedent and precedent.get("empreinte_inventaire_complet") != nouveau["empreinte_inventaire_complet"]:
                changemens += 1
            nouveau["observe_le"] = releve
            connus[source["id"]] = nouveau
            reussites += 1
        except (ErreurDECP, HTTPError, URLError, OSError, TimeoutError, ValueError) as exc:
            echecs.append({"source_id": source["id"],
                           "motif": "HTTP_" + str(exc.code) if isinstance(exc, HTTPError) else type(exc).__name__})
    if reussites == 0:
        raise ErreurDECP("Aucun catalogue accessible : ancien état conservé")
    return {
        "version": "decp-metadonnees-v1", "controle_le": releve,
        "sources_reussies": reussites, "sources_echouees": echecs,
        "catalogues": [connus[k] for k in sorted(connus)],
        "inventaires_complets_telecharges": 0,
        "nombre_catalogues_avec_modifications": changemens,
        "qualifie_des_besoins_actuels": False,
    }


def main() -> None:
    """Exécuter un relevé de métadonnées avec écriture atomique d'un état."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sources", type=Path, default=CONFIG)
    p.add_argument("--sortie", type=Path, default=ETAT)
    args = p.parse_args()
    try:
        sources = json.loads(args.sources.read_text(encoding="utf-8"))
        ancien = json.loads(args.sortie.read_text(encoding="utf-8")) if args.sortie.exists() else {}
        resultat = executer(sources, ancien)
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        temporaire = args.sortie.with_suffix(".json.tmp")
        temporaire.write_text(json.dumps(resultat, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporaire.replace(args.sortie)
        print(json.dumps({k: v for k, v in resultat.items() if k != "catalogues"}, ensure_ascii=False))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        p.exit(1, f"Collecte DECP interrompue : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
