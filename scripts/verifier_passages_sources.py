"""Contrôler l'intégrité du premier registre de passages primaires.

Le code contrôle les identifiants et structures ; il ne visite pas les URL
et ne certifie pas la véracité des passages par lecture indépendante.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit


def url_officielle_valide(valeur) -> bool:
    if not isinstance(valeur, str) or not valeur.strip():
        return False
    lien = urlsplit(valeur)
    return lien.scheme == "https" and bool(lien.hostname) and not lien.username and not lien.password


def verifier(registre: dict, passages: dict) -> dict:
    erreurs = []
    if not isinstance(registre, dict) or not isinstance(passages, dict):
        raise ValueError("Registre et passages doivent être des objets.")
    versions = {
        "registre-verification-evenements-v3": (
            "passages-sources-primaires-v1", "donnees/registre_verification_evenements_v3.json",
        ),
        "registre-verification-evenements-v4": (
            "passages-sources-primaires-v2", "donnees/registre_verification_evenements_v4.json",
        ),
        "registre-verification-evenements-v5": (
            "passages-sources-primaires-v3", "donnees/registre_verification_evenements_v5.json",
        ),
        "registre-verification-evenements-v6": (
            "passages-sources-primaires-v4", "donnees/registre_verification_evenements_v6.json",
        ),
        "registre-verification-evenements-v7": (
            "passages-sources-primaires-v6", "donnees/registre_verification_evenements_v7.json",
        ),
    }
    versions_attendues = versions.get(registre.get("version_schema"))
    if versions_attendues is None:
        erreurs.append("Version du registre cible inconnue.")
    elif (passages.get("version_schema"), passages.get("registre_cible")) != versions_attendues:
        suite_courante = (
            registre.get("version_schema") == "registre-verification-evenements-v6"
            and passages.get("version_schema") == "passages-sources-primaires-v5"
            and passages.get("registre_cible") == "donnees/registre_verification_evenements_v6.json"
        )
        if not suite_courante:
            erreurs.append("Version des passages ou référence au registre cible incorrecte.")
    if passages.get("relecture_humaine_independante_effectuee") is not False:
        erreurs.append("La relecture indépendante doit rester non réalisée à ce stade.")
    if passages.get("responsable_de_la_premiere_lecture") != "assistant_de_recherche":
        erreurs.append("Auteur de la première lecture non identifié.")
    evenements = registre.get("evenements")
    fiches = passages.get("entrees")
    if not isinstance(evenements, list) or not isinstance(fiches, list):
        raise ValueError("Listes d'événements et de passages obligatoires.")
    ids = [x.get("identifiant_evenement") for x in evenements if isinstance(x, dict)]
    if len(ids) != len(evenements) or len(set(ids)) != len(ids):
        erreurs.append("Identifiants du registre des événements incomplets ou répétés.")
    attendus = set(ids)
    vus = set()
    for rang, x in enumerate(fiches, 1):
        if not isinstance(x, dict):
            erreurs.append(f"Passage {rang} : objet attendu.")
            continue
        identifiant = x.get("identifiant_evenement")
        if not isinstance(identifiant, str) or identifiant not in attendus:
            erreurs.append(f"Passage {rang} : événement inconnu.")
        elif identifiant in vus:
            erreurs.append(f"{identifiant} : passage répété.")
        vus.add(identifiant)
        if x.get("etat_verification") != "LECTURE_DOCUMENTAIRE_PRELIMINAIRE":
            erreurs.append(f"{identifiant} : état de vérification excessif ou inconnu.")
        if x.get("appui") != "PASSAGE_CIBLE_TROUVE":
            erreurs.append(f"{identifiant} : qualification de l'appui inconnue.")
        if x.get("verification_independante") is not False:
            erreurs.append(f"{identifiant} : indépendance déclarée à tort.")
        if not isinstance(x.get("limites"), str) or not x["limites"].strip():
            erreurs.append(f"{identifiant} : limites non renseignées.")
        for champ in ("source_principale", "source_complementaire"):
            source = x.get(champ)
            if source is None and champ == "source_complementaire":
                continue
            if not isinstance(source, dict) or not url_officielle_valide(source.get("url")):
                erreurs.append(f"{identifiant} : {champ} absente ou URL invalide.")
                continue
            for nom in ("localisation", "point_precis_etaye"):
                if not isinstance(source.get(nom), str) or not source[nom].strip():
                    erreurs.append(f"{identifiant} : {champ}/{nom} manquant.")
    if passages.get("version_schema") in {"passages-sources-primaires-v5", "passages-sources-primaires-v6"}:
        manquants = passages.get("evenements_restants_sans_passage")
        if not isinstance(manquants, list) or len(manquants) != len(set(manquants)):
            erreurs.append("Liste des événements sans passage absente ou répétée.")
        elif set(manquants) != attendus - vus:
            erreurs.append("Liste des événements sans passage incohérente avec les références.")
    if type(passages.get("nombre_entrees")) is not int or passages["nombre_entrees"] != len(fiches):
        erreurs.append("Nombre déclaré de passages différent du nombre réel.")
    return {
        "version_schema": "controle-passages-primaires-v1",
        "valide_structurellement": not erreurs,
        "total_evenements_registre": len(evenements),
        "passages_documentaires_preliminaires": len(fiches),
        "evenements_sans_passage_individuel": len(attendus - vus),
        "relecture_independante_realisee": False,
        "erreurs": erreurs,
        "limite": (
            "La validation de structure ne consulte pas les pages web et ne prouve "
            "ni la concordance factuelle ni l'indépendance de la première lecture."
        ),
    }


def principal() -> None:
    analyseur = argparse.ArgumentParser(description="Vérifier les références et limites du registre documentaire.")
    analyseur.add_argument("--registre", type=Path, default=Path("donnees/registre_verification_evenements_v7.json"))
    analyseur.add_argument("--passages", type=Path, default=Path("donnees/passages_sources_evenements_v6.json"))
    args = analyseur.parse_args()
    bilan = verifier(
        json.loads(args.registre.read_text(encoding="utf-8")),
        json.loads(args.passages.read_text(encoding="utf-8")),
    )
    print(json.dumps(bilan, ensure_ascii=False, indent=2))
    if not bilan["valide_structurellement"]:
        raise SystemExit(1)


if __name__ == "__main__":
    principal()
