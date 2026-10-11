"""Confronter les six cas pilotes aux métadonnées BOAMP et BeauAMP vérifiées.

Chaque rapprochement BeauAMP reste une information secondaire indicative.
Le programme ne déduit ni déficit de compétences, ni marché unique, ni délai
d'identification, ni compétence publique réellement disponible.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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
    from scripts.rapprocher_avis_attributions import (
        fichiers_beauamp, lire_identifiant, COLONNES,
    )
except ModuleNotFoundError:
    from analyser_historique_boamp import BilanInvalide, produire
    from rapprocher_avis_attributions import (
        fichiers_beauamp, lire_identifiant, COLONNES,
    )

VERSION = "dossiers-pilotes-documentaires-v1"
ID_RE = re.compile(r"[0-9]{2}-[0-9]{2,8}")
MOT_RE = re.compile(r"[a-z0-9_]{3,80}")


def lire_cas(fichier: Path) -> list[dict]:
    document = json.loads(fichier.read_text(encoding="utf-8"))
    if (not isinstance(document, dict)
            or document.get("version") != "cas-pilotes-boamp-v1"
            or not isinstance(document.get("cas"), list)
            or not document["cas"]
            or document.get("verification_interpretative_effectuee") is not False):
        raise BilanInvalide("Registre des cas non reconnu.")
    vus = set()
    resultat = []
    for fiche in document["cas"]:
        if not isinstance(fiche, dict):
            raise BilanInvalide("Fiche pilote non structurée.")
        code = fiche.get("identifiant")
        jour = fiche.get("date_attendue")
        if not isinstance(code, str) or not ID_RE.fullmatch(code) or code in vus:
            raise BilanInvalide("Identifiant pilote absent ou répété.")
        try:
            attendu = date.fromisoformat(jour)
        except (ValueError, TypeError):
            raise BilanInvalide("Date pilote incorrecte.") from None
        hypotheses = fiche.get("hypotheses")
        if (attendu.isoformat() != jour
                or not isinstance(fiche.get("theme"), str)
                or not MOT_RE.fullmatch(fiche["theme"])
                or not isinstance(hypotheses, list)
                or not hypotheses
                or any(not isinstance(h, str) or not MOT_RE.fullmatch(h)
                       for h in hypotheses)
                or len(set(hypotheses)) != len(hypotheses)):
            raise BilanInvalide("Hypothèses ou date de pilote incorrectes.")
        vus.add(code)
        resultat.append(fiche)
    return resultat


def produire_dossiers(index: Path, preuve: Path,
                     beauamp: Path, registre: Path) -> dict:
    bilan = produire(index, preuve)
    cas = lire_cas(registre)
    archives, manifeste = fichiers_beauamp(beauamp)
    fiches = {}
    with closing(sqlite3.connect(f"file:{index.resolve().as_posix()}?mode=ro", uri=True)) as db:
        for cas_cible in cas:
            code = cas_cible["identifiant"]
            lignes = db.execute(
                "SELECT jour,identifiant,objet,acheteur,categorie,etat,avis,"
                "archive_source,releve_le FROM recherche WHERE identifiant = ?",
                (code,),
            ).fetchall()
            if len(lignes) != 1:
                raise BilanInvalide("Cas pilote absent ou identifiant BOAMP ambigu.")
            jour, identifiant, objet, acheteur, categorie, etat, lien, archive, date_releve = lignes[0]
            if jour != cas_cible["date_attendue"]:
                raise BilanInvalide("Date de parution du cas différente de la référence.")
            fiches[code] = {
                "identifiant_avis": identifiant,
                "date_parution": jour,
                "objet_officiel_normalise": objet,
                "acheteur_declare": acheteur,
                "etat_documentaire": etat,
                "categorie_marche": categorie,
                "lien_officiel": lien,
                "archive_boamp": archive,
                "releve_boamp_le": date_releve,
                "theme_de_recherche": cas_cible["theme"],
                "hypotheses_pre_enregistrees": cas_cible["hypotheses"],
                "pieces_de_consultation_examinees": False,
                "premier_avis_initial_retrouve": etat == "INITIAL",
                "origine_exacte_du_besoin_etablie": False,
                "capacite_disponible_etablie": False,
                "attribution_officielle_validee": False,
                "premiere_contribution_utile_mesuree": False,
                "appariements_secondaires": [],
            }
    suivis = Counter()
    fichiers_proches = defaultdict(set)
    identifiants_lots = defaultdict(set)
    dates_secondaires = defaultdict(set)
    for jour_fichier, chemin, fiche_source in archives:
        with chemin.open("r", encoding="utf-8-sig", newline="") as f:
            lecteur = csv.DictReader(f, delimiter=";")
            if not lecteur.fieldnames or not set(COLONNES) <= set(lecteur.fieldnames):
                raise BilanInvalide("Schéma BeauAMP quotidien absent.")
            for ligne in lecteur:
                matches = [
                    colonne for colonne in ("id_boamp_attribution", "id_boamp_contrat")
                    if lire_identifiant(ligne.get(colonne)) in fiches
                ]
                for colonne in matches:
                    identifiant = lire_identifiant(ligne.get(colonne))
                    suivis[(identifiant, colonne)] += 1
                    fichiers_proches[identifiant].add(fiche_source["chemin"])
                    lot = (ligne.get("id_lot") or "").strip()
                    if lot:
                        identifiants_lots[identifiant].add(lot)
                    date_attribution = (ligne.get("date_avis_attribution") or "").strip()
                    if date_attribution:
                        dates_secondaires[identifiant].add(date_attribution)
                    sortie = fiches[identifiant]["appariements_secondaires"]
                    # Conserver une observation par source, type, lot et date.
                    # Les lignes distinctes sont comptées, sans créer de marchés uniques.
                    signature = (
                        colonne, fiche_source["chemin"], lot,
                        date_attribution, (ligne.get("objet") or "")[:250],
                    )
                    if len(sortie) < 20 and not any(
                        tuple(x["signature_documentaire"]) == signature for x in sortie
                    ):
                        sortie.append({
                            "signature_documentaire": list(signature),
                            "type_identifiant": colonne,
                            "fichier_source": fiche_source["chemin"],
                            "empreinte_fichier_source": fiche_source["sha256"],
                            "identifiant_lot_declare": lot or None,
                            "date_avis_attribution_declaree": date_attribution or None,
                            "objet_secondaire": (ligne.get("objet") or "")[:250],
                            "source_indicative": True,
                        })
