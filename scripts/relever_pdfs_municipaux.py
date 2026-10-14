"""Relever les octets de trois PDF municipaux officiels et leurs indices paginés.

Le PDF n'est ni publié à nouveau ni transcrit intégralement. Un mot repéré sur
une page ne prouve ni un usage effectif ni le résultat d'une prestation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

RACINE = Path(__file__).resolve().parents[1]
DOSSIER = RACINE / "institutionnel" / "pieces_publiques"
CONFIG = DOSSIER / "sources_pdfs_municipaux_v1.json"
SORTIE = DOSSIER / "observations_pdfs_municipaux.json"
MAX_PDF = 15_000_000
MAX_PAGES = 150
CIBLES = {
    "esc-2025-02-13": (
        "https://www.escalquens.fr/wp-content/uploads/2025/02/"
        "D%C3%A9lib%C3%A9rations-CM-2025-02-13.pdf"
    ),
    "auz-2025-06-18": (
        "https://www.auzeville.fr/wp-content/uploads/2025/06/PV-18-06-25.pdf"
    ),
    "esc-2025-02-13-pv": (
        "https://www.escalquens.fr/wp-content/uploads/2025/04/PV-CM-2025-02-13.pdf"
    ),
}


class SourceInvalide(ValueError):
    """La pièce, sa provenance ou ses métadonnées sont incohérentes."""


class SansRedirection(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SourceInvalide("Redirection non autorisée")


def instant_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normaliser(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte.casefold())
    return " ".join("".join(c for c in texte if not unicodedata.combining(c)).split())


def verifier_sources(config: dict) -> list[dict]:
    if not isinstance(config, dict) or config.get("version") != "sources-pdf-communaux-v1":
        raise SourceInvalide("Configuration de sources incorrecte")
    sources = config.get("sources")
    if not isinstance(sources, list) or len(sources) != len(CIBLES):
        raise SourceInvalide("Effectif inattendu des pièces")
    ids = set()
    for s in sources:
        if not isinstance(s, dict):
            raise SourceInvalide("Source incorrecte")
        uid = s.get("id")
        if uid in ids or uid not in CIBLES or s.get("url") != CIBLES[uid]:
            raise SourceInvalide("Identité ou adresse de pièce modifiée")
        ids.add(uid)
        url = urlsplit(s["url"])
        if url.scheme != "https" or url.username or url.password or url.port is not None:
            raise SourceInvalide("Adresse non publique")
        mots = s.get("mots")
        if (not isinstance(mots, list) or not mots or len(mots) > 8
                or any(not isinstance(w, str) or not 2 <= len(w) <= 80 for w in mots)
                or len(set(mots)) != len(mots)):
            raise SourceInvalide("Expressions de recherche incorrectes")
        for key in ("commune", "repere", "type"):
            if not isinstance(s.get(key), str) or not s[key].strip():
                raise SourceInvalide("Description de la source manquante")
    if ids != set(CIBLES):
        raise SourceInvalide("Sources obligatoires absentes")
    return sorted(sources, key=lambda x: x["id"])


def obtenir_pdf(url: str) -> bytes:
    if url not in CIBLES.values():
        raise SourceInvalide("Adresse de téléchargement inconnue")
    req = Request(url, headers={
        "User-Agent": "FRONTIERE-capture-pdf-public/1.0",
        "Accept": "application/pdf",
    })
    with build_opener(SansRedirection).open(req, timeout=30) as r:
        if r.status != 200 or r.geturl() != url:
            raise SourceInvalide("Réponse ou destination inattendue")
        data = r.read(MAX_PDF + 1)
    if len(data) > MAX_PDF:
        raise SourceInvalide("Document dépassant la limite d'octets")
    return data


def extraire_pages(data: bytes) -> list[str]:
    """Extraire uniquement les pages textuelles, sans reconnaissance d'images."""
    from pypdf import PdfReader

    lecteur = PdfReader(io.BytesIO(data), strict=False)
    if not 1 <= len(lecteur.pages) <= MAX_PAGES:
        raise SourceInvalide("Nombre de pages hors limites")
    return [page.extract_text() or "" for page in lecteur.pages]


def analyser_pdf(data: bytes, source: dict, *, instant: str,
                 extracteur=extraire_pages) -> dict:
    if not isinstance(data, bytes) or not data.startswith(b"%PDF-"):
        raise SourceInvalide("En-tête PDF absent")
    if b"%%EOF" not in data[-2048:]:
        raise SourceInvalide("Fin PDF absente")
    if len(data) > MAX_PDF:
        raise SourceInvalide("Document trop volumineux")
    pages = extracteur(data)
    if not isinstance(pages, list) or not 1 <= len(pages) <= MAX_PAGES:
        raise SourceInvalide("Extraction des pages incorrecte")
    if any(not isinstance(p, str) for p in pages):
        raise SourceInvalide("Texte de page invalide")
    indices = {}
    for mot in source["mots"]:
        terme = normaliser(mot)
        indices[mot] = [
            rang for rang, texte in enumerate(pages, 1)
            if terme in normaliser(texte)
        ]
    return {
        "id_source": source["id"], "commune": source["commune"],
        "type_piece": source["type"], "repere": source["repere"],
        "url_source_officielle": source["url"],
        "sha256_octets_pdf": hashlib.sha256(data).hexdigest(),
        "taille_octets": len(data), "pages": len(pages),
        "pages_extraites_avec_texte": sum(bool(p.strip()) for p in pages),
        "pages_contenant_termes": indices,
        "observation_le": instant,
        "qualification": "presence_lexicale_paginee_sans_validation_usage",
        "utilisation_effective_prouvee": False,
        "octets_pdf_republies": False,
    }


def executer(config: dict, *, ancien: dict, telecharger=obtenir_pdf,
             extracteur=extraire_pages, instant: str | None = None) -> dict:
    sources = verifier_sources(config)
    if not isinstance(ancien, dict) or ancien.get("version") != "observations-pdfs-municipaux-v1":
        raise SourceInvalide("Rapport précédent invalide")
    precedents = ancien.get("pieces")
    if not isinstance(precedents, list):
        raise SourceInvalide("Liste précédente invalide")
    rapport = {s["id_source"]: s for s in precedents if (
        isinstance(s, dict) and isinstance(s.get("id_source"), str)
    )}
    erreurs = []
    nouvelles = 0
    maintenant = instant or instant_utc()
    for source in sources:
        try:
            data = telecharger(source["url"])
            fiche = analyser_pdf(data, source, instant=maintenant, extracteur=extracteur)
            ancienne = rapport.get(source["id"])
            if ancienne and ancienne.get("sha256_octets_pdf") == fiche["sha256_octets_pdf"]:
                # Idempotence : la date du premier relevé n'est pas modifiée.
                fiche["observation_le"] = ancienne.get("observation_le", maintenant)
            else:
                nouvelles += 1
            rapport[source["id"]] = fiche
        except (OSError, ValueError, ImportError) as exc:
            erreurs.append({"source_id": source["id"], "motif": type(exc).__name__})
    if not rapport:
        raise SourceInvalide("Aucune pièce vérifiable : ne pas effacer les précédents")
    return {
        "version": "observations-pdfs-municipaux-v1",
        "controle_le": maintenant,
        "sources_attendues": len(sources),
        "pieces_avec_empreinte": len(rapport),
        "pieces_nouvelles_ou_changees": nouvelles,
        "echecs": erreurs,
        "donnees_probantes": "empreintes_et_paginage_sans_extraits_libres",
        "effets_mesures": 0,
        "pieces": [rapport[k] for k in sorted(rapport)],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sources", type=Path, default=CONFIG)
    p.add_argument("--sortie", type=Path, default=SORTIE)
    args = p.parse_args()
    try:
        sources = json.loads(args.sources.read_text(encoding="utf-8"))
        ancien = (
            json.loads(args.sortie.read_text(encoding="utf-8"))
            if args.sortie.exists() else
            {"version": "observations-pdfs-municipaux-v1", "pieces": []}
        )
        nouveau = executer(sources, ancien=ancien)
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        temporaire = args.sortie.with_suffix(".json.temp")
        temporaire.write_text(json.dumps(
            nouveau, ensure_ascii=False, sort_keys=True, indent=2
        ) + "\n", encoding="utf-8")
        temporaire.replace(args.sortie)
        print(json.dumps({
            k: v for k, v in nouveau.items() if k != "pieces"
        }, ensure_ascii=False, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        p.exit(1, f"Relevé PDF interrompu : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
