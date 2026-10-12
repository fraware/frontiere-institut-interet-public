"""Valider les jalons publics sans assimiler une attestation à l'exécution.

Le module fonctionne hors réseau. L'URL de source est une référence
documentaire : sa présence ne prouve pas qu'un document est inchangé.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
from urllib.parse import urlparse


class ObservationInvalide(ValueError):
    """Signaler une incohérence de provenance ou de chronologie."""


def _date_iso(value: object, champ: str) -> str | None:
    """Vérifier une date ISO journalière ou l'absence explicite de date."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ObservationInvalide(f"{champ} doit être une date ou null")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ObservationInvalide(f"{champ} illisible") from exc
    if parsed.isoformat() != value:
        raise ObservationInvalide(f"{champ} non canonique")
    return value


def verifier_observations(document: dict) -> list[dict]:
    """Contrôler les contraintes temporelles propres à chaque source."""
    if not isinstance(document, dict) or document.get("version") != "1":
        raise ObservationInvalide("Version inconnue")
    if not _date_iso(document.get("date_recherche"), "date_recherche"):
        raise ObservationInvalide("Date de recherche manquante")
    observations = document.get("observations")
    if not isinstance(observations, list) or not observations:
        raise ObservationInvalide("Liste d'observations absente")
    vus: set[str] = set()
    for observation in observations:
        if not isinstance(observation, dict):
            raise ObservationInvalide("Observation mal structurée")
        identifiant = observation.get("id_observation")
        signal = observation.get("id_signal")
        if not isinstance(identifiant, str) or not identifiant.startswith("OBS-"):
            raise ObservationInvalide("Identifiant de constat incorrect")
        if identifiant in vus:
            raise ObservationInvalide("Constat dupliqué")
        vus.add(identifiant)
        if not isinstance(signal, str) or not signal.startswith("S"):
            raise ObservationInvalide("Identifiant de cas incorrect")
        if not isinstance(observation.get("evenement"), str) or not observation["evenement"].strip():
            raise ObservationInvalide("Description manquante")
        if not isinstance(observation.get("portee"), str) or not observation["portee"].strip():
            raise ObservationInvalide("Portée manquante")
        inconnues = observation.get("inconnues")
        if not isinstance(inconnues, list) or not inconnues or not all(
            isinstance(v, str) and v.strip() for v in inconnues
        ):
            raise ObservationInvalide("Inconnues insuffisamment décrites")
        source = observation.get("source")
        if not isinstance(source, dict):
            raise ObservationInvalide("Source manquante")
        adresse = source.get("url")
        if not isinstance(adresse, str):
            raise ObservationInvalide("Adresse de source incorrecte")
        url = urlparse(adresse)
        if url.scheme != "https" or not url.netloc:
            raise ObservationInvalide("Adresse de source non sécurisée")
        if type(source.get("page_pdf")) is not int or source["page_pdf"] < 1:
            raise ObservationInvalide("Page probante absente")
        attestation = _date_iso(observation.get("date_attestation"), "date_attestation")
        action = _date_iso(observation.get("date_action_exacte"), "date_action_exacte")
        borne = _date_iso(
            observation.get("borne_superieure_action_collective"), "borne_superieure"
        )
        nature = observation.get("nature")
        if nature == "attestation_retrospective_datee":
            if not attestation or borne != attestation or action is not None:
                raise ObservationInvalide("Attestation collective mal bornée")
            if observation.get("statut_borne") != (
                "au_moins_une_sollicitation_anterieure_ou_contemporaine_a_l_attestation"
            ):
                raise ObservationInvalide("Interprétation de borne incorrecte")
        elif nature == "description_publique_poste_non_datee":
            if any((attestation, action, borne)) or observation.get("statut_borne") != (
                "aucune_date_d_action_etablie"
            ):
                raise ObservationInvalide("Date d'action déduite d'une fiche non datée")
        else:
            raise ObservationInvalide("Nature documentaire inconnue")
    return observations


def resumer(document: dict) -> dict:
    """Synthétiser des observations en conservant les inconnues."""
    observations = verifier_observations(document)
    return {
        "version": document["version"],
        "date_recherche": document["date_recherche"],
        "nombre_observations": len(observations),
        "cas_documentes": sorted({v["id_signal"] for v in observations}),
        "attestations_retrospectives_datees": sum(
            v["nature"] == "attestation_retrospective_datee" for v in observations
        ),
        "descriptions_poste_non_datees": sum(
            v["nature"] == "description_publique_poste_non_datee" for v in observations
        ),
        "dates_precises_actions_individuelles": sum(
            v["date_action_exacte"] is not None for v in observations
        ),
        "temps_jusqua_premiere_contribution_utile_observables": 0,
        "jalons": [
            {
                "id_observation": v["id_observation"],
                "id_signal": v["id_signal"],
                "nature": v["nature"],
                "date_attestation": v["date_attestation"],
                "date_action_exacte": v["date_action_exacte"],
                "borne_superieure_action_collective": (
                    v["borne_superieure_action_collective"]
                ),
                "url_source": v["source"]["url"],
            }
            for v in observations
        ],
    }


def main() -> int:
    """Contrôler des observations locales et afficher ou enregistrer le bilan."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--observations", type=Path,
        default=Path("donnees/observations_execution_publiques_2026-10-12.json"),
    )
    parser.add_argument("--sortie", type=Path)
    arguments = parser.parse_args()
    try:
        document = json.loads(arguments.observations.read_text(encoding="utf-8"))
        sortie = json.dumps(resumer(document), ensure_ascii=False, indent=2) + "\n"
        if arguments.sortie:
            arguments.sortie.write_text(sortie, encoding="utf-8")
        else:
            print(sortie, end="")
    except (OSError, json.JSONDecodeError, ObservationInvalide) as exc:
        parser.exit(1, f"Compléments invalides : {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
