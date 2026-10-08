"""Vérifier l'identité entre une capture brute et un manifeste d'ingestion.

Les empreintes sémantiques des données transformées ne remplacent jamais
les empreintes du transport exact. Les références privées ne sont pas lues.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re

try:
    from scripts.archiver_source_brute import ErreurArchive, verifier
except ModuleNotFoundError:
    from archiver_source_brute import ErreurArchive, verifier

EMPREINTE = re.compile(r"^[a-f0-9]{64}$")
# Champ contenant SHA-256 des octets téléchargés, et taille quand disponible.
SOURCES_TRANSPORT_BRUT = {
    "dila_roae": ("sha256_zip", "octets_zip"),
    "dila_annuaire_local": ("sha256_export", None),
    "insee_cog": ("sha256_zip", None),
}


def _charger(path: Path) -> dict:
    try:
        valeur = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ErreurArchive("Manifeste inaccessible ou non conforme.") from exc
    if not isinstance(valeur, dict):
        raise ErreurArchive("Le manifeste doit être un objet JSON.")
    return valeur


def verifier_lien(manifeste: dict, racine: Path, capture: str) -> dict:
    """Confronter deux déclarations de même transport après vérification des octets."""
    identifiant = manifeste.get("source_id")
    if identifiant not in SOURCES_TRANSPORT_BRUT:
        raise ErreurArchive(
            "Source non prise en charge : empreinte brute du transport non établie. "
            "Une empreinte sémantique ne constitue pas une preuve des octets d'origine."
        )
    cle_sha, cle_taille = SOURCES_TRANSPORT_BRUT[identifiant]
    digest_attendu = manifeste.get(cle_sha)
    if not isinstance(digest_attendu, str) or EMPREINTE.fullmatch(digest_attendu) is None:
        raise ErreurArchive(f"Empreinte des octets bruts absente ou invalide : {cle_sha}.")
    resultat = verifier(racine, capture)
    fiche = _charger(racine / "captures" / f"{capture}.json")
    if fiche.get("source_id") != identifiant:
        raise ErreurArchive("Identité de source différente entre la capture et le manifeste.")
    if digest_attendu != resultat["objet"]:
        raise ErreurArchive("Empreintes de transport divergentes.")
    if cle_taille is not None:
        taille_attendue = manifeste.get(cle_taille)
        if type(taille_attendue) is not int or taille_attendue != resultat["octets"]:
            raise ErreurArchive("Taille du transport brute différente du manifeste.")
    return {
        "version_schema": "verification-lien-capture-manifeste-v1",
        "source_id": identifiant,
        "sha256_transport_brut": resultat["objet"],
        "nombre_octets_bruts": resultat["octets"],
        "capture": capture,
        "identite_octets_verifiee": True,
        "origine_distante_attestee": False,
        "conservation_immuable_confirmee": False,
        "date_capture_identique_declaree": (
            fiche.get("observe_le_declare") == manifeste.get("observe_le")
        ),
        "limite": "Correspondance cryptographique locale des octets bruts seulement.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifeste", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--capture", required=True)
    args = parser.parse_args()
    try:
        bilan = verifier_lien(_charger(args.manifeste), args.archive, args.capture)
    except (ErreurArchive, OSError, ValueError) as exc:
        parser.exit(1, f"Correspondance refusée : {exc}\n")
    print(json.dumps(bilan, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
