from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import json
import statistics
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import BenchmarkCase, BenchmarkPrediction, Discovery, Episode, EpisodeResult, Hypothesis, KnowledgeItem, NeedVersion, ReuseEvent, SearchRun, StakeholderContact

PUBLIC_RESULTS = {"P0", "P1", "P2", "P3"}
HOST_STATES = {"PASS", "FAIL", "UNKNOWN", "NON_APPLICABLE"}


def classify_public_search(*, complete: bool, relevant_found: bool | None, mobilizable_found: bool | None) -> str:
    """Classification conservative de la recherche publique.

    P0: recherche insuffisante pour conclure.
    P1: capacité publique pertinente et mobilisable.
    P2: capacité publique pertinente identifiée, mobilisation non établie/échouée.
    P3: recherche suffisante et aucune capacité publique suffisamment pertinente identifiée.
    """
    if mobilizable_found is True and relevant_found is not True:
        raise ValueError("Une capacité déclarée mobilisable doit d'abord être identifiée comme pertinente.")
    if not complete or relevant_found is None:
        return "P0"
    if relevant_found is True:
        return "P1" if mobilizable_found is True else "P2"
    return "P3"


def host_ready(states: Iterable[str]) -> bool:
    states = list(states)
    return bool(states) and all(s == "PASS" for s in states)


def critical_path_minutes(events: list[tuple[datetime, datetime | None, int | None]]) -> int | None:
    """Somme maximale des durées déclarées sur les dépendances représentées.

    Un parent doit correspondre à un événement antérieur dans la liste ; le
    graphe représenté possède donc un parent au maximum par événement. La
    valeur est inconnue si une opération est ouverte ou si la liste est vide.
    Les durées invalides et les liens incorrects sont refusés explicitement.

    Cette mesure ne constitue ni un chemin critique temporel prenant en compte
    les attentes et les chevauchements, ni le délai jusqu'à une contribution
    utile ; celui-ci est documenté indépendamment.
    """
    if not events:
        return None

    incomplet = False
    for numero, (debut, fin, parent_idx) in enumerate(events):
        if not isinstance(debut, datetime) or debut.utcoffset() is None:
            raise ValueError("Chaque début doit être une date avec fuseau horaire.")
        if parent_idx is not None and (
            type(parent_idx) is not int or not 0 <= parent_idx < numero
        ):
            raise ValueError("Chaque dépendance doit référencer un événement antérieur.")
        if fin is None:
            incomplet = True
            continue
        if not isinstance(fin, datetime) or fin.utcoffset() is None:
            raise ValueError("Chaque fin connue doit être une date avec fuseau horaire.")
        if fin < debut:
            raise ValueError("La fin d'un événement précède son début.")

    if incomplet:
        return None

    scores: list[int] = []
    for debut, fin, parent_idx in events:
        # Toutes les fins sont connues ici, après la vérification précédente.
        assert fin is not None
        duree = int((fin - debut).total_seconds() // 60)
        score_parent = scores[parent_idx] if parent_idx is not None else 0
        scores.append(score_parent + duree)
    return max(scores)



def elapsed_span_minutes(events: list[tuple[datetime, datetime | None, int | None]]) -> int | None:
    """Durée calendaire du premier début à la dernière fin observée.

    Le calcul accepte les chevauchements et conserve les attentes. Une date
    manquante rend l'intervalle complet inconnu ; une date invalide est refusée.
    Le résultat ne prouve pas la date de première contribution utile.
    """
    if not events:
        return None
    incomplet = False
    for debut, fin, _ in events:
        if not isinstance(debut, datetime) or debut.utcoffset() is None:
            raise ValueError("Chaque début doit être une date avec fuseau horaire.")
        if fin is None:
            incomplet = True
            continue
        if not isinstance(fin, datetime) or fin.utcoffset() is None:
            raise ValueError("Chaque fin connue doit être une date avec fuseau horaire.")
        if fin < debut:
            raise ValueError("La fin d'un événement précède son début.")
    if incomplet:
        return None
    premiere_date = min(debut for debut, _, _ in events)
    derniere_date = max(fin for _, fin, _ in events if fin is not None)
    return int((derniere_date - premiere_date).total_seconds() // 60)



def dashboard_metrics(db: Session) -> dict:
    episodes = db.scalars(select(Episode).where(Episode.synthetic.is_(False))).all()
    synthetic = db.scalar(select(func.count(Episode.id)).where(Episode.synthetic.is_(True))) or 0
    demand = Counter(e.demand_level for e in episodes)
    statuses = Counter(e.status for e in episodes)

    public_runs = db.scalars(
        select(SearchRun).join(Episode)
        .where(Episode.synthetic.is_(False), SearchRun.search_type == "PUBLIQUE")
        .order_by(SearchRun.id)
    ).all()
    latest_public = {r.episode_id: r for r in public_runs}
    public_results = Counter(
        r.public_result for r in latest_public.values() if r.public_result
    )

    closed_results = db.scalars(
        select(EpisodeResult).join(Episode)
        .where(Episode.synthetic.is_(False))
        .order_by(EpisodeResult.id)
    ).all()
    latest_results = {r.episode_id: r for r in closed_results}
    reuse_count = db.scalar(
        select(func.count(ReuseEvent.id)).join(Episode, ReuseEvent.destination_episode_id == Episode.id).where(Episode.synthetic.is_(False))
    ) or 0
    knowledge_count = db.scalar(select(func.count(KnowledgeItem.id))) or 0
    contacts_active = db.scalar(select(func.count(StakeholderContact.id)).where(StakeholderContact.status.notin_(["CLOS", "ABANDONNE"]))) or 0
    needs_locked = db.scalar(select(func.count(Episode.id)).join(Episode.needs).where(Episode.synthetic.is_(False), NeedVersion.active.is_(True), NeedVersion.locked_at.is_not(None))) or 0

    return {
        "episodes": len(episodes),
        "synthetic": synthetic,
        "d2_plus": sum(demand[k] for k in ("D2", "D3", "D4")),
        "demand": dict(demand),
        "statuses": dict(statuses),
        "public_results": dict(public_results),
        "public_search_records": len(public_runs),
        "public_search_episodes": len(latest_public),
        "results": len(closed_results),
        "result_episodes": len(latest_results),
        "reuse_events": reuse_count,
        "knowledge_items": knowledge_count,
        "contacts_active": contacts_active,
        "needs_locked": needs_locked,
    }


def hypothesis_summary(db: Session) -> list[Hypothesis]:
    return list(db.scalars(select(Hypothesis).order_by(Hypothesis.code)).all())


def empirical_metrics(db: Session) -> dict:
    episodes = list(db.scalars(select(Episode).where(Episode.synthetic.is_(False)).order_by(Episode.id)).all())
    demand = Counter(e.demand_level for e in episodes)
    organizations = len({e.organization_id for e in episodes})
    known_preexisting = [e for e in episodes if e.need_preexisting_frontiere is not None]
    preexisting_yes = sum(1 for e in known_preexisting if e.need_preexisting_frontiere is True)

    latest_public: dict[int, SearchRun] = {}
    for run in db.scalars(
        select(SearchRun)
        .join(Episode)
        .where(Episode.synthetic.is_(False), SearchRun.search_type == "PUBLIQUE")
        .order_by(SearchRun.id)
    ).all():
        latest_public[run.episode_id] = run
    public_results = Counter(r.public_result for r in latest_public.values() if r.public_result)

    r5_query = (
        select(Discovery.resource_id)
        .join(SearchRun, Discovery.search_run_id == SearchRun.id)
        .join(Episode, SearchRun.episode_id == Episode.id)
        .where(Episode.synthetic.is_(False), Discovery.state == "R5")
    )
    r5_resource_ids = db.scalars(r5_query).all()

    result_rows = list(db.scalars(
        select(EpisodeResult).join(Episode)
        .where(Episode.synthetic.is_(False))
        .order_by(EpisodeResult.id)
    ).all())
    latest_results = {r.episode_id: r for r in result_rows}
    result_statuses = Counter(r.result_status for r in latest_results.values())
    dominant_frictions = Counter(
        r.dominant_friction for r in latest_results.values() if r.dominant_friction
    )
    reuse_count = db.scalar(
        select(func.count(ReuseEvent.id))
        .join(Episode, ReuseEvent.destination_episode_id == Episode.id)
        .where(Episode.synthetic.is_(False))
    ) or 0

    return {
        "episodes": len(episodes),
        "organizations": organizations,
        "d2_plus": sum(demand[k] for k in ("D2", "D3", "D4")),
        "demand": dict(demand),
        "preexisting_known": len(known_preexisting),
        "preexisting_yes": preexisting_yes,
        "preexisting_rate": (preexisting_yes / len(known_preexisting)) if known_preexisting else None,
        "public_results": dict(public_results),
        "r5": len(set(r5_resource_ids)),
        "r5_observations": len(r5_resource_ids),
        "result_records": len(result_rows),
        "result_episodes": len(latest_results),
        "result_statuses": dict(result_statuses),
        "dominant_frictions": dict(dominant_frictions),
        "reuse_events": int(reuse_count),
    }


def _json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    return [str(item).strip() for item in data if str(item).strip()] if isinstance(data, list) else []


def _normalized_set(values: list[str]) -> set[str]:
    return {v.strip().upper() for v in values if v and v.strip()}


def _recall(expected: list[str], predicted: list[str]) -> float | None:
    gold = _normalized_set(expected)
    if not gold:
        return None
    pred = _normalized_set(predicted)
    return len(gold & pred) / len(gold)


def _precision(expected: list[str], predicted: list[str]) -> float | None:
    gold = _normalized_set(expected)
    pred = _normalized_set(predicted)
    if not gold:
        return None
    if not pred:
        return 0.0
    return len(gold & pred) / len(pred)


def _f1(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None:
        return None
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def benchmark_prediction_metrics(case: BenchmarkCase, prediction: BenchmarkPrediction) -> dict:
    expected_routes = _json_list(case.expected_routes_json)
    expected_forms = _json_list(case.expected_resource_forms_json)
    expected_resources = _json_list(case.expected_resources_json)
    predicted_routes = _json_list(prediction.routes_json)
    predicted_forms = _json_list(prediction.resource_forms_json)
    predicted_resources = _json_list(prediction.resources_json)
    evidence_urls = _json_list(prediction.evidence_urls_json)
    route_recall = _recall(expected_routes, predicted_routes)
    route_precision = _precision(expected_routes, predicted_routes)
    form_recall = _recall(expected_forms, predicted_forms)
    form_precision = _precision(expected_forms, predicted_forms)
    resource_recall = _recall(expected_resources, predicted_resources)
    resource_precision = _precision(expected_resources, predicted_resources)
    return {
        "route_recall": route_recall,
        "route_precision": route_precision,
        "route_f1": _f1(route_precision, route_recall),
        "resource_form_recall": form_recall,
        "resource_form_precision": form_precision,
        "resource_form_f1": _f1(form_precision, form_recall),
        "resource_recall": resource_recall,
        "resource_precision": resource_precision,
        "resource_f1": _f1(resource_precision, resource_recall),
        "evidence_count": len(evidence_urls),
        "analyst_minutes": prediction.analyst_minutes,
        "verification_minutes": prediction.verification_minutes,
        "human_minutes": prediction.analyst_minutes + prediction.verification_minutes,
        "elapsed_seconds": prediction.elapsed_seconds,
    }


def benchmark_summary(db: Session) -> dict:
    cases = list(db.scalars(select(BenchmarkCase).where(BenchmarkCase.active.is_(True)).order_by(BenchmarkCase.code)).all())
    predictions = list(
        db.scalars(
            select(BenchmarkPrediction)
            .join(BenchmarkCase)
            .where(BenchmarkCase.active.is_(True))
            .order_by(BenchmarkPrediction.submitted_at)
        ).all()
    )
    by_method: dict[tuple[str, str], list[tuple[BenchmarkCase, BenchmarkPrediction]]] = defaultdict(list)
    case_by_id = {c.id: c for c in cases}
    for prediction in predictions:
        case = case_by_id.get(prediction.case_id)
        # Aucun agrégat chiffré n'est publié avant la révélation explicite.
        # Même une moyenne sur un seul cas scellé divulguerait sa référence.
        if case is not None and case.revealed:
            by_method[(prediction.method, prediction.method_version)].append((case, prediction))

    methods = []
    for (method, method_version), rows in sorted(by_method.items()):
        vectors = [benchmark_prediction_metrics(case, prediction) for case, prediction in rows]
        route = [v["route_recall"] for v in vectors if v["route_recall"] is not None]
        route_p = [v["route_precision"] for v in vectors if v["route_precision"] is not None]
        route_f1 = [v["route_f1"] for v in vectors if v["route_f1"] is not None]
        forms = [v["resource_form_recall"] for v in vectors if v["resource_form_recall"] is not None]
        forms_p = [v["resource_form_precision"] for v in vectors if v["resource_form_precision"] is not None]
        forms_f1 = [v["resource_form_f1"] for v in vectors if v["resource_form_f1"] is not None]
        resources = [v["resource_recall"] for v in vectors if v["resource_recall"] is not None]
        resources_p = [v["resource_precision"] for v in vectors if v["resource_precision"] is not None]
        resources_f1 = [v["resource_f1"] for v in vectors if v["resource_f1"] is not None]
        human = [v["human_minutes"] for v in vectors]
        elapsed = [v["elapsed_seconds"] for v in vectors if v["elapsed_seconds"] is not None]
        methods.append({
            "method": method,
            "method_version": method_version,
            "n": len(rows),
            "route_recall_mean": (sum(route) / len(route)) if route else None,
            "route_precision_mean": (sum(route_p) / len(route_p)) if route_p else None,
            "route_f1_mean": (sum(route_f1) / len(route_f1)) if route_f1 else None,
            "resource_form_recall_mean": (sum(forms) / len(forms)) if forms else None,
            "resource_form_precision_mean": (sum(forms_p) / len(forms_p)) if forms_p else None,
            "resource_form_f1_mean": (sum(forms_f1) / len(forms_f1)) if forms_f1 else None,
            "resource_recall_mean": (sum(resources) / len(resources)) if resources else None,
            "resource_precision_mean": (sum(resources_p) / len(resources_p)) if resources_p else None,
            "resource_f1_mean": (sum(resources_f1) / len(resources_f1)) if resources_f1 else None,
            "human_minutes_median": statistics.median(human) if human else None,
            "elapsed_seconds_median": statistics.median(elapsed) if elapsed else None,
            "evidence_count_mean": (sum(v["evidence_count"] for v in vectors) / len(vectors)) if vectors else 0,
        })
    return {
        "cases": cases,
        "predictions": predictions,
        "methods": methods,
        "scored_prediction_count": sum(len(rows) for rows in by_method.values()),
        "sealed_prediction_count": sum(1 for p in predictions if not case_by_id[p.case_id].revealed),
    }
