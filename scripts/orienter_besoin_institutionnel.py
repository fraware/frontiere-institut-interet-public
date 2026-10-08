"""Exécuter localement l'orientation d'une requête de capacité déjà verrouillée."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys

# L'appel "python scripts/..." doit retrouver le paquet app à la racine.
RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

from app.config import settings
from app.database import SessionLocal
from app.orientation import executer_sur_dossier
from scripts.rechercher_capacites_institutionnelles import DEFAULT_ENTITES, DEFAULT_INDEX


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Orienter un dossier verrouillé à partir du référentiel institutionnel local."
    )
    parser.add_argument("--episode", required=True, help="Code exact du dossier déjà enregistré.")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--entites", type=Path, default=DEFAULT_ENTITES)
    parser.add_argument("--limite", type=int, default=8, help="Nombre de pistes par classe et par clause.")
    args = parser.parse_args()
    if settings.env.strip().lower() not in {"development", "test", "testing"}:
        parser.exit(1, "Démarrage refusé : exécution réservée à une instance locale expérimentale.\n")
    with SessionLocal() as db:
        try:
            resultat = executer_sur_dossier(
                db, code=args.episode, index_path=args.index,
                entites=args.entites, limite=args.limite,
            )
        except (ValueError, OSError, sqlite3.Error) as exc:
            db.rollback()
            parser.exit(1, f"Orientation documentaire refusée : {exc}\n")
    print(json.dumps(resultat, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
