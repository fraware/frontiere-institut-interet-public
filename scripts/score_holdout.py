from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def norm(values):
    return {str(v).strip().upper() for v in values if str(v).strip()}


def metrics(expected, predicted):
    gold = norm(expected)
    pred = norm(predicted)
    if not gold:
        return {"precision": None, "recall": None, "f1": None}
    precision = len(gold & pred) / len(pred) if pred else 0.0
    recall = len(gold & pred) / len(gold)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    p = argparse.ArgumentParser(description="Score un run HOLDOUT FRONTIÈRE hors du dépôt public.")
    p.add_argument("--blind", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--labels", required=True)
    p.add_argument("--predictions", required=True)
    p.add_argument("--output", default="holdout_score.json")
    args = p.parse_args()

    blind_path = Path(args.blind)
    manifest_path = Path(args.manifest)
    labels_path = Path(args.labels)
    predictions_path = Path(args.predictions)

    blind = json.loads(blind_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    predictions = json.loads(predictions_path.read_text(encoding="utf-8"))

    actual_hash = sha256(labels_path)
    expected_hash = manifest["labels_sha256"]
    if actual_hash != expected_hash:
        raise SystemExit(f"labels hash mismatch: {actual_hash} != {expected_hash}")

    blind_codes = {c["code"] for c in blind["cases"]}
    labels_by_code = {c["code"]: c for c in labels["cases"]}
    predicted_by_code = {c["code"]: c for c in predictions["cases"]}
    if blind_codes != set(labels_by_code):
        raise SystemExit("blind/labels case mismatch")
    missing = sorted(blind_codes - set(predicted_by_code))
    extra = sorted(set(predicted_by_code) - blind_codes)
    if missing or extra:
        raise SystemExit(f"prediction case mismatch: missing={missing}, extra={extra}")

    rows = []
    for code in sorted(blind_codes):
        gold = labels_by_code[code]
        pred = predicted_by_code[code]
        route = metrics(gold.get("expected_routes", []), pred.get("routes", []))
        forms = metrics(gold.get("expected_resource_forms", []), pred.get("resource_forms", []))
        rows.append({
            "code": code,
            "route": route,
            "resource_forms": forms,
            "analyst_minutes": max(0, pred.get("analyst_minutes", 0)),
            "verification_minutes": max(0, pred.get("verification_minutes", 0)),
            "elapsed_seconds": pred.get("elapsed_seconds"),
            "evidence_count": len(pred.get("evidence_urls", [])),
        })

    def mean(field, subfield):
        vals = [r[field][subfield] for r in rows if r[field][subfield] is not None]
        return sum(vals) / len(vals) if vals else None

    report = {
        "schema_version": "holdout-score-v1",
        "method": predictions.get("method"),
        "method_version": predictions.get("method_version"),
        "case_count": len(rows),
        "labels_sha256": actual_hash,
        "route_precision_mean": mean("route", "precision"),
        "route_recall_mean": mean("route", "recall"),
        "route_f1_mean": mean("route", "f1"),
        "resource_form_precision_mean": mean("resource_forms", "precision"),
        "resource_form_recall_mean": mean("resource_forms", "recall"),
        "resource_form_f1_mean": mean("resource_forms", "f1"),
        "human_minutes_total": sum(r["analyst_minutes"] + r["verification_minutes"] for r in rows),
        "evidence_count_total": sum(r["evidence_count"] for r in rows),
        "cases": rows,
    }
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
