"""Tirage stratifié documentaire BOAMP, avec dénominateurs et témoins lexicaux."""
from __future__ import annotations
import argparse
import calendar
from collections import Counter, defaultdict
from contextlib import closing
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile

try:
    from scripts.analyser_historique_boamp import (
        MOTIFS, BilanInvalide, produire, normaliser,
    )
except ModuleNotFoundError:
    from analyser_historique_boamp import (
        MOTIFS, BilanInvalide, produire, normaliser,
    )

VERSION = "echantillon-exploratoire-boamp-v1"
TEMOIN = "temoin_sans_expression_des_sept_domaines"
SEMENCE = "frontiere-exploration-2026-10-v1"


def categorie_strate(valeur):
    if valeur is None:
        return "AUTRE"
    if not isinstance(valeur, str):
        raise BilanInvalide("Catégorie incorrecte.")
    texte = normaliser(valeur)
    for categorie in ("SERVICES", "FOURNITURES", "TRAVAUX"):
        if categorie.lower() in texte:
            return categorie
    return "AUTRE"


def mois_couverts(jours):
    presentes = set(jours)
    if not presentes or len(presentes) != len(jours):
        raise BilanInvalide("Journées absentes ou répétées.")
    for valeur in jours:
        try:
            if date.fromisoformat(valeur).isoformat() != valeur:
                raise ValueError("non canonique")
        except ValueError as erreur:
            raise BilanInvalide("Date documentaire incorrecte.") from erreur
    debut, fin = date.fromisoformat(min(jours)), date.fromisoformat(max(jours))
    y, m = debut.year, debut.month
    complets, couverture = [], []
    while (y, m) <= (fin.year, fin.month):
        mois = f"{y:04d}-{m:02d}"
        attendus = calendar.monthrange(y, m)[1]
        vus = sum(f"{mois}-{n:02d}" in presentes for n in range(1, attendus + 1))
        ok = vus == attendus
        couverture.append({"mois": mois, "jours_archives": vus,
                           "jours_calendaires": attendus, "mois_complet": ok})
        if ok:
            complets.append(mois)
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return complets, couverture


def rang(semence, strate, jour, identifiant):
    message = json.dumps([semence, *strate, jour, identifiant],
                         ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(message.encode("utf-8")).hexdigest()


def selectionner(groupes, strate, notice, quota):
    liste = groupes[strate]
    if len(liste) < quota:
        liste.append(notice)
        return
    pire = max(range(len(liste)), key=lambda k: (
        liste[k]["rang_sha256"], liste[k]["date_parution"], liste[k]["identifiant"]))
    if (notice["rang_sha256"], notice["date_parution"], notice["identifiant"]) < (
        liste[pire]["rang_sha256"], liste[pire]["date_parution"], liste[pire]["identifiant"]):
        liste[pire] = notice


