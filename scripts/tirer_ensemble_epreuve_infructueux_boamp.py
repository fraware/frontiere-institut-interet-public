"""Tirer un ensemble d'épreuve enrichi, séparé des 36 cas indépendants.

Un mot de titre 'infructueux' est une piste de recherche, PAS une
étiquette de lot sans offre. Le prélèvement est délibérément biaisé.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import unicodedata

try:
    from scripts.relever_issues_echantillon_independant import charger_tirage
    from scripts.tirer_jeu_independant_boamp import EXCLUS
except ModuleNotFoundError:
    from relever_issues_echantillon_independant import charger_tirage
    from tirer_jeu_independant_boamp import EXCLUS

VERSION = "ensemble-epreuve-infructueux-v1"
MOIS = ("2025-07", "2025-09", "2025-10", "2026-01", "2026-03", "2026-06")
QUOTA = 4
SEMENCE = "frontiere-challenge-infructueux-2026-10-12-v1"
EMPREINTE_BASE = "40f791c35adcdc67d69bb933e873b0efaa7b24dd0c74958474dc6272b94242c8"


class EpreuveInvalide(ValueError):
    """Le périmètre annoncé ou l'intégrité n'est pas respecté."""


def normaliser(x):
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", x).casefold()
                           if not unicodedata.combining(c)).split())


def tirer(index: Path, preuve: Path, jeu_base: Path):
    base = charger_tirage(jeu_base)
    if base["sha256_identifiants_ordonnes"] != EMPREINTE_BASE:
        raise EpreuveInvalide("Tirage de référence différent des 36 cas engagés.")
    avant = {item["avis"] for item in base["cas"]}
    manifeste = json.loads(preuve.read_text(encoding="utf-8"))
    empreinte = hashlib.sha256(index.read_bytes()).hexdigest()
    if manifeste.get("sha256_index") != empreinte:
        raise EpreuveInvalide("Index ne correspond pas à sa preuve.")
    with sqlite3.connect(f"file:{index.resolve()}?mode=ro", uri=True) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise EpreuveInvalide("Index SQLite invalide.")
        candidats = db.execute(
            "SELECT jour, identifiant, objet, acheteur FROM recherche "
            "WHERE recherche MATCH ? AND substr(jour,1,7) IN (" +
            ",".join("?" for _ in MOIS) + ")",
            ("infructueux", *MOIS),
        ).fetchall()

    groupes = {m: [] for m in MOIS}
    for jour, identifiant, objet, acheteur in candidats:
        if (not all(isinstance(x, str) for x in
                    (jour, identifiant, objet, acheteur))
                or identifiant in EXCLUS or identifiant in avant):
            continue
        mois = jour[:7]
        serie = hashlib.sha256(
            (normaliser(acheteur) + "\0" + normaliser(objet)).encode()
        ).hexdigest()
        alea = hashlib.sha256(
            (SEMENCE + "\0" + mois + "\0" + identifiant).encode()
        ).hexdigest()
        groupes[mois].append((alea, identifiant, jour, objet, acheteur, serie))
    choisis, series = [], set()
    for mois in MOIS:
        n = 0
        for _, identifiant, jour, objet, acheteur, serie in sorted(groupes[mois]):
            if serie in series:
                continue
            series.add(serie)
            choisis.append({
                "avis": identifiant, "date_parution": jour,
                "objet": objet, "acheteur": acheteur,
                "sha256_serie_acheteur_objet": serie,
                "issue_reelle": None,
                "motif_officiel_absence_offres_confirme": False,
            })
            n += 1
            if n == QUOTA:
                break
        if n != QUOTA:
            raise EpreuveInvalide(f"Quota indisponible pour {mois} ({n}/{QUOTA}).")
    ids = [x["avis"] for x in choisis]
    digest = hashlib.sha256(json.dumps(
        ids, ensure_ascii=False, separators=(",", ":")
    ).encode()).hexdigest()
    return {
        "version": VERSION,
        "nombre_cas": len(choisis),
        "mois": list(MOIS),
        "quota_par_mois": QUOTA,
        "sha256_index": empreinte,
        "sha256_tirage_original": EMPREINTE_BASE,
        "semence": SEMENCE,
        "expression_recherche_pre_enregistree": "infructueux",
        "sha256_identifiants_ordonnes": digest,
        "cas": choisis,
        "selection_sur_mention_potentiellement_liee_au_resultat": True,
        "selection_sans_information_de_resultat": False,
        "ensemble_representatif": False,
        "issues_verifiees_par_lot": False,
        "evaluation_independante_effectuee": False,
        "interpretation": (
            "Un titre avec 'infructueux' ne prouve pas zéro offre : il peut "
            "signaler une nouvelle consultation, un abandon ou une autre "
            "forme d'échec. Corpus distinct et enrichi ; ne jamais regrouper "
            "ses métriques avec celles du tirage initial de 36 cas."
        ),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--preuve-index", type=Path, required=True)
    p.add_argument("--tirage-original", type=Path, required=True)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args()
    if a.sortie.exists():
        p.exit(1, "Sortie existante : refus d'écrasement.\n")
    try:
        rapport = tirer(a.index, a.preuve_index, a.tirage_original)
        a.sortie.parent.mkdir(parents=True, exist_ok=True)
        with a.sortie.open("x", encoding="utf-8") as f:
            json.dump(rapport, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")
    except (ValueError, OSError, sqlite3.DatabaseError) as e:
        p.exit(1, f"Ensemble d'épreuve non validé : {e}\n")
    print(json.dumps({
        "cas": rapport["nombre_cas"],
        "sha256": rapport["sha256_identifiants_ordonnes"],
        "etiquettes_verifiees": rapport["issues_verifiees_par_lot"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
