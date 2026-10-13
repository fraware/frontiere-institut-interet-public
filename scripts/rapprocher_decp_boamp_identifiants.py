"""Rapprocher des références BOAMP attestées et des identités DECP.

Le fichier d'entrée ne contient que des identifiants transcrits depuis des
avis officiels et assortis de leur chemin de preuve. Une correspondance exacte
est une *piste documentaire*, jamais une preuve de continuité juridique ou
de besoin de compétence non satisfait.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sqlite3

SIRET = re.compile(r"^[0-9]{14}$")
AVIS = re.compile(r"^[0-9]{2}-[0-9]{2,8}$")
MAX = 10000


class RapprochementInvalide(ValueError):
    """Entrée ambiguë, base incomplète ou provenance non vérifiable."""


def _chaine(valeur: object, limite: int = 256) -> str:
    if not isinstance(valeur, str) or not 0 < len(valeur.strip()) <= limite:
        raise RapprochementInvalide("Identifiant ou référence absent/invalide")
    if valeur != valeur.strip():
        raise RapprochementInvalide("Espaces parasites dans une référence")
    return valeur


def rapprocher(base: Path, attestations: dict) -> dict:
    """Comparer des identifiants strictement identiques, sans normalisation floue.

    L'unité de résultat est l'avis BOAMP. Si plusieurs identités DECP sont
    soutenues par les mêmes références, le lien reste ambigu.
    """
    if (not isinstance(attestations, dict)
            or attestations.get("version") != "references-boamp-decp-v1"
            or not isinstance(attestations.get("avis"), list)
            or len(attestations["avis"]) > MAX):
        raise RapprochementInvalide("Registre d'attestations incompatible")
    if not base.is_file():
        raise RapprochementInvalide("Index DECP absent")
    try:
        uri = base.resolve().as_uri() + "?mode=ro"
        connexion = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        raise RapprochementInvalide("Ouverture de l'index impossible") from exc
    try:
        tables = {r[0] for r in connexion.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"marches", "versions", "attestations"}.issubset(tables):
            raise RapprochementInvalide("Schéma DECP incomplet")
        if connexion.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RapprochementInvalide("Index DECP corrompu")
        identites = {
            (siret, identifiant)
            for siret, identifiant in connexion.execute(
                "SELECT acheteur_siret, id_marche FROM marches")
        }
        vus, resultats = set(), []
        for avis in attestations["avis"]:
            if not isinstance(avis, dict):
                raise RapprochementInvalide("Notice incorrecte")
            identifiant = _chaine(avis.get("id_boamp"))
            if not AVIS.fullmatch(identifiant) or identifiant in vus:
                raise RapprochementInvalide("Numéro BOAMP invalide ou répété")
            vus.add(identifiant)
            source = _chaine(avis.get("url_source"), 2048)
            if not source.startswith("https://"):
                raise RapprochementInvalide("Source HTTPS officielle attendue")
            references = avis.get("references")
            if not isinstance(references, list) or not references or len(references) > 100:
                raise RapprochementInvalide("Références documentaires absentes")
            candidates = set()
            for ref in references:
                if not isinstance(ref, dict):
                    raise RapprochementInvalide("Référence incorrecte")
                siret = _chaine(ref.get("acheteur_siret"))
                marche = _chaine(ref.get("id_marche"), 100)
                chemin = _chaine(ref.get("chemin_preuve"), 2048)
                if not SIRET.fullmatch(siret) or not chemin.startswith("/"):
                    raise RapprochementInvalide("Clé ou localisation documentaire invalide")
                if ".." in chemin.split("/"):
                    raise RapprochementInvalide("Localisation documentaire ambiguë")
                if (siret, marche) in identites:
                    candidates.add((siret, marche))
            if len(candidates) == 1:
                statut = "cle_exacte_candidate"
            elif len(candidates) > 1:
                statut = "plusieurs_cles_candidates"
            else:
                statut = "aucune_cle_commune"
            resultats.append({
                "id_boamp": identifiant,
                "url_source": source,
                "statut": statut,
                "identites_decp_candidates": [
                    {"acheteur_siret": s, "id_marche": m}
                    for s, m in sorted(candidates)
                ],
                "references_examinees": len(references),
                "controle_valeur_dans_source_primaire": False,
                "continuite_juridique_etablie": False,
            })
        return {
            "version": "rapprochement-decp-boamp-v1",
            "avis_examines": len(resultats),
            "liens_juridiques_verifies": 0,
            "cle_exacte_candidate": sum(x["statut"] == "cle_exacte_candidate"
                                         for x in resultats),
            "plusieurs_cles_candidates": sum(
                x["statut"] == "plusieurs_cles_candidates" for x in resultats),
            "aucune_cle_commune": sum(
                x["statut"] == "aucune_cle_commune" for x in resultats),
            "resultats": resultats,
        }
    except sqlite3.Error as exc:
        raise RapprochementInvalide("Erreur de lecture SQLite") from exc
    finally:
        connexion.close()


def main() -> None:
    """Exécuter hors réseau un examen de correspondance documentaire."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--attestations", required=True, type=Path)
    parser.add_argument("--sortie", required=True, type=Path)
    args = parser.parse_args()
    try:
        entree = json.loads(args.attestations.read_text(encoding="utf-8"))
        bilan = rapprocher(args.base, entree)
        if args.sortie.exists():
            raise RapprochementInvalide("Refus d'écraser un bilan antérieur")
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        args.sortie.write_text(
            json.dumps(bilan, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, UnicodeError) as exc:
        parser.exit(1, f"Rapprochement refusé : {exc}\n")


if __name__ == "__main__":
    main()
