"""Contre-vérifier les tirages BOAMP par une seconde procédure intégrale.

Le contrôle relit les avis de l'index attesté, reconstruit indépendamment
les dénominateurs et les premiers rangs de chaque strate, vérifie les avis
publiés et mesure la sensibilité à des semences alternatives.
"""
from __future__ import annotations

import argparse
import calendar
from collections import Counter, defaultdict
from contextlib import closing
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sqlite3

try:
    from scripts.analyser_historique_boamp import MOTIFS, normaliser
except ModuleNotFoundError:
    from analyser_historique_boamp import MOTIFS, normaliser

VERSION = "contre-verification-tirage-boamp-v1"
VERSION_TIRAGE = "echantillon-exploratoire-boamp-v2"
TEMOIN = "temoin_sans_expression_des_sept_domaines"
SEMENCES_REPLICATION = ("frontiere-contrepreuve-alpha-2026", "frontiere-contrepreuve-beta-2026")
ETATS = {"INITIAL", "RECTIFICATIF", "MODIFICATION", "ANNULATION"}


class ControleInvalide(ValueError):
    """La sélection publiée ne correspond pas aux avis de référence."""


def empreinte(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for bloc in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloc)
    return h.hexdigest()


def empreinte_tirage(semence: str, cle: tuple[str, str, str],
                    jour: str, identifiant: str) -> str:
    # Reconstruction distincte : on recalcule les octets de la clé, sans
    # réutiliser le code de tri du générateur d'échantillon.
    elements = [semence, cle[0], cle[1], cle[2], jour, identifiant]
    octets = json.dumps(
        elements, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(octets).hexdigest()


def meilleurs(stock: dict, cle: tuple, entree: tuple, quota: int) -> None:
    # Tri intégral des k+1 candidats par strate ; algorithme volontairement
    # distinct de celui du tirage d'origine (élimination du pire rang).
    stock[cle].append(entree)
    stock[cle].sort()
    if len(stock[cle]) > quota:
        stock[cle].pop()


def mois_civils_attestes(jours: list[str]) -> tuple[list[str], list[dict]]:
    uniques = set(jours)
    if not jours or len(uniques) != len(jours):
        raise ControleInvalide("Inventaire journalier vide ou dupliqué.")
    try:
        dates = [date.fromisoformat(v) for v in jours]
    except (ValueError, TypeError) as erreur:
        raise ControleInvalide("Date d'inventaire illisible.") from erreur
    if any(d.isoformat() != raw for d, raw in zip(dates, jours)):
        raise ControleInvalide("Date d'inventaire non canonique.")
    start, end = min(dates), max(dates)
    annee, mois = start.year, start.month
    complets, details = [], []
    while (annee, mois) <= (end.year, end.month):
        nom = f"{annee:04d}-{mois:02d}"
        total = calendar.monthrange(annee, mois)[1]
        count = sum(f"{nom}-{day:02d}" in uniques for day in range(1, total + 1))
        valide = count == total
        details.append({
            "mois": nom, "jours_archives": count,
            "jours_calendaires": total, "mois_complet": valide,
        })
        if valide:
            complets.append(nom)
        if mois == 12:
            annee, mois = annee + 1, 1
        else:
            mois += 1
    return complets, details


def classer_etat(valeur) -> str:
    if not isinstance(valeur, str):
        return "NON_RENSEIGNE"
    valeur = valeur.strip().upper()
    return valeur if valeur in ETATS else "AUTRE"


def verifier_rapports(index: Path, preuve: Path, echantillon: Path) -> dict:
    if not all(p.is_file() for p in (index, preuve, echantillon)):
        raise ControleInvalide("Fichier de contre-vérification absent.")
    source = json.loads(preuve.read_text(encoding="utf-8"))
    resultat = json.loads(echantillon.read_text(encoding="utf-8"))
    sha = empreinte(index)
    if (source.get("version") != "publication-index-boamp-v1"
            or sha != source.get("sha256_index")
            or sha != resultat.get("sha256_index_boamp")
            or source.get("revision_depot") != resultat.get("revision_depot_source")
            or resultat.get("version") != VERSION_TIRAGE
            or resultat.get("stratification_categorie_marche_effective") is not False
            and resultat.get("nombre_categories_marche_renseignees") == 0):
        raise ControleInvalide("Provenance ou version du tirage incohérente.")
    quota = resultat.get("quota_par_strate")
    semence = resultat.get("semence")
    if type(quota) is not int or not 1 <= quota <= 50:
        raise ControleInvalide("Quota incorrect.")
    if not isinstance(semence, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{8,120}", semence):
        raise ControleInvalide("Semence incorrecte.")
    return {"source": source, "echantillon": resultat,
            "sha_index": sha, "quota": quota, "semence": semence}

