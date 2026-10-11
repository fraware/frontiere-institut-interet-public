"""Rapprocher des identifiants BOAMP explicites d'archives BeauAMP vérifiées."""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import closing
import csv
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile

try:
    from scripts.analyser_historique_boamp import BilanInvalide, produire
except ModuleNotFoundError:
    from analyser_historique_boamp import BilanInvalide, produire

VERSION = "appariement-documentaire-boamp-beauamp-v1"
VERSION_BEAUAMP = "beauamp-quotidiens-v1"
IDENTIFIANT = re.compile(r"[0-9]{2}-[0-9]{2,8}")
SHA = re.compile(r"[0-9a-f]{64}")
JOUR = re.compile(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}")
COLONNES = ("id_boamp_attribution", "id_boamp_contrat",
            "date_avis_attribution", "date_avis_marche", "objet", "id_lot")


def sha256(chemin):
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(1_048_576), b""):
            h.update(bloc)
    return h.hexdigest()


def lire_identifiant(valeur):
    texte = str(valeur or "").strip()
    return texte if IDENTIFIANT.fullmatch(texte) else None


def fichiers_beauamp(racine):
    manifeste = json.loads((racine / "manifest.json").read_text(encoding="utf-8"))
    if (manifeste.get("version") != VERSION_BEAUAMP
            or manifeste.get("licence") != "cc-by-sa"
            or len(manifeste.get("fichiers", [])) != manifeste.get("nombre_fichiers")):
        raise BilanInvalide("Manifeste BeauAMP incorrect.")
    uniques, resultat = set(), []
    for fiche in manifeste["fichiers"]:
        jour = fiche.get("jour")
        if not isinstance(jour, str) or not JOUR.fullmatch(jour):
            raise BilanInvalide("Date BeauAMP incorrecte.")
        if date.fromisoformat(jour).isoformat() != jour:
            raise BilanInvalide("Date BeauAMP non canonique.")
        chemin_relatif = f"quotidiens/{jour}.csv"
        if fiche.get("chemin") != chemin_relatif or jour in uniques:
            raise BilanInvalide("Fichier BeauAMP dupliqué ou déplacé.")
        uniques.add(jour)
        chemin = racine / chemin_relatif
        if not chemin.is_file() or chemin.is_symlink():
            raise BilanInvalide("Fichier BeauAMP manquant.")
        resultat.append((jour, chemin, fiche))
    return sorted(resultat), manifeste


