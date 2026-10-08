"""Préparer deux lectures indépendantes des passages officiels du corpus historique.

Le paquet présente le fait à contrôler et les pièces candidates, sans afficher
la conclusion préliminaire de l'assistant ni son appréciation des limites.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    from scripts.verifier_passages_sources import verifier as verifier_passages
except ModuleNotFoundError:
    from verifier_passages_sources import verifier as verifier_passages

DIMENSIONS = ("piece_retrouvee", "fait_etaye", "date_etayee", "precision_respectee")


def ecrire(chemin: Path, donnees: dict) -> None:
    chemin.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def empreinte(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


def preparer(registre_path: Path, passages_path: Path, destination: Path) -> dict:
    depot = Path(__file__).resolve().parents[1]
    if destination.resolve().is_relative_to(depot):
        raise ValueError("Les réponses des relecteurs doivent rester hors du dépôt public.")
    registre = json.loads(registre_path.read_text(encoding="utf-8"))
    passages = json.loads(passages_path.read_text(encoding="utf-8"))
    resultat = verifier_passages(registre, passages)
    if not resultat["valide_structurellement"]:
        raise ValueError("Registre documentaire incorrect : " + "; ".join(resultat["erreurs"]))
    if resultat["evenements_sans_passage_individuel"]:
        raise ValueError("Le paquet exige une pièce candidate par événement.")
    references = {p["identifiant_evenement"]: p for p in passages["entrees"]}
    fiches = []
    reponses = []
    for evenement in sorted(registre["evenements"], key=lambda x: x["identifiant_evenement"]):
        identifiant = evenement["identifiant_evenement"]
        note = references[identifiant]
        pieces = []
        for nom, prefixe in (("source_principale", "P1"), ("source_complementaire", "P2")):
            p = note.get(nom)
            if p:
                pieces.append({"id": prefixe, "url": p["url"], "localisation_proposee": p["localisation"]})
        fiches.append({
            "identifiant_evenement": identifiant,
            "id_signal": evenement["id_signal"],
            "date_a_controler": evenement["date_documentee"],
            "precision_temporelle": evenement["precision_temporelle"],
            "assertion_a_controler": evenement["fait_a_verifier"],
            "pieces_candidates": pieces,
        })
        reponses.append({
            "identifiant_evenement": identifiant,
            **{nom: "A_VERIFIER" for nom in DIMENSIONS},
            "passage_effectivement_consulte": "",
            "justification": "",
        })
    paquet = {
        "version_schema": "paquet-relecture-evenements-v1",
        "nombre_evenements": len(fiches),
        "fiches": fiches,
        "regle": "Les sources sont candidates ; aucune assertion du paquet n'est présumée établie.",
    }
    destination.mkdir(parents=True, exist_ok=False)
    paquet_central = destination / "paquet_commun.json"
    ecrire(paquet_central, paquet)
    sha = empreinte(paquet_central)
    formulaire = {
        "version_schema": "jugements-evenements-v1",
        "empreinte_sha256_paquet": sha,
        "relecteur_code": "A_RENSEIGNER",
        "jugements": reponses,
    }
    for n in (1, 2):
        dossier = destination / f"relecteur_{n}"
        dossier.mkdir()
        (dossier / "paquet.json").write_bytes(paquet_central.read_bytes())
        ecrire(dossier / "jugements_vierges.json", formulaire)
        (dossier / "CONSIGNES.md").write_text(
            "# Relecture indépendante des événements\n\n"
            "Évaluer chaque assertion au moyen des pièces proposées, sans "
            "consulter les jugements de l'autre relecteur.\n\n"
            "Pour chaque dimension (pièce retrouvée, fait étayé, date étayée, "
            "précision respectée), remplacer A_VERIFIER par OUI, NON ou "
            "INDETERMINE. Une justification personnelle est obligatoire. "
            "Renseigner le passage effectivement consulté quand il existe. "
            "Consigner les liens rompus, contradictions, lacunes et connaissances "
            "antérieures des faits.\n\n"
            "La recherche d'une pièce complémentaire est admise si sa provenance "
            "est citée dans la justification. L'absence de preuve doit rester "
            "INDETERMINE lorsque le document n'est pas accessible.\n",
            encoding="utf-8",
        )
    manifeste = {
        "version_schema": "preparation-relecture-evenements-v1",
        "empreinte_sha256_registre": empreinte(registre_path),
        "empreinte_sha256_passages": empreinte(passages_path),
        "empreinte_sha256_paquet": sha,
        "nombre_evenements": len(fiches),
        "relectures_recues": False,
        "avis_independants_disponibles": False,
        "limite": "L'empreinte locale ne date pas les travaux : une attestation extérieure doit précéder les séances.",
    }
    ecrire(destination / "manifest_preparation.json", manifeste)
    return manifeste


def principal() -> None:
    p = argparse.ArgumentParser(description="Produire les dossiers d'une double relecture de sources.")
    p.add_argument("--registre", type=Path, default=Path("donnees/registre_verification_evenements_v7.json"))
    p.add_argument("--passages", type=Path, default=Path("donnees/passages_sources_evenements_v6.json"))
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args()
    try:
        resultat = preparer(a.registre, a.passages, a.sortie)
    except (ValueError, KeyError, TypeError, OSError) as e:
        raise SystemExit(f"Préparation impossible : {e}") from e
    print(f"Dossiers préparés pour {resultat['nombre_evenements']} événements ; aucune relecture recueillie.")


if __name__ == "__main__":
    principal()
