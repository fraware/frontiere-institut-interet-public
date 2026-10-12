"""Contrôler les jalons opérationnels supplémentaires fondés sur des sources publiques.

Les attestations collectives ne deviennent jamais des dates individuelles de
mobilisation. Les réalisations d'une ancienne génération d'équipements restent
séparées du marché de renouvellement étudié.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from math import isfinite
from pathlib import Path
from urllib.parse import urlsplit


class JalonsInvalides(ValueError):
    """Signaler une incohérence structurelle ou une date indûment attribuée."""


TYPES_ADMIS = {
    "production_effective",
    "performance_operationnelle",
    "habilitation_operationnelle",
    "formation_effective",
    "reception_equipement",
    "mise_en_exploitation",
}
PRECISIONS = {"jour", "annee", "borne_documentaire", "periode_qualitative"}
LIEN_ANCIEN = "generation_anterieure_distincte_du_marche_2026"


def _texte(valeur: object, champ: str) -> str:
    """Refuser un champ libre absent, blanc ou non textuel."""
    if not isinstance(valeur, str) or not valeur.strip():
        raise JalonsInvalides(f"{champ} doit contenir du texte")
    return valeur


def _valider_source(source: object) -> str:
    """Valider la référence publique sans prétendre contrôler son contenu distant."""
    if not isinstance(source, dict):
        raise JalonsInvalides("Source non structurée")
    identifiant = _texte(source.get("id"), "source.id")
    for champ in ("organisme", "titre", "repere", "publication"):
        _texte(source.get(champ), f"source.{champ}")
    url = urlsplit(_texte(source.get("url"), "source.url"))
    if url.scheme != "https" or not url.netloc or url.username or url.password:
        raise JalonsInvalides("URL de source incorrecte")
    return identifiant


def _valider_indicateur(indicateur: object, type_jalon: str) -> None:
    """Vérifier unités et valeurs sans transformer un jalon qualitatif en zéro."""
    if indicateur is None:
        if type_jalon != "mise_en_exploitation":
            raise JalonsInvalides("Indicateur numérique obligatoire pour ce jalon")
        return
    if not isinstance(indicateur, dict):
        raise JalonsInvalides("Indicateur mal structuré")
    valeur = indicateur.get("valeur")
    if type(valeur) not in (int, float) or not isfinite(valeur) or valeur <= 0:
        raise JalonsInvalides("La valeur doit être un réel strictement positif")
    _texte(indicateur.get("unite"), "indicateur.unite")


def verifier(document: object, identifiants_corpus: set[str]) -> list[dict]:
    """Valider sources, périodes et liens avec le corpus de chronologies.

    La reconnaissance d'une source ne vaut pas vérification de son contenu :
    les références sont traitées comme des assertions documentaires à tracer.
    """
    if not isinstance(document, dict) or document.get("version") != "1":
        raise JalonsInvalides("Version de document non reconnue")
    recherche = _texte(document.get("date_recherche"), "date_recherche")
    try:
        if date.fromisoformat(recherche).isoformat() != recherche:
            raise ValueError("Date non canonique")
    except ValueError as exc:
        raise JalonsInvalides("Date de recherche incorrecte") from exc

    sources = document.get("sources")
    jalons = document.get("observations")
    if not isinstance(sources, list) or not sources:
        raise JalonsInvalides("Aucune source")
    if not isinstance(jalons, list) or not jalons:
        raise JalonsInvalides("Aucune observation")

    ids_sources: set[str] = set()
    for source in sources:
        identifiant = _valider_source(source)
        if identifiant in ids_sources:
            raise JalonsInvalides("Source répétée")
        ids_sources.add(identifiant)

    ids_jalons: set[str] = set()
    for jalon in jalons:
        if not isinstance(jalon, dict):
            raise JalonsInvalides("Observation mal structurée")
        identifiant = _texte(jalon.get("id"), "observation.id")
        if identifiant in ids_jalons:
            raise JalonsInvalides("Identifiant d'observation répété")
        ids_jalons.add(identifiant)
        identifiant_cas = _texte(jalon.get("id_signal"), "observation.id_signal")
        if identifiant_cas not in identifiants_corpus:
            raise JalonsInvalides(f"Cas non présent dans le corpus : {identifiant_cas}")
        if jalon.get("source_id") not in ids_sources:
            raise JalonsInvalides("Référence de source manquante")
        type_jalon = jalon.get("type")
        if type_jalon not in TYPES_ADMIS:
            raise JalonsInvalides("Type de jalon inconnu")
        for champ in ("objet", "periode_reference", "lien_avec_cas", "limite", "domaine"):
            _texte(jalon.get(champ), f"observation.{champ}")

        precision = jalon.get("precision_date")
        if precision not in PRECISIONS:
            raise JalonsInvalides("Précision temporelle inconnue")
        date_jour = jalon.get("date_jour")
        if precision == "jour":
            if not isinstance(date_jour, str):
                raise JalonsInvalides("Date journalière manquante")
            try:
                if date.fromisoformat(date_jour).isoformat() != date_jour:
                    raise ValueError("Date non canonique")
            except ValueError as exc:
                raise JalonsInvalides("Date journalière incorrecte") from exc
            if jalon["periode_reference"] != date_jour:
                raise JalonsInvalides("Contradiction entre date et période")
        elif date_jour is not None:
            raise JalonsInvalides("Date journalière inventée à partir d'une période")

        _valider_indicateur(jalon.get("indicateur"), type_jalon)
        ancien = jalon["lien_avec_cas"] == LIEN_ANCIEN
        if identifiant_cas == "S050" and not ancien:
            raise JalonsInvalides("Confusion entre anciens calculateurs et marché 2026")
        if ancien and identifiant_cas != "S050":
            raise JalonsInvalides("Comparateur ancien associé au mauvais cas")

    return jalons


def bilan(document: dict, chronologies: dict) -> dict:
    """Produire une couverture traçable, sans inférer de délai opérationnel."""
    cas = chronologies.get("chronologies")
    if not isinstance(cas, list):
        raise JalonsInvalides("Corpus de chronologies mal structuré")
    identifiants = {x.get("id_signal") for x in cas if isinstance(x, dict)}
    jalons = verifier(document, identifiants)
    resultat = {}
    for jalon in jalons:
        code = jalon["id_signal"]
        entree = resultat.setdefault(code, {
            "observations": 0,
            "observations_generation_anterieure": 0,
            "dates_individuelles_de_premiere_contribution": 0,
            "indicateurs": [],
        })
        entree["observations"] += 1
        entree["observations_generation_anterieure"] += int(
            jalon["lien_avec_cas"] == LIEN_ANCIEN
        )
        if jalon["indicateur"] is not None:
            entree["indicateurs"].append({
                "observation": jalon["id"],
                "valeur": jalon["indicateur"]["valeur"],
                "unite": jalon["indicateur"]["unite"],
                "source": jalon["source_id"],
            })
    return {
        "version": document["version"],
        "date_recherche": document["date_recherche"],
        "cas_concernes": sorted(resultat),
        "nombre_jalons": len(jalons),
        "nombre_sources": len(document["sources"]),
        "delais_besoin_vers_premiere_contribution_nouvellement_observes": 0,
        "par_cas": resultat,
    }


def main() -> int:
    """Exécuter la validation et imprimer un bilan au format JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jalons", type=Path, default=Path(
        "donnees/jalons_operationnels_sources_publiques_2026-10-12.json"
    ))
    parser.add_argument("--chronologies", type=Path, default=Path(
        "donnees/chronologies_v9.json"
    ))
    parser.add_argument("--sortie", type=Path)
    args = parser.parse_args()
    try:
        jalons = json.loads(args.jalons.read_text(encoding="utf-8"))
        chronologies = json.loads(args.chronologies.read_text(encoding="utf-8"))
        texte = json.dumps(bilan(jalons, chronologies), indent=2, ensure_ascii=False) + "\n"
        if args.sortie is None:
            print(texte, end="")
        else:
            # Préserver une sortie existante : aucune écriture destructive implicite.
            with args.sortie.open("x", encoding="utf-8") as fichier:
                fichier.write(texte)
    except (OSError, json.JSONDecodeError, JalonsInvalides) as exc:
        parser.exit(1, f"Échec de validation documentaire : {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
