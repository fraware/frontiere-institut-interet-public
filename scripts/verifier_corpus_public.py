"""Contrôle structurel du corpus public, sans vérification factuelle des sources.

Les dates partielles restent partielles. Les conclusions historiques ne sont
jamais déduites ou réécrites par ce programme.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


NIVEAUX = {"cas_solide", "cas_partiel", "signal_contextuel"}
PRECISIONS = {"jour", "mois", "annee", "intervalle"}


def valider_date(texte: str, precision: str) -> bool:
    if not isinstance(texte, str) or not isinstance(precision, str):
        return False
    if precision == "jour":
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", texte):
            return False
        try:
            date.fromisoformat(texte)
        except ValueError:
            return False
        return True
    if precision == "mois":
        return bool(re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", texte))
    if precision == "annee":
        return bool(re.fullmatch(r"\d{4}", texte))
    if precision == "intervalle":
        if re.fullmatch(r"\d{4}-\d{4}", texte):
            depart, fin = (int(x) for x in texte.split("-"))
            return fin >= depart
        return bool(re.fullmatch(r"\d{4}-(fin|S[12])", texte))
    return False


def source_web_valide(texte: str) -> bool:
    if not isinstance(texte, str) or not texte.strip():
        return False
    parsed = urlsplit(texte)
    return parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username


def verifier(signaux: dict, chronologies: dict) -> dict:
    erreurs = []
    if not isinstance(signaux, dict) or not isinstance(chronologies, dict):
        raise ValueError("Les deux fichiers doivent contenir des objets.")
    lignes = signaux.get("signaux")
    parcours = chronologies.get("chronologies")
    if not isinstance(lignes, list) or not isinstance(parcours, list):
        raise ValueError("Les collections de signaux et de chronologies sont obligatoires.")
    if type(signaux.get("nombre_signaux")) is not int or signaux["nombre_signaux"] != len(lignes):
        erreurs.append("Nombre déclaré de signaux incohérent.")
    codes = set()
    classes = Counter()
    for position, ligne in enumerate(lignes, 1):
        if not isinstance(ligne, dict):
            erreurs.append(f"Signal {position} : format incorrect.")
            continue
        code = ligne.get("id_signal")
        if not isinstance(code, str) or not re.fullmatch(r"S\d{3}", code):
            erreurs.append(f"Signal {position} : identifiant invalide.")
            continue
        if code in codes:
            erreurs.append(f"Signal {code} : identifiant répété.")
        codes.add(code)
        niveau = ligne.get("niveau_documentaire")
        if niveau not in NIVEAUX:
            erreurs.append(f"Signal {code} : niveau documentaire invalide.")
        else:
            classes[niveau] += 1
        for champ in ("titre", "institution", "fait_documente", "capacite_concernee"):
            if not isinstance(ligne.get(champ), str) or not ligne[champ].strip():
                erreurs.append(f"Signal {code} : {champ} absent.")
        if not source_web_valide(ligne.get("source_url")):
            erreurs.append(f"Signal {code} : lien vers la source absent ou invalide.")
        date_source = ligne.get("date_source")
        precision = "mois" if isinstance(date_source, str) and "-" in date_source else "annee"
        if not valider_date(date_source, precision):
            erreurs.append(f"Signal {code} : date de source incohérente.")
    chronos_vus = set()
    precision_compte = Counter()
    nombre_evenements = 0
    sans_source_propre = 0
    for position, parcours_item in enumerate(parcours, 1):
        if not isinstance(parcours_item, dict):
            erreurs.append(f"Chronologie {position} : format incorrect.")
            continue
        code = parcours_item.get("id_signal")
        if code not in codes:
            erreurs.append(f"Chronologie {position} : signal inexistant : {code}.")
        if code in chronos_vus:
            erreurs.append(f"Chronologie {code} : signal répété.")
        chronos_vus.add(code)
        evenements = parcours_item.get("evenements")
        if not isinstance(evenements, list) or not evenements:
            erreurs.append(f"Chronologie {code} : aucun événement.")
            continue
        for indice, evenement in enumerate(evenements, 1):
            nombre_evenements += 1
            if not isinstance(evenement, dict):
                erreurs.append(f"Chronologie {code}, événement {indice} : format incorrect.")
                continue
            precision = evenement.get("precision")
            texte = evenement.get("date")
            if precision not in PRECISIONS or not valider_date(texte, precision):
                erreurs.append(f"Chronologie {code}, événement {indice} : date ou précision incorrecte.")
            else:
                precision_compte[precision] += 1
            if not isinstance(evenement.get("evenement"), str) or not evenement["evenement"].strip():
                erreurs.append(f"Chronologie {code}, événement {indice} : description absente.")
            if not evenement.get("source_url"):
                sans_source_propre += 1
            elif not source_web_valide(evenement["source_url"]):
                erreurs.append(f"Chronologie {code}, événement {indice} : source invalide.")
    return {
        "version_schema": "controle-corpus-public-v1",
        "valide_structurellement": not erreurs,
        "nombre_signaux": len(lignes),
        "niveaux_documentaires": dict(classes),
        "nombre_chronologies": len(parcours),
        "nombre_evenements": nombre_evenements,
        "precisions_temporelles": dict(precision_compte),
        "evenements_sans_source_propre": sans_source_propre,
        "erreurs": erreurs,
        "limite": (
            "Ce contrôle vérifie les structures et les liens entre fichiers ; "
            "il ne prouve pas que les sources soutiennent les événements ni les interprétations."
        ),
    }


def principal() -> None:
    analyseur = argparse.ArgumentParser(description="Contrôler la structure du corpus public.")
    analyseur.add_argument("--signaux", type=Path, default=Path("donnees/signaux_publics_v1.json"))
    analyseur.add_argument("--chronologies", type=Path, default=Path("donnees/chronologies_v5.json"))
    args = analyseur.parse_args()
    rapport = verifier(
        json.loads(args.signaux.read_text(encoding="utf-8")),
        json.loads(args.chronologies.read_text(encoding="utf-8")),
    )
    print(json.dumps(rapport, ensure_ascii=False, indent=2))
    if not rapport["valide_structurellement"]:
        raise SystemExit(1)


if __name__ == "__main__":
    principal()
