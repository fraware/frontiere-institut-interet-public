from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.models import BenchmarkCase


def principal() -> None:
    analyseur = argparse.ArgumentParser(description="Exporte les cas d'évaluation sans leurs références.")
    analyseur.add_argument("--sortie", default="jeu_evaluation_aveugle.json")
    arguments = analyseur.parse_args()

    with SessionLocal() as db:
        cas = list(
            db.scalars(
                select(BenchmarkCase)
                .where(BenchmarkCase.active.is_(True))
                .order_by(BenchmarkCase.code)
            ).all()
        )
        contenu = {
            "version_schema": "0.5.1",
            "cas": [
                {
                    "code": item.code,
                    "titre": item.title,
                    "question": item.prompt,
                    "qualite_reference": item.label_quality,
                }
                for item in cas
            ],
        }

    chemin = Path(arguments.sortie)
    chemin.write_text(json.dumps(contenu, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(contenu['cas'])} cas exportés vers {chemin}")


if __name__ == "__main__":
    principal()
