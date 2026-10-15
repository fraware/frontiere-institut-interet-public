"""Rattrapage progressif de l'historique TED français, sans retraitement inutile.

La table captures_ted fait office de calendrier persistant : une date est
couverte seulement après l'importation transactionnelle de toutes ses pages.
Les dates absentes sont reprises de la plus ancienne à la plus récente.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import sys
import time
from typing import Callable
from urllib.error import HTTPError, URLError

from app.collecteur_ted_continu import (
    StockageTED, collecter_jour, TEDInvalide,
)

DEBUT_INITIAL = date(2024, 1, 1)
MARGE_JOURS = 4
MAX_JOURS_PAR_CYCLE = 12


def dates_manquantes(
    stockage: StockageTED, depuis: date, jusquau: date, *,
    maximum: int = MAX_JOURS_PAR_CYCLE,
) -> tuple[list[date], int, int]:
    """Retrouver les journées absentes au moyen du calendrier SQL existant."""
    if (not isinstance(depuis, date) or not isinstance(jusquau, date) or
            depuis < date(1995, 1, 1) or jusquau < depuis):
        raise ValueError("Intervalle historique TED incorrect.")
    if type(maximum) is not int or not 1 <= maximum <= MAX_JOURS_PAR_CYCLE:
        raise ValueError("Nombre de journées par passage non admissible.")
    with stockage.connexion() as conn:
        connues = {
            ligne[0] for ligne in conn.execute(
                "SELECT jour FROM captures_ted WHERE jour >= ? AND jour <= ?",
                (depuis.isoformat(), jusquau.isoformat()),
            )
        }
    total = (jusquau - depuis).days + 1
    manquantes, nombre_absentes = [], 0
    for index in range(total):
        jour = depuis + timedelta(days=index)
        if jour.isoformat() not in connues:
            nombre_absentes += 1
            if len(manquantes) < maximum:
                manquantes.append(jour)
    return manquantes, len(connues), nombre_absentes


def passage(
    stockage: StockageTED, *, debut: date = DEBUT_INITIAL,
    maximum: int = 3,
    aujourd_hui: date | None = None,
    obtenir: Callable = collecter_jour,
) -> dict:
    """Importer une tranche historique, avec reprises après panne par journée."""
    present = aujourd_hui or datetime.now(timezone.utc).date()
    if not isinstance(present, date):
        raise ValueError("Horloge de collecte TED invalide.")
    limite = present - timedelta(days=MARGE_JOURS)
    if debut > limite:
        return {
            "premiere_date": debut.isoformat(),
            "derniere_date_eligible": limite.isoformat(),
            "jours_couverts": 0, "jours_manquants": 0, "jours_tentes": 0,
            "jours_importes": 0, "erreurs": [],
            "etat": "periode_non_encore_eligible",
        }
    manquantes, connues, absentes = dates_manquantes(
        stockage, debut, limite, maximum=maximum
    )
    resultat = {
        "premiere_date": debut.isoformat(),
        "derniere_date_eligible": limite.isoformat(),
        "jours_couverts_avant": connues,
        "jours_manquants_avant": absentes,
        "jours_tentes": 0,
        "jours_importes": 0,
        "avis_importes": 0,
        "erreurs": [],
    }
    for jour in manquantes:
        resultat["jours_tentes"] += 1
        try:
            notices, pages = obtenir(jour)
            if not isinstance(notices, list) or type(pages) is not int or pages < 1:
                raise TEDInvalide("Réponse de journée TED invalide.")
            stockage.importer(jour, notices, pages)
            resultat["jours_importes"] += 1
            resultat["avis_importes"] += len(notices)
        except (OSError, ValueError, HTTPError, URLError, sqlite3.Error) as exc:
            resultat["erreurs"].append({
                "jour": jour.isoformat(), "erreur": type(exc).__name__,
            })
    restantes, couvertes, absences = dates_manquantes(
        stockage, debut, limite, maximum=1
    )
    resultat["jours_couverts_apres"] = couvertes
    resultat["jours_manquants_apres"] = absences
    resultat["prochaine_date_manquante"] = (
        restantes[0].isoformat() if restantes else None
    )
    resultat["etat"] = (
        "complet" if absences == 0 else
        "partiel_avec_erreurs" if resultat["erreurs"] else "en_progression"
    )
    return resultat


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--depuis", type=date.fromisoformat,
                        default=DEBUT_INITIAL)
    parser.add_argument("--maximum", type=int, default=3)
    sous = parser.add_subparsers(dest="action", required=True)
    sous.add_parser("collecter")
    suivi = sous.add_parser("suivre")
    suivi.add_argument("--intervalle", type=int, default=21600)
    args = parser.parse_args(argv)
    if args.action == "suivre" and not 3600 <= args.intervalle <= 86400:
        parser.error("Intervalle de suivi hors limites.")
    try:
        stockage = StockageTED(args.base)
        while True:
            resultat = passage(
                stockage, debut=args.depuis, maximum=args.maximum
            )
            print(json.dumps(resultat, ensure_ascii=False, sort_keys=True),
                  flush=True)
            if args.action != "suivre":
                return 0 if not resultat["erreurs"] else 1
            time.sleep(args.intervalle)
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"Rattrapage TED : {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
