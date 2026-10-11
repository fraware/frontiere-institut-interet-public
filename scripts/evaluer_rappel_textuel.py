"""Comparer le rappel textuel exact du moteur classique et du croisement v3."""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import os
import tempfile

try:
    from scripts.analyser_historique_boamp import produire, BilanInvalide
    from scripts.constituer_pistes_boamp import constituer
    from scripts.croiser_pistes_capacites import (
        expressions_avis, preuves_exactes, chercher_expressions_exactes,
    )
    from scripts.rechercher_capacites_institutionnelles import (
        ouvrir_index, verifier_sources, chercher, normaliser,
    )
except ModuleNotFoundError:
    from analyser_historique_boamp import produire, BilanInvalide
    from constituer_pistes_boamp import constituer
    from croiser_pistes_capacites import (
        expressions_avis, preuves_exactes, chercher_expressions_exactes,
    )
    from rechercher_capacites_institutionnelles import (
        ouvrir_index, verifier_sources, chercher, normaliser,
    )

VERSION = "banc-rappel-textuel-capacites-v1"
CHAMPS = ("capacite_index", "mission_index", "domaine_index", "nom_index")
SORTIES = (
    "correspondances_aux_missions_ou_capacites_publiees",
    "correspondances_aux_domaines_scientifiques_publies",
    "correspondances_de_nom_uniquement",
)


def reference_exacte(db, expression):
    tokens = normaliser(expression)
    if not tokens or len(tokens) > 10:
        raise BilanInvalide("Expression à évaluer invalide.")
    candidat_ids = set()
    phrase = " ".join(tokens)
    for champ in CHAMPS:
        for code, in db.execute(
            "SELECT o.identifiant FROM termes AS t "
            "JOIN organismes AS o ON o.numero=t.rowid "
            "WHERE termes MATCH ? AND o.etat='ACTIF'",
            (f'{champ} : "{phrase}"',),
        ):
            candidat_ids.add(code)
    resultat = sorted(code for code in candidat_ids if preuves_exactes(
        db, code, expression,
    ))
    digest = hashlib.sha256(
        json.dumps(resultat, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return set(resultat), digest


def ids_verifies(db, candidats, expression):
    return {
        item["identifiant"] for item in candidats
        if preuves_exactes(db, item["identifiant"], expression)
    }


