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


def constituer(index, preuve, bilan, *, quota=4, semence=SEMENCE):
    if type(quota) is not int or not 1 <= quota <= 50:
        raise BilanInvalide("Quota par strate incorrect.")
    if not isinstance(semence, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{8,120}", semence):
        raise BilanInvalide("Semence incorrecte.")
    reference = produire(index, preuve)
    if json.loads(bilan.read_text(encoding="utf-8")) != reference:
        raise BilanInvalide("Bilan différent de l'index vérifié.")
    groupes = defaultdict(list)
    effectifs = Counter()
    suivis = set()
    nombre, exclus, multit = 0, 0, 0
    motifs = {t: [re.compile(x) for x in m] for t, m in MOTIFS.items()}
    with closing(sqlite3.connect(f"file:{index.resolve().as_posix()}?mode=ro", uri=True)) as con:
        dates = [j for (j,) in con.execute("SELECT jour FROM provenance ORDER BY jour")]
        complets, couverture = mois_couverts(dates)
        retenus = set(complets)
        for jour, code, objet, acheteur, categorie, lien, archive, releve in con.execute(
            "SELECT jour,identifiant,objet,acheteur,categorie,avis,archive_source,releve_le "
            "FROM recherche ORDER BY jour,identifiant"
        ):
            nombre += 1
            if (jour, code) in suivis:
                raise BilanInvalide("Avis dupliqué dans l'index.")
            suivis.add((jour, code))
            if not isinstance(objet, str):
                raise BilanInvalide("Objet documentaire incorrect.")
            expression = normaliser(objet)
            domaines = [theme for theme, regles in motifs.items()
                        if any(r.search(expression) for r in regles)]
            multit += len(domaines) > 1
            mois = jour[:7]
            if mois not in retenus:
                exclus += 1
                continue
            cat = categorie_strate(categorie)
            for theme in domaines or [TEMOIN]:
                strate = (mois, cat, theme)
                effectifs[strate] += 1
                selectionner(groupes, strate, {
                    "date_parution": jour, "identifiant": code,
                    "objet": objet[:500],
                    "acheteur_declare": (acheteur or "")[:200],
                    "categorie_declaree": categorie,
                    "lien_officiel": lien, "archive_source": archive,
                    "releve_le": releve, "themes_detectes": domaines,
                    "rang_sha256": rang(semence, strate, jour, code),
                    "besoin_scientifique_valide": False,
                    "competence_mobilisable_etablie": False,
                }, quota)
    if nombre != reference["nombre_avis"] or not complets:
        raise BilanInvalide("Couverture historique insuffisante ou incohérente.")
