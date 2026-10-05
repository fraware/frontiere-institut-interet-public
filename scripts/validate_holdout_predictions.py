from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_CASE_FIELDS = {
    "code",
    "routes",
    "resource_forms",
    "resources",
    "evidence_urls",
    "elapsed_seconds",
    "analyst_minutes",
    "verification_minutes",
    "notes",
}


def main() -> None:
    p = argparse.ArgumentParser(description="Valide un fichier de prédictions HOLDOUT avant gel.")
    p.add_argument("--blind", required=True)
    p.add_argument("--predictions", required=True)
    args = p.parse_args()

    blind = json.loads(Path(args.blind).read_text(encoding="utf-8"))
    predictions = json.loads(Path(args.predictions).read_text(encoding="utf-8"))

    if predictions.get("schema_version") != "holdout-predictions-v1":
        raise SystemExit("schema_version must be holdout-predictions-v1")
    if not predictions.get("method") or not predictions.get("method_version"):
        raise SystemExit("method and method_version are required")

    blind_codes = [c["code"] for c in blind["cases"]]
    rows = predictions.get("cases")
    if not isinstance(rows, list):
        raise SystemExit("cases must be a list")

    seen = []
    for row in rows:
        missing = REQUIRED_CASE_FIELDS - set(row)
        if missing:
            raise SystemExit(f"{row.get('code','?')}: missing fields {sorted(missing)}")
        code = row["code"]
        seen.append(code)
        for name in ("routes", "resource_forms", "resources", "evidence_urls"):
            if not isinstance(row[name], list):
                raise SystemExit(f"{code}: {name} must be a list")
        if row["analyst_minutes"] < 0 or row["verification_minutes"] < 0:
            raise SystemExit(f"{code}: minutes must be non-negative")
        if row["elapsed_seconds"] is not None and row["elapsed_seconds"] < 0:
            raise SystemExit(f"{code}: elapsed_seconds must be non-negative")

    if len(seen) != len(set(seen)):
        raise SystemExit("duplicate case codes")
    missing = sorted(set(blind_codes) - set(seen))
    extra = sorted(set(seen) - set(blind_codes))
    if missing or extra:
        raise SystemExit(f"case mismatch: missing={missing}, extra={extra}")

    print(f"valid: {predictions['method']} {predictions['method_version']} — {len(rows)} cases")


if __name__ == "__main__":
    main()
