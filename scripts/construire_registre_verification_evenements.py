"""Construire un registre explicite des événements historiques à vérifier.

Une source qui soutient un signal n'est qu'une source *candidate* pour chacun
de ses événements : aucune preuve directe n'est supposée ou fabriquée.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def construire(signaux: dict, chronologies: dict) -> dict:
    repertoire = {s["id_signal"]: s for s in signaux["signaux"]}
    if len(repertoire) != len(signaux["signaux"]):
        raise ValueError("Identifiants de signaux dupliqués.")
    fiches = []
    for chronologie in chronologies["chronologies"]:
        identifiant = chronologie["id_signal"]
        if identifiant not in repertoire:
            raise ValueError(f"Signal inconnu : {identifiant}")
        signal = repertoire[identifiant]
        for rang, evenement in enumerate(chronologie["evenements"], 1):
            fiches.append({
                "identifiant_evenement": f"{identifiant}-E{rang:02d}",
                "id_signal": identifiant,
                "titre_signal": signal["titre"],
                "date_documentee": evenement["date"],
                "precision_temporelle": evenement["precision"],
                "fait_a_verifier": evenement["evenement"],
                "source_candidate_du_signal": signal["source_url"],
                "organisme_source_du_signal": signal["source_organisme"],
                "preuve_directe_de_cet_evenement": "A_VERIFIER",
                "resultat_relecture": None,
                "motif_relecture": None,
            })
    version_chronologies = str(chronologies.get("version", ""))
    if version_chronologies not in {"3", "4", "5"}:
        raise ValueError("Version de chronologies non prise en charge pour ce registre.")
    version_registre = str(int(version_chronologies) - 2)
    return {
        "version_schema": f"registre-verification-evenements-v{version_registre}",
        "origine": ["donnees/signaux_publics_v1.json", f"donnees/chronologies_v{version_chronologies}.json"],
        "nombre_evenements": len(fiches),
        "regle": (
            "La source candidate provient du signal parent. Elle ne doit pas "
            "être qualifiée de source directe de l'événement sans examen du "
            "passage exact qui le documente."
        ),
        "evenements": fiches,
    }


def principal() -> None:
    parser = argparse.ArgumentParser(description="Préparer le registre des preuves événementielles.")
    parser.add_argument("--signaux", type=Path, default=Path("donnees/signaux_publics_v1.json"))
    parser.add_argument("--chronologies", type=Path, default=Path("donnees/chronologies_v5.json"))
    parser.add_argument("--sortie", type=Path, required=True)
    args = parser.parse_args()
    document = construire(
        json.loads(args.signaux.read_text(encoding="utf-8")),
        json.loads(args.chronologies.read_text(encoding="utf-8")),
    )
    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.sortie.open("x", encoding="utf-8") as fichier:
            json.dump(document, fichier, ensure_ascii=False, indent=2)
            fichier.write("\n")
    except FileExistsError as erreur:
        raise SystemExit("Le registre existe déjà : refuser une réécriture silencieuse.") from erreur
    print(f"Registre de vérification préparé : {document['nombre_evenements']} événements.")


if __name__ == "__main__":
    principal()
