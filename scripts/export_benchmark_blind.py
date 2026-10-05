from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.models import BenchmarkCase


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporte le banc FRONTIÈRE sans références ni étiquettes.")
    parser.add_argument("--output", default="benchmark_blind.json")
    args = parser.parse_args()

    with SessionLocal() as db:
        cases = list(
            db.scalars(
                select(BenchmarkCase)
                .where(BenchmarkCase.active.is_(True))
                .order_by(BenchmarkCase.code)
            ).all()
        )
        payload = {
            "schema_version": "0.5.1",
            "cases": [
                {
                    "code": case.code,
                    "title": case.title,
                    "prompt": case.prompt,
                    "label_quality": case.label_quality,
                }
                for case in cases
            ],
        }

    path = Path(args.output)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(payload['cases'])} cas exportés vers {path}")


if __name__ == "__main__":
    main()
