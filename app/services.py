from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Episode, EpisodeResult, Hypothesis, KnowledgeItem, ReuseEvent, SearchRun

PUBLIC_RESULTS = {"P0", "P1", "P2", "P3"}
HOST_STATES = {"PASS", "FAIL", "UNKNOWN", "NON_APPLICABLE"}


def classify_public_search(*, complete: bool, relevant_found: bool | None, mobilizable_found: bool | None) -> str:
    """Classification conservative de la recherche publique.

    P0: recherche insuffisante pour conclure.
    P1: capacité publique pertinente et mobilisable.
    P2: capacité publique pertinente identifiée, mobilisation non établie/échouée.
    P3: recherche suffisante et aucune capacité publique suffisamment pertinente identifiée.
    """
    if not complete:
        return "P0"
    if relevant_found:
        return "P1" if mobilizable_found else "P2"
    return "P3"


def host_ready(states: Iterable[str]) -> bool:
    states = list(states)
    return bool(states) and all(s == "PASS" for s in states)


def critical_path_minutes(events: list[tuple[datetime, datetime | None, int | None]]) -> int | None:
    """Calcule une durée de chemin critique sur un graphe simple à parent unique.

    Chaque tuple contient (début, fin, index_parent). Les événements ouverts sont ignorés.
    Le calcul utilise la durée propre de l'événement et la meilleure chaîne de dépendance.
    """
    if not events:
        return 0
    durations: list[int] = []
    scores: list[int] = []
    for start, end, parent_idx in events:
        if end is None:
            durations.append(0)
            scores.append(0)
            continue
        duration = max(0, int((end - start).total_seconds() // 60))
        durations.append(duration)
        parent_score = scores[parent_idx] if parent_idx is not None and 0 <= parent_idx < len(scores) else 0
        scores.append(parent_score + duration)
    return max(scores) if scores else 0


def dashboard_metrics(db: Session) -> dict:
    episodes = db.scalars(select(Episode).where(Episode.synthetic.is_(False))).all()
    synthetic = db.scalar(select(func.count(Episode.id)).where(Episode.synthetic.is_(True))) or 0
    demand = Counter(e.demand_level for e in episodes)
    statuses = Counter(e.status for e in episodes)

    public_runs = db.scalars(
        select(SearchRun).join(Episode).where(Episode.synthetic.is_(False), SearchRun.search_type == "PUBLIQUE")
    ).all()
    public_results = Counter(r.public_result for r in public_runs if r.public_result)

    closed_results = db.scalars(select(EpisodeResult).join(Episode).where(Episode.synthetic.is_(False))).all()
    reuse_count = db.scalar(
        select(func.count(ReuseEvent.id)).join(Episode, ReuseEvent.destination_episode_id == Episode.id).where(Episode.synthetic.is_(False))
    ) or 0
    knowledge_count = db.scalar(select(func.count(KnowledgeItem.id))) or 0

    return {
        "episodes": len(episodes),
        "synthetic": synthetic,
        "d2_plus": sum(demand[k] for k in ("D2", "D3", "D4")),
        "demand": dict(demand),
        "statuses": dict(statuses),
        "public_results": dict(public_results),
        "results": len(closed_results),
        "reuse_events": reuse_count,
        "knowledge_items": knowledge_count,
    }


def hypothesis_summary(db: Session) -> list[Hypothesis]:
    return list(db.scalars(select(Hypothesis).order_by(Hypothesis.code)).all())
