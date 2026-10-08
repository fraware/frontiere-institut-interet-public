from __future__ import annotations

from contextlib import asynccontextmanager
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .preregistration_integrity import verifier_preenregistrements
from .config import settings
from .database import Base, engine, get_db
from .models import (
    AuditEvent,
    BenchmarkCase,
    BenchmarkPrediction,
    CapabilityQuery,
    Decision,
    Discovery,
    Evidence,
    Episode,
    EpisodeResult,
    FrictionEvent,
    Hypothesis,
    KnowledgeItem,
    ReuseEvent,
    NeedVersion,
    Organization,
    Resource,
    RouteAssessment,
    SearchRun,
    StakeholderContact,
)
from .services import benchmark_prediction_metrics, benchmark_summary, classify_public_search, dashboard_metrics, empirical_metrics, hypothesis_summary

BASE_DIR = Path(__file__).resolve().parent
@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version="0.5.4", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

MAX_UNAUTHENTICATED_SENSITIVITY = 2
EVIDENCE_QUALITIES = {"A", "B", "C", "D", "E"}
DATA_ENVIRONMENTS = {"RECHERCHE", "RESEAU", "CANDIDATURE", "INTEGRITE"}
RESOURCE_STATES = ["R0", "R1", "R2", "R3", "R4", "R5"]
ADDITIONALITY_LEVELS = {"FORTE", "MODEREE", "FAIBLE", "NULLE", "INDETERMINE"}


def _active_need(ep: Episode) -> NeedVersion | None:
    return next((n for n in sorted(ep.needs, key=lambda n: n.version, reverse=True) if n.active), None)


def _require_locked_need(db: Session, ep: Episode) -> NeedVersion:
    need = db.scalar(
        select(NeedVersion)
        .where(NeedVersion.episode_id == ep.id, NeedVersion.active.is_(True))
        .order_by(NeedVersion.version.desc())
        .limit(1)
    )
    if need is None or need.locked_at is None:
        raise HTTPException(409, "Le besoin et la situation sans FRONTIÈRE doivent être verrouillés avant cette étape.")
    return need


def _audit(
    db: Session,
    *,
    event_type: str,
    entity_type: str,
    entity_id: int | None = None,
    episode_id: int | None = None,
    payload: dict | None = None,
    actor: str = "équipe Frontière",
) -> None:
    db.add(
        AuditEvent(
            episode_id=episode_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            actor=actor,
            payload_json=json.dumps(payload or {}, ensure_ascii=False, sort_keys=True),
        )
    )


def _audit_event(db: Session, episode_id: int, event_type: str) -> AuditEvent | None:
    return db.scalar(
        select(AuditEvent)
        .where(AuditEvent.episode_id == episode_id, AuditEvent.event_type == event_type)
        .order_by(AuditEvent.id.desc())
        .limit(1)
    )


def _audit_payload(event: AuditEvent | None) -> dict:
    if event is None or not event.payload_json:
        return {}
    try:
        valeur = json.loads(event.payload_json)
    except json.JSONDecodeError:
        return {}
    return valeur if isinstance(valeur, dict) else {}


def _empreinte(objet: dict) -> str:
    brut = json.dumps(
        objet,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(brut).hexdigest()


def _prospective_event(db: Session, ep: Episode) -> AuditEvent | None:
    return _audit_event(db, ep.id, "CAS_PROSPECTIF_PRE_ENREGISTRE")


def _comparison_event(db: Session, ep: Episode) -> AuditEvent | None:
    return _audit_event(db, ep.id, "COMPARAISON_APPARIEE_PRE_ENREGISTREE")


def _require_comparison_plan_if_prospective(db: Session, ep: Episode) -> None:
    if _prospective_event(db, ep) is not None and _comparison_event(db, ep) is None:
        raise HTTPException(
            409,
            "L’état initial de ce cas est déjà enregistré. Enregistrez les règles de comparaison des deux méthodes avant toute intervention de FRONTIÈRE.",
        )


def _interventions_existantes(db: Session, ep: Episode) -> list[str]:
    """Repère toute action déjà entreprise susceptible de fausser l'antériorité."""
    controles = [
        ("recherche", SearchRun, SearchRun.episode_id),
        ("requête de capacité", CapabilityQuery, CapabilityQuery.episode_id),
        ("voie évaluée", RouteAssessment, RouteAssessment.episode_id),
        ("décision", Decision, Decision.episode_id),
        ("obstacle enregistré", FrictionEvent, FrictionEvent.episode_id),
        ("résultat", EpisodeResult, EpisodeResult.episode_id),
        ("connaissance créée", KnowledgeItem, KnowledgeItem.source_episode_id),
        ("connaissance réutilisée", ReuseEvent, ReuseEvent.destination_episode_id),
    ]
    return [
        libelle
        for libelle, modele, colonne in controles
        if db.scalar(select(modele.id).where(colonne == ep.id).limit(1)) is not None
    ]


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "frontiere-institut-interet-public", "version": "0.5.4"}


@app.get("/api/v1/metrics")
def api_metrics(db: Session = Depends(get_db)) -> dict:
    return dashboard_metrics(db)


@app.get("/api/v1/episodes")
def api_episodes(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Episode).options(selectinload(Episode.organization)).where(Episode.synthetic.is_(False)).order_by(Episode.created_at.desc())).all()
    return [
        {
            "code": e.code,
            "title": e.title,
            "organization": e.organization.name,
            "status": e.status,
            "demand_level": e.demand_level,
            "sensitivity_level": e.sensitivity_level,
        }
        for e in rows
    ]


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    episodes = db.scalars(
        select(Episode)
        .options(selectinload(Episode.organization))
        .where(Episode.synthetic.is_(False))
        .order_by(Episode.updated_at.desc())
        .limit(12)
    ).all()
    metrics = dashboard_metrics(db)
    hypotheses = hypothesis_summary(db)
    return templates.TemplateResponse(
        request=request,
        name="tableau_bord.html",
        context={"episodes": episodes, "metrics": metrics, "hypotheses": hypotheses[:5]},
    )


@app.get("/donnees-terrain", response_class=HTMLResponse)
def empirical_dashboard(request: Request, db: Session = Depends(get_db)):
    metrics = empirical_metrics(db)
    return templates.TemplateResponse(
        request=request,
        name="donnees_terrain.html",
        context={"metrics": metrics},
    )


@app.get("/episodes/new", response_class=HTMLResponse)
def new_episode(request: Request):
    return templates.TemplateResponse(request=request, name="nouveau_cas.html", context={})


@app.post("/episodes")
def create_episode(
    organization_name: str = Form(...),
    organizational_unit: str = Form(""),
    title: str = Form(...),
    current_situation: str = Form(...),
    desired_outcome: str = Form(...),
    demand_level: str = Form("D0"),
    sensitivity_level: int = Form(1),
    need_preexisting_frontiere: str = Form("unknown"),
    sponsor: str = Form(""),
    latest_useful_date: str = Form(""),
    counterfactual_plan: str = Form(""),
    initial_frontiere_hypothesis: str = Form(""),
    db: Session = Depends(get_db),
):
    if demand_level not in {"D0", "D1", "D2", "D3", "D4"}:
        raise HTTPException(400, "Niveau de demande invalide")
    if sensitivity_level < 1 or sensitivity_level > MAX_UNAUTHENTICATED_SENSITIVITY:
        raise HTTPException(400, "Le prototype public v0.2 accepte uniquement les niveaux de sensibilité 1 et 2. Les niveaux 3–4 exigent authentification et contrôle d'accès.")
    org = db.scalar(select(Organization).where(Organization.name == organization_name.strip()))
    if org is None:
        org = Organization(name=organization_name.strip())
        db.add(org)
        db.flush()

    next_id = (db.scalar(select(Episode.id).order_by(Episode.id.desc()).limit(1)) or 0) + 1
    code = f"EP-{date.today().year}-{next_id:04d}"
    preexisting = None if need_preexisting_frontiere == "unknown" else need_preexisting_frontiere == "yes"
    deadline = date.fromisoformat(latest_useful_date) if latest_useful_date else None

    ep = Episode(
        code=code,
        organization_id=org.id,
        organizational_unit=organizational_unit.strip() or None,
        title=title.strip(),
        demand_level=demand_level,
        sensitivity_level=sensitivity_level,
        need_preexisting_frontiere=preexisting,
        status="QUALIFICATION",
    )
    db.add(ep)
    db.flush()
    need = NeedVersion(
        episode_id=ep.id,
        current_situation=current_situation.strip(),
        desired_outcome=desired_outcome.strip(),
        latest_useful_date=deadline,
        sponsor=sponsor.strip() or None,
        counterfactual_plan=counterfactual_plan.strip() or None,
        initial_frontiere_hypothesis=initial_frontiere_hypothesis.strip() or None,
    )
    db.add(need)
    db.flush()
    _audit(
        db,
        event_type="EPISODE_CREE",
        entity_type="EPISODE",
        entity_id=ep.id,
        episode_id=ep.id,
        payload={"need_version_id": need.id, "demand_level": ep.demand_level, "sensitivity_level": ep.sensitivity_level},
    )
    db.commit()
    return RedirectResponse(url=f"/episodes/{ep.code}", status_code=303)


@app.get("/episodes/{code}", response_class=HTMLResponse)
def episode_detail(code: str, request: Request, db: Session = Depends(get_db)):
    ep = db.scalar(
        select(Episode)
        .options(
            selectinload(Episode.organization),
            selectinload(Episode.needs).selectinload(NeedVersion.capability_requirements),
            selectinload(Episode.searches).selectinload(SearchRun.discoveries).selectinload(Discovery.resource),
            selectinload(Episode.route_assessments),
            selectinload(Episode.decisions),
            selectinload(Episode.friction_events),
            selectinload(Episode.results),
            selectinload(Episode.knowledge_items),
            selectinload(Episode.evidence_items),
            selectinload(Episode.audit_events),
        )
        .where(Episode.code == code)
    )
    if ep is None:
        raise HTTPException(404, "Épisode introuvable")
    active_need = _active_need(ep)
    prospective_event = _prospective_event(db, ep)
    comparison_event = _comparison_event(db, ep)
    prospective_payload = _audit_payload(prospective_event)
    comparison_payload = _audit_payload(comparison_event)
    prospective_fingerprint = prospective_payload.get("baseline_sha256")
    capability_query = db.scalar(
        select(CapabilityQuery)
        .where(CapabilityQuery.episode_id == ep.id, CapabilityQuery.active.is_(True))
        .order_by(CapabilityQuery.version.desc())
        .limit(1)
    )
    reusable_knowledge = list(db.scalars(
        select(KnowledgeItem)
        .where(KnowledgeItem.status == "ACTIVE", KnowledgeItem.source_episode_id != ep.id)
        .order_by(KnowledgeItem.created_at.desc())
        .limit(100)
    ).all())
    reuse_events = list(db.scalars(
        select(ReuseEvent)
        .options(selectinload(ReuseEvent.knowledge))
        .where(ReuseEvent.destination_episode_id == ep.id)
        .order_by(ReuseEvent.reused_at.desc())
    ).all())
    return templates.TemplateResponse(
        request=request,
        name="detail_cas.html",
        context={
            "episode": ep,
            "need": active_need,
            "need_locked": bool(active_need and active_need.locked_at),
            "prospective_payload": prospective_payload,
            "prospective_fingerprint": prospective_fingerprint,
            "comparison_payload": comparison_payload,
            "capability_query": capability_query,
            "reusable_knowledge": reusable_knowledge,
            "reuse_events": reuse_events,
        },
    )


@app.post("/episodes/{code}/capability-query")
def create_capability_query(
    code: str,
    raw_request: str = Form(...),
    domain: str = Form(...),
    function: str = Form(...),
    depth: str = Form("intermediaire"),
    operational_context: str = Form(""),
    constraints: str = Form(""),
    resource_forms: str = Form(""),
    must_have: str = Form(""),
    nice_to_have: str = Form(""),
    latest_useful_date: str = Form(""),
    compiler: str = Form("human"),
    db: Session = Depends(get_db),
):
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404, "Épisode introuvable")
    need = _require_locked_need(db, ep)
    _require_comparison_plan_if_prospective(db, ep)

    current = db.scalar(
        select(CapabilityQuery)
        .where(CapabilityQuery.need_id == need.id, CapabilityQuery.active.is_(True))
        .order_by(CapabilityQuery.version.desc())
        .limit(1)
    )
    version = 1
    if current is not None:
        current.active = False
        version = current.version + 1

    def items(text: str) -> list[str]:
        return [part.strip() for part in text.replace("\n", ",").split(",") if part.strip()]

    deadline = date.fromisoformat(latest_useful_date) if latest_useful_date else need.latest_useful_date
    query = CapabilityQuery(
        episode_id=ep.id,
        need_id=need.id,
        version=version,
        active=True,
        raw_request=raw_request.strip(),
        domain=domain.strip(),
        function=function.strip(),
        depth=depth.strip(),
        operational_context=operational_context.strip() or None,
        constraints=constraints.strip() or None,
        resource_forms_json=json.dumps(items(resource_forms), ensure_ascii=False),
        must_have_json=json.dumps(items(must_have), ensure_ascii=False),
        nice_to_have_json=json.dumps(items(nice_to_have), ensure_ascii=False),
        latest_useful_date=deadline,
        compiler=compiler.strip() or "human",
        compiler_version="1.0",
        locked_at=datetime.now(timezone.utc),
    )
    db.add(query)
    db.flush()
    _audit(
        db,
        event_type="CAPABILITY_QUERY_COMPILÉE",
        entity_type="CAPABILITY_QUERY",
        entity_id=query.id,
        episode_id=ep.id,
        payload={
            "need_version_id": need.id,
            "query_version": query.version,
            "domain": query.domain,
            "function": query.function,
            "depth": query.depth,
            "resource_forms": json.loads(query.resource_forms_json),
        },
    )
    db.commit()
    return RedirectResponse(url=f"/episodes/{code}#capability-query", status_code=303)


@app.get("/api/v1/episodes/{code}/capability-query")
def api_capability_query(code: str, db: Session = Depends(get_db)) -> dict:
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404, "Épisode introuvable")
    query = db.scalar(
        select(CapabilityQuery)
        .where(CapabilityQuery.episode_id == ep.id, CapabilityQuery.active.is_(True))
        .order_by(CapabilityQuery.version.desc())
        .limit(1)
    )
    if query is None:
        raise HTTPException(404, "Aucune requête de capacité active")
    return {
        "episode": ep.code,
        "version": query.version,
        "raw_request": query.raw_request,
        "domain": query.domain,
        "function": query.function,
        "depth": query.depth,
        "operational_context": query.operational_context,
        "constraints": query.constraints,
        "resource_forms": json.loads(query.resource_forms_json),
        "must_have": json.loads(query.must_have_json),
        "nice_to_have": json.loads(query.nice_to_have_json),
        "latest_useful_date": query.latest_useful_date.isoformat() if query.latest_useful_date else None,
        "compiler": query.compiler,
        "locked_at": query.locked_at.isoformat() if query.locked_at else None,
    }


@app.post("/episodes/{code}/public-search")
def add_public_search(
    code: str,
    complete: str = Form("no"),
    relevant_found: str = Form("unknown"),
    mobilizable_found: str = Form("unknown"),
    analyst_minutes: int = Form(0),
    method_name: str = Form("recherche structurée"),
    search_scope: str = Form(""),
    sources_consulted: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404)
    _require_locked_need(db, ep)
    _require_comparison_plan_if_prospective(db, ep)
    complete_b = complete == "yes"
    rel = None if relevant_found == "unknown" else relevant_found == "yes"
    mob = None if mobilizable_found == "unknown" else mobilizable_found == "yes"
    result = classify_public_search(complete=complete_b, relevant_found=rel, mobilizable_found=mob)
    run = SearchRun(
        episode_id=ep.id,
        search_type="PUBLIQUE",
        method_name=method_name.strip() or "recherche structurée",
        complete_enough_to_conclude=complete_b,
        public_relevant_found=rel,
        public_mobilizable_found=mob,
        public_result=result,
        analyst_minutes=max(0, analyst_minutes),
        notes=notes.strip() or None,
    )
    db.add(run)
    db.flush()
    ep.status = "INVESTIGATION"
    locked_need = _require_locked_need(db, ep)
    _audit(
        db,
        event_type="RECHERCHE_PUBLIQUE_ENREGISTREE",
        entity_type="SEARCH_RUN",
        entity_id=run.id,
        episode_id=ep.id,
        payload={
            "need_version_id": locked_need.id,
            "public_result": result,
            "complete": complete_b,
            "analyst_minutes": max(0, analyst_minutes),
            "method_name": run.method_name,
            "search_scope": search_scope.strip() or None,
            "sources_consulted": [
                ligne.strip()
                for ligne in sources_consulted.replace(",", "\n").splitlines()
                if ligne.strip()
            ],
        },
    )
    db.commit()
    return RedirectResponse(url=f"/episodes/{code}#recherche", status_code=303)


@app.post("/episodes/{code}/decision")
def add_decision(
    code: str,
    selected_option: str = Form(...),
    justification: str = Form(...),
    contradictory_evidence: str = Form(""),
    uncertainties: str = Form(""),
    confidence: str = Form("moyenne"),
    db: Session = Depends(get_db),
):
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404)
    _require_locked_need(db, ep)
    _require_comparison_plan_if_prospective(db, ep)
    d = Decision(
        episode_id=ep.id,
        selected_option=selected_option.strip(),
        justification=justification.strip(),
        contradictory_evidence=contradictory_evidence.strip() or None,
        uncertainties=uncertainties.strip() or None,
        confidence=confidence,
    )
    db.add(d)
    db.flush()
    ep.status = "ORIENTE"
    locked_need = _require_locked_need(db, ep)
    _audit(
        db,
        event_type="DECISION_VERROUILLEE",
        entity_type="DECISION",
        entity_id=d.id,
        episode_id=ep.id,
        payload={"need_version_id": locked_need.id, "selected_option": d.selected_option, "confidence": d.confidence},
    )
    db.commit()
    return RedirectResponse(url=f"/episodes/{code}#decision", status_code=303)


@app.post("/episodes/{code}/resource")
def add_resource(
    code: str,
    search_type: str = Form("PUBLIQUE"),
    resource_type: str = Form(...),
    display_name: str = Form(...),
    source_channel: str = Form(""),
    state: str = Form("R0"),
    state_reason: str = Form(""),
    mission_specific_interest: str = Form("unknown"),
    available_as_of: str = Form(""),
    db: Session = Depends(get_db),
):
    if state not in RESOURCE_STATES:
        raise HTTPException(400, "État de ressource invalide")
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404)
    locked_need = _require_locked_need(db, ep)
    _require_comparison_plan_if_prospective(db, ep)
    resource = db.scalar(select(Resource).where(Resource.display_name == display_name.strip(), Resource.resource_type == resource_type))
    if resource is None:
        resource = Resource(resource_type=resource_type, display_name=display_name.strip())
        db.add(resource)
        db.flush()
    run = db.scalar(
        select(SearchRun)
        .where(SearchRun.episode_id == ep.id, SearchRun.search_type == search_type)
        .order_by(SearchRun.id.desc())
        .limit(1)
    )
    if run is None:
        run = SearchRun(episode_id=ep.id, search_type=search_type, method_name="saisie opérateur")
        db.add(run)
        db.flush()

    existing = db.scalar(select(Discovery).where(Discovery.search_run_id == run.id, Discovery.resource_id == resource.id))
    reason = state_reason.strip() or None
    interest = None if mission_specific_interest == "unknown" else mission_specific_interest == "yes"
    availability_date = date.fromisoformat(available_as_of) if available_as_of else None

    if existing is None:
        if state != "R0":
            raise HTTPException(409, "Une nouvelle ressource entre en R0. Les progressions R1–R5 sont enregistrées séquentiellement.")
        existing = Discovery(
            search_run_id=run.id,
            resource_id=resource.id,
            source_channel=source_channel.strip() or "non précisé",
            state="R0",
            state_reason=reason,
            mission_specific_interest=interest,
            available_as_of=availability_date,
        )
        db.add(existing)
    else:
        current_index = RESOURCE_STATES.index(existing.state)
        new_index = RESOURCE_STATES.index(state)
        if new_index > current_index + 1:
            raise HTTPException(409, f"Transition {existing.state} → {state} interdite : avancer un état à la fois.")
        if new_index >= 2 and not reason:
            raise HTTPException(409, "R2–R5 exigent une justification vérifiable.")
        if state == "R5" and (interest is not True or availability_date is None):
            raise HTTPException(409, "R5 exige un intérêt explicite pour la mission et une date de disponibilité confirmée.")
        existing.state = state
        existing.state_reason = reason or existing.state_reason
        existing.source_channel = source_channel.strip() or existing.source_channel
        if interest is not None:
            existing.mission_specific_interest = interest
        if availability_date is not None:
            existing.available_as_of = availability_date

    db.flush()
    _audit(
        db,
        event_type="RESSOURCE_ETAT_ENREGISTRE",
        entity_type="DISCOVERY",
        entity_id=existing.id,
        episode_id=ep.id,
        payload={
            "need_version_id": locked_need.id,
            "resource_id": resource.id,
            "search_type": search_type,
            "state": existing.state,
            "state_reason": existing.state_reason,
            "mission_specific_interest": existing.mission_specific_interest,
            "available_as_of": existing.available_as_of.isoformat() if existing.available_as_of else None,
            "source_channel": existing.source_channel,
        },
    )
    db.commit()
    return RedirectResponse(url=f"/episodes/{code}#ressources", status_code=303)


@app.post("/episodes/{code}/route")
def add_route(
    code: str,
    route_code: str = Form(...),
    route_label: str = Form(...),
    status_current: str = Form("INFORMATION_INSUFFISANTE"),
    evidence_for: str = Form(""),
    evidence_against: str = Form(""),
    blocking_condition: str = Form(""),
    next_action: str = Form(""),
    db: Session = Depends(get_db),
):
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404)
    locked_need = _require_locked_need(db, ep)
    _require_comparison_plan_if_prospective(db, ep)
    route = db.scalar(select(RouteAssessment).where(RouteAssessment.episode_id == ep.id, RouteAssessment.route_code == route_code.strip()))
    if route is None:
        route = RouteAssessment(episode_id=ep.id, route_code=route_code.strip(), route_label=route_label.strip(), status_initial=status_current, status_current=status_current)
        db.add(route)
    else:
        route.route_label = route_label.strip()
        route.status_current = status_current
    route.evidence_for = evidence_for.strip() or None
    route.evidence_against = evidence_against.strip() or None
    route.blocking_condition = blocking_condition.strip() or None
    route.next_action = next_action.strip() or None
    db.flush()
    _audit(
        db,
        event_type="VOIE_EVALUEE",
        entity_type="ROUTE_ASSESSMENT",
        entity_id=route.id,
        episode_id=ep.id,
        payload={"need_version_id": locked_need.id, "route_code": route.route_code, "status": route.status_current},
    )
    db.commit()
    return RedirectResponse(url=f"/episodes/{code}#voies", status_code=303)


@app.post("/episodes/{code}/friction")
def add_friction(
    code: str,
    category: str = Form(...),
    subcategory: str = Form(""),
    started_at: str = Form(...),
    ended_at: str = Form(""),
    owner: str = Form(""),
    blocking: str = Form("no"),
    reason: str = Form(""),
    db: Session = Depends(get_db),
):
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404)
    locked_need = _require_locked_need(db, ep)
    _require_comparison_plan_if_prospective(db, ep)
    start = datetime.fromisoformat(started_at)
    end = datetime.fromisoformat(ended_at) if ended_at else None
    friction = FrictionEvent(episode_id=ep.id, category=category, subcategory=subcategory.strip() or None, started_at=start, ended_at=end, owner=owner.strip() or None, blocking=blocking == "yes", reason=reason.strip() or None)
    db.add(friction)
    db.flush()
    _audit(
        db,
        event_type="FRICTION_ENREGISTREE",
        entity_type="FRICTION_EVENT",
        entity_id=friction.id,
        episode_id=ep.id,
        payload={"need_version_id": locked_need.id, "category": category, "blocking": blocking == "yes"},
    )
    db.commit()
    return RedirectResponse(url=f"/episodes/{code}#frictions", status_code=303)


@app.post("/episodes/{code}/result")
def add_result(
    code: str,
    result_status: str = Form(...),
    actual_intervention: str = Form(""),
    actual_route: str = Form(""),
    outcome_description: str = Form(...),
    dominant_friction: str = Form(""),
    first_useful_contribution_at: str = Form(""),
    direct_cost_eur: float | None = Form(None),
    frontiere_minutes: int = Form(0),
    institution_minutes: int = Form(0),
    additionality_outcome: str = Form("INDETERMINE"),
    additionality_time: str = Form("INDETERMINE"),
    additionality_quality: str = Form("INDETERMINE"),
    additionality_cost: str = Form("INDETERMINE"),
    additionality_learning: str = Form("INDETERMINE"),
    db: Session = Depends(get_db),
):
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404)
    locked_need = _require_locked_need(db, ep)
    _require_comparison_plan_if_prospective(db, ep)
    levels = {
        additionality_outcome,
        additionality_time,
        additionality_quality,
        additionality_cost,
        additionality_learning,
    }
    if not levels.issubset(ADDITIONALITY_LEVELS):
        raise HTTPException(400, "Niveau d'effet propre invalide.")
    first_value = datetime.fromisoformat(first_useful_contribution_at) if first_useful_contribution_at else None
    result = EpisodeResult(
        episode_id=ep.id,
        result_status=result_status,
        actual_intervention=actual_intervention.strip() or None,
        actual_route=actual_route.strip() or None,
        outcome_description=outcome_description.strip(),
        dominant_friction=dominant_friction.strip() or None,
        first_useful_contribution_at=first_value,
        direct_cost_eur=max(0, direct_cost_eur) if direct_cost_eur is not None else None,
        frontiere_minutes=max(0, frontiere_minutes),
        institution_minutes=max(0, institution_minutes),
        additionality_outcome=additionality_outcome,
        additionality_time=additionality_time,
        additionality_quality=additionality_quality,
        additionality_cost=additionality_cost,
        additionality_learning=additionality_learning,
    )
    db.add(result)
    db.flush()
    ep.status = "RESULTAT_ENREGISTRE"
    _audit(
        db,
        event_type="RESULTAT_ENREGISTRE",
        entity_type="EPISODE_RESULT",
        entity_id=result.id,
        episode_id=ep.id,
        payload={
            "need_version_id": locked_need.id,
            "result_status": result_status,
            "dominant_friction": dominant_friction.strip() or None,
            "first_useful_contribution_at": first_value.isoformat() if first_value else None,
            "direct_cost_eur": result.direct_cost_eur,
            "additionality": {
                "outcome": additionality_outcome,
                "time": additionality_time,
                "quality": additionality_quality,
                "cost": additionality_cost,
                "learning": additionality_learning,
            },
        },
    )
    db.commit()
    return RedirectResponse(url=f"/episodes/{code}#resultat", status_code=303)


@app.post("/episodes/{code}/knowledge")
def add_knowledge(
    code: str,
    knowledge_type: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    scope: str = Form(""),
    evidence_level: str = Form("C"),
    db: Session = Depends(get_db),
):
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404)
    locked_need = _require_locked_need(db, ep)
    _require_comparison_plan_if_prospective(db, ep)
    item = KnowledgeItem(source_episode_id=ep.id, knowledge_type=knowledge_type, title=title.strip(), content=content.strip(), scope=scope.strip() or None, evidence_level=evidence_level)
    db.add(item)
    db.flush()
    _audit(
        db,
        event_type="CONNAISSANCE_CREEE",
        entity_type="KNOWLEDGE_ITEM",
        entity_id=item.id,
        episode_id=ep.id,
        payload={"need_version_id": locked_need.id, "knowledge_type": knowledge_type, "evidence_level": evidence_level},
    )
    db.commit()
    return RedirectResponse(url=f"/episodes/{code}#connaissance", status_code=303)


@app.post("/episodes/{code}/reuse")
def add_reuse(
    code: str,
    knowledge_id: int = Form(...),
    decision_changed: str = Form("no"),
    estimated_minutes_saved: int | None = Form(None),
    accessible_to_new_analyst: str = Form("yes"),
    effect_description: str = Form(""),
    db: Session = Depends(get_db),
):
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404, "Épisode introuvable")
    locked_need = _require_locked_need(db, ep)
    _require_comparison_plan_if_prospective(db, ep)
    knowledge = db.scalar(select(KnowledgeItem).where(KnowledgeItem.id == knowledge_id, KnowledgeItem.status == "ACTIVE"))
    if knowledge is None:
        raise HTTPException(404, "Connaissance introuvable")
    if knowledge.source_episode_id == ep.id:
        raise HTTPException(409, "Une connaissance ne peut pas être comptée comme réutilisée dans son épisode source.")
    reuse = ReuseEvent(
        knowledge_id=knowledge.id,
        destination_episode_id=ep.id,
        decision_changed=decision_changed == "yes",
        estimated_minutes_saved=max(0, estimated_minutes_saved) if estimated_minutes_saved is not None else None,
        accessible_to_new_analyst=accessible_to_new_analyst == "yes",
        effect_description=effect_description.strip() or None,
    )
    db.add(reuse)
    db.flush()
    _audit(
        db,
        event_type="CONNAISSANCE_REUTILISEE",
        entity_type="REUSE_EVENT",
        entity_id=reuse.id,
        episode_id=ep.id,
        payload={
            "need_version_id": locked_need.id,
            "knowledge_id": knowledge.id,
            "source_episode_id": knowledge.source_episode_id,
            "decision_changed": reuse.decision_changed,
            "estimated_minutes_saved": reuse.estimated_minutes_saved,
            "accessible_to_new_analyst": reuse.accessible_to_new_analyst,
        },
    )
    db.commit()
    return RedirectResponse(url=f"/episodes/{code}#reutilisation", status_code=303)


@app.post("/episodes/{code}/need/update-initial")
def update_initial_need(
    code: str,
    current_situation: str = Form(...),
    desired_outcome: str = Form(...),
    sponsor: str = Form(""),
    latest_useful_date: str = Form(""),
    need_preexisting_frontiere: str = Form("unknown"),
    counterfactual_plan: str = Form(""),
    initial_frontiere_hypothesis: str = Form(""),
    db: Session = Depends(get_db),
):
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404, "Épisode introuvable")
    need = db.scalar(
        select(NeedVersion)
        .where(NeedVersion.episode_id == ep.id, NeedVersion.active.is_(True))
        .order_by(NeedVersion.version.desc())
        .limit(1)
    )
    if need is None:
        raise HTTPException(409, "Aucune version active du besoin")
    if need.locked_at is not None:
        raise HTTPException(409, "L’état initial est déjà verrouillé. Utiliser une révision versionnée.")
    if need_preexisting_frontiere not in {"yes", "no", "unknown"}:
        raise HTTPException(400, "Qualification de préexistence invalide.")
    deadline = date.fromisoformat(latest_useful_date) if latest_useful_date else None
    need.current_situation = current_situation.strip()
    need.desired_outcome = desired_outcome.strip()
    need.sponsor = sponsor.strip() or None
    need.latest_useful_date = deadline
    need.counterfactual_plan = counterfactual_plan.strip() or None
    need.initial_frontiere_hypothesis = initial_frontiere_hypothesis.strip() or None
    ep.need_preexisting_frontiere = (
        None if need_preexisting_frontiere == "unknown" else need_preexisting_frontiere == "yes"
    )
    _audit(
        db,
        event_type="ETAT_INITIAL_MIS_A_JOUR",
        entity_type="NEED_VERSION",
        entity_id=need.id,
        episode_id=ep.id,
        payload={
            "version": need.version,
            "preexistence_qualifiee": ep.need_preexisting_frontiere is not None,
            "responsable_present": bool(need.sponsor),
            "echeance_presente": bool(need.latest_useful_date),
        },
    )
    db.commit()
    return RedirectResponse(url=f"/episodes/{code}#prospectif", status_code=303)


@app.post("/episodes/{code}/prospective/lock")
def lock_prospective_baseline(code: str, db: Session = Depends(get_db)):
    ep = db.scalar(
        select(Episode)
        .options(selectinload(Episode.organization))
        .where(Episode.code == code)
    )
    if ep is None:
        raise HTTPException(404, "Épisode introuvable")
    if ep.synthetic or ep.nature != "actuel":
        raise HTTPException(409, "L’enregistrement de l’état initial exige un cas réel et actuel.")
    if _prospective_event(db, ep) is not None:
        raise HTTPException(409, "L’état initial de ce cas a déjà été enregistré et figé.")
    interventions = _interventions_existantes(db, ep)
    if interventions:
        raise HTTPException(
            409,
            "L’état initial ne peut être préenregistré après une intervention : " + ", ".join(interventions),
        )

    need = db.scalar(
        select(NeedVersion)
        .where(NeedVersion.episode_id == ep.id, NeedVersion.active.is_(True))
        .order_by(NeedVersion.version.desc())
        .limit(1)
    )
    if need is None:
        raise HTTPException(409, "Aucune version active du besoin")

    preuves = list(
        db.scalars(
            select(Evidence)
            .where(Evidence.episode_id == ep.id)
            .order_by(Evidence.id)
        ).all()
    )
    manquants: list[str] = []
    if not need.current_situation.strip():
        manquants.append("situation")
    if not need.desired_outcome.strip():
        manquants.append("résultat recherché")
    if not need.sponsor:
        manquants.append("responsable opérationnel")
    if ep.need_preexisting_frontiere is None:
        manquants.append("préexistence du besoin")
    if not need.latest_useful_date:
        manquants.append("échéance utile")
    if not need.counterfactual_plan:
        manquants.append("situation sans FRONTIÈRE")
    if not need.initial_frontiere_hypothesis:
        manquants.append("hypothèse initiale")
    if not preuves:
        manquants.append("au moins une preuve initiale")
    if manquants:
        raise HTTPException(
            409,
            "Impossible de figer l’état initial : " + ", ".join(manquants),
        )

    if need.locked_at is None:
        need.locked_at = datetime.now(timezone.utc)

    baseline = {
        "schema_version": "prospectif-v1",
        "episode": {
            "code": ep.code,
            "organization": ep.organization.name,
            "organizational_unit": ep.organizational_unit,
            "title": ep.title,
            "nature": ep.nature,
            "detected_at": ep.detected_at.isoformat(),
            "need_preexisting_frontiere": ep.need_preexisting_frontiere,
            "demand_level": ep.demand_level,
        },
        "need": {
            "version": need.version,
            "current_situation": need.current_situation,
            "desired_outcome": need.desired_outcome,
            "sponsor": need.sponsor,
            "latest_useful_date": need.latest_useful_date.isoformat(),
            "counterfactual_plan": need.counterfactual_plan,
            "initial_frontiere_hypothesis": need.initial_frontiere_hypothesis,
            "locked_at": need.locked_at.isoformat(),
        },
        "evidence": [
            {
                "id": preuve.id,
                "title": preuve.title,
                "evidence_type": preuve.evidence_type,
                "source": preuve.source,
                "evidence_date": preuve.evidence_date.isoformat() if preuve.evidence_date else None,
                "quality": preuve.quality,
                "data_environment": preuve.data_environment,
            }
            for preuve in preuves
        ],
    }
    baseline_sha256 = _empreinte(baseline)
    ep.status = "PRE_ENREGISTRE"
    _audit(
        db,
        event_type="CAS_PROSPECTIF_PRE_ENREGISTRE",
        entity_type="EPISODE",
        entity_id=ep.id,
        episode_id=ep.id,
        payload={
            "schema_version": "prospectif-v1",
            "baseline_sha256": baseline_sha256,
            "baseline": baseline,
        },
    )
    db.commit()
    return RedirectResponse(url=f"/episodes/{code}#prospectif", status_code=303)


@app.post("/episodes/{code}/comparison/lock")
def lock_paired_comparison(
    code: str,
    usual_method: str = Form(...),
    frontiere_method: str = Form("FRONTIÈRE"),
    usual_owner: str = Form(...),
    frontiere_owner: str = Form(...),
    primary_outcome: str = Form(...),
    observation_date: str = Form(...),
    interference_policy: str = Form(...),
    usual_budget_minutes: int = Form(0),
    frontiere_budget_minutes: int = Form(0),
    db: Session = Depends(get_db),
):
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404, "Épisode introuvable")
    baseline_event = _prospective_event(db, ep)
    if baseline_event is None:
        raise HTTPException(409, "Enregistrez et figez d’abord l’état initial.")
    if _comparison_event(db, ep) is not None:
        raise HTTPException(409, "Les règles de comparaison des deux méthodes sont déjà enregistrées.")
    interventions = _interventions_existantes(db, ep)
    if interventions:
        raise HTTPException(
            409,
            "Les règles de comparaison ne peuvent être enregistrées après une intervention : " + ", ".join(interventions),
        )

    methode_habituelle = usual_method.strip()
    methode_frontiere = frontiere_method.strip()
    proprietaire_habituel = usual_owner.strip()
    proprietaire_frontiere = frontiere_owner.strip()
    mesure = primary_outcome.strip()
    regle_interference = interference_policy.strip()
    if not all([methode_habituelle, methode_frontiere, proprietaire_habituel, proprietaire_frontiere, mesure, regle_interference]):
        raise HTTPException(400, "Tous les champs du plan de comparaison sont obligatoires.")
    if methode_habituelle.casefold() == methode_frontiere.casefold():
        raise HTTPException(400, "Les deux méthodes comparées doivent être différentes.")

    date_observation = date.fromisoformat(observation_date)
    if date_observation < date.today():
        raise HTTPException(400, "La date d’observation doit être aujourd’hui ou dans le futur.")

    baseline_payload = _audit_payload(baseline_event)
    plan = {
        "schema_version": "comparaison-appariee-v1",
        "need_version_id": _require_locked_need(db, ep).id,
        "baseline_sha256": baseline_payload.get("baseline_sha256"),
        "usual_method": methode_habituelle,
        "frontiere_method": methode_frontiere,
        "usual_owner": proprietaire_habituel,
        "frontiere_owner": proprietaire_frontiere,
        "primary_outcome": mesure,
        "observation_date": date_observation.isoformat(),
        "interference_policy": regle_interference,
        "usual_budget_minutes": max(0, usual_budget_minutes),
        "frontiere_budget_minutes": max(0, frontiere_budget_minutes),
        "registered_before_search": True,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    plan_sha256 = _empreinte(plan)
    ep.status = "COMPARAISON_PRE_ENREGISTREE"
    _audit(
        db,
        event_type="COMPARAISON_APPARIEE_PRE_ENREGISTREE",
        entity_type="EPISODE",
        entity_id=ep.id,
        episode_id=ep.id,
        payload={
            **plan,
            "plan_sha256": plan_sha256,
        },
    )
    db.commit()
    return RedirectResponse(url=f"/episodes/{code}#prospectif", status_code=303)


@app.get("/api/v1/episodes/{code}/preregistration")
def api_preregistration(code: str, db: Session = Depends(get_db)) -> dict:
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404, "Épisode introuvable")
    baseline_event = _prospective_event(db, ep)
    comparison_event = _comparison_event(db, ep)
    return {
        "episode": ep.code,
        "prospective_baseline": {
            "occurred_at": baseline_event.occurred_at.isoformat(),
            "payload": _audit_payload(baseline_event),
        } if baseline_event else None,
        "paired_comparison": {
            "occurred_at": comparison_event.occurred_at.isoformat(),
            "payload": _audit_payload(comparison_event),
        } if comparison_event else None,
        "integrity": verifier_preenregistrements(
            _audit_payload(baseline_event) if baseline_event else None,
            _audit_payload(comparison_event) if comparison_event else None,
            baseline_event.occurred_at if baseline_event else None,
            comparison_event.occurred_at if comparison_event else None,
        ),
    }


@app.post("/episodes/{code}/need/lock")
def lock_need(code: str, db: Session = Depends(get_db)):
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404, "Épisode introuvable")
    need = db.scalar(
        select(NeedVersion)
        .where(NeedVersion.episode_id == ep.id, NeedVersion.active.is_(True))
        .order_by(NeedVersion.version.desc())
        .limit(1)
    )
    if need is None:
        raise HTTPException(409, "Aucune version active du besoin")
    missing = []
    if not need.current_situation.strip(): missing.append("situation")
    if not need.desired_outcome.strip(): missing.append("résultat recherché")
    if not need.counterfactual_plan: missing.append("situation sans FRONTIÈRE")
    if not need.initial_frontiere_hypothesis: missing.append("hypothèse initiale")
    if missing:
        raise HTTPException(409, "Impossible de verrouiller : " + ", ".join(missing))
    if need.locked_at is None:
        need.locked_at = datetime.now(timezone.utc)
        ep.status = "QUALIFIE"
        _audit(
            db,
            event_type="BESOIN_VERROUILLE",
            entity_type="NEED_VERSION",
            entity_id=need.id,
            episode_id=ep.id,
            payload={"version": need.version, "counterfactual_present": bool(need.counterfactual_plan), "hypothesis_present": bool(need.initial_frontiere_hypothesis)},
        )
        db.commit()
    return RedirectResponse(url=f"/episodes/{code}", status_code=303)


@app.post("/episodes/{code}/need/revise")
def revise_need(
    code: str,
    revision_reason: str = Form(...),
    current_situation: str = Form(...),
    desired_outcome: str = Form(...),
    sponsor: str = Form(""),
    latest_useful_date: str = Form(""),
    counterfactual_plan: str = Form(""),
    initial_frontiere_hypothesis: str = Form(""),
    db: Session = Depends(get_db),
):
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404, "Épisode introuvable")
    current = _require_locked_need(db, ep)
    reason = revision_reason.strip()
    if not reason:
        raise HTTPException(400, "La raison de révision est obligatoire.")
    deadline = date.fromisoformat(latest_useful_date) if latest_useful_date else None
    current.active = False
    revised = NeedVersion(
        episode_id=ep.id,
        version=current.version + 1,
        active=True,
        current_situation=current_situation.strip(),
        desired_outcome=desired_outcome.strip(),
        dependent_decision=current.dependent_decision,
        delay_consequence=current.delay_consequence,
        urgency=current.urgency,
        latest_useful_date=deadline,
        sponsor=sponsor.strip() or None,
        counterfactual_plan=counterfactual_plan.strip() or None,
        initial_frontiere_hypothesis=initial_frontiere_hypothesis.strip() or None,
        locked_at=datetime.now(timezone.utc),
    )
    if not revised.current_situation or not revised.desired_outcome or not revised.counterfactual_plan or not revised.initial_frontiere_hypothesis:
        raise HTTPException(409, "Une révision doit conserver la situation, le résultat, la situation sans FRONTIÈRE et l’hypothèse.")
    db.add(revised)
    db.flush()
    _audit(
        db,
        event_type="BESOIN_REVISE",
        entity_type="NEED_VERSION",
        entity_id=revised.id,
        episode_id=ep.id,
        payload={"from_version": current.version, "to_version": revised.version, "reason": reason},
    )
    db.commit()
    return RedirectResponse(url=f"/episodes/{code}#versions", status_code=303)


@app.post("/episodes/{code}/evidence")
def add_evidence(
    code: str,
    title: str = Form(...),
    evidence_type: str = Form("document"),
    source: str = Form(""),
    evidence_date: str = Form(""),
    quality: str = Form("C"),
    sensitivity_level: int = Form(1),
    data_environment: str = Form("RECHERCHE"),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404, "Épisode introuvable")
    if quality not in EVIDENCE_QUALITIES:
        raise HTTPException(400, "Qualité de preuve invalide")
    if data_environment not in DATA_ENVIRONMENTS:
        raise HTTPException(400, "Environnement de données invalide")
    if sensitivity_level < 1 or sensitivity_level > MAX_UNAUTHENTICATED_SENSITIVITY:
        raise HTTPException(400, "Les preuves de sensibilité 3–4 ne doivent pas être saisies dans ce prototype public.")
    parsed_date = date.fromisoformat(evidence_date) if evidence_date else None
    evidence = Evidence(
        episode_id=ep.id,
        evidence_type=evidence_type.strip() or "document",
        title=title.strip(),
        source=source.strip() or None,
        evidence_date=parsed_date,
        quality=quality,
        sensitivity_level=sensitivity_level,
        data_environment=data_environment,
        notes=notes.strip() or None,
    )
    db.add(evidence)
    db.flush()
    _audit(
        db,
        event_type="PREUVE_AJOUTEE",
        entity_type="EVIDENCE",
        entity_id=evidence.id,
        episode_id=ep.id,
        payload={"quality": quality, "data_environment": data_environment, "sensitivity_level": sensitivity_level},
    )
    db.commit()
    return RedirectResponse(url=f"/episodes/{code}#preuves", status_code=303)


@app.get("/contacts", response_class=HTMLResponse)
def contacts_page(request: Request, db: Session = Depends(get_db)):
    contacts = db.scalars(select(StakeholderContact).order_by(StakeholderContact.priority, StakeholderContact.id)).all()
    return templates.TemplateResponse(request=request, name="contacts.html", context={"contacts": contacts})


@app.post("/contacts")
def create_contact(
    institution: str = Form(...),
    function: str = Form(...),
    person: str = Form(""),
    priority: int = Form(3),
    hypothesis_tested: str = Form(...),
    single_ask: str = Form(...),
    minimal_success: str = Form(...),
    next_intro_sought: str = Form(""),
    document_to_send: str = Form(""),
    db: Session = Depends(get_db),
):
    next_id = (db.scalar(select(StakeholderContact.id).order_by(StakeholderContact.id.desc()).limit(1)) or 0) + 1
    contact = StakeholderContact(
        code=f"INT-{next_id:03d}", institution=institution.strip(), function=function.strip(),
        person=person.strip() or None, priority=max(1, min(priority, 5)),
        hypothesis_tested=hypothesis_tested.strip(), single_ask=single_ask.strip(),
        minimal_success=minimal_success.strip(), next_intro_sought=next_intro_sought.strip() or None,
        document_to_send=document_to_send.strip() or None,
    )
    db.add(contact)
    db.flush()
    _audit(
        db,
        event_type="INTERLOCUTEUR_AJOUTE",
        entity_type="STAKEHOLDER_CONTACT",
        entity_id=contact.id,
        payload={"code": contact.code, "institution": contact.institution, "priority": contact.priority},
    )
    db.commit()
    return RedirectResponse(url="/contacts", status_code=303)


@app.post("/contacts/{code}/update")
def update_contact(
    code: str,
    status: str = Form(...),
    produced_evidence: str = Form("no"),
    produced_case: str = Form("no"),
    produced_experiment: str = Form("no"),
    produced_introduction: str = Form("no"),
    followup_due_at: str = Form(""),
    outcome_summary: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    allowed = {"PLANIFIE", "CONTACTE", "REPONDU", "ENTRETIEN_PLANIFIE", "ENTRETIEN_REALISE", "SUIVI", "CLOS", "ABANDONNE"}
    if status not in allowed:
        raise HTTPException(400, "Statut de contact invalide")
    contact = db.scalar(select(StakeholderContact).where(StakeholderContact.code == code))
    if contact is None:
        raise HTTPException(404, "Interlocuteur introuvable")
    contact.status = status
    contact.produced_evidence = produced_evidence == "yes"
    contact.produced_case = produced_case == "yes"
    contact.produced_experiment = produced_experiment == "yes"
    contact.produced_introduction = produced_introduction == "yes"
    contact.followup_due_at = date.fromisoformat(followup_due_at) if followup_due_at else None
    contact.outcome_summary = outcome_summary.strip() or None
    contact.notes = notes.strip() or None
    if status == "CONTACTE" and contact.first_contact_at is None:
        contact.first_contact_at = datetime.now(timezone.utc)
    _audit(
        db,
        event_type="INTERLOCUTEUR_MIS_A_JOUR",
        entity_type="STAKEHOLDER_CONTACT",
        entity_id=contact.id,
        payload={
            "code": contact.code,
            "status": status,
            "produced_evidence": contact.produced_evidence,
            "produced_case": contact.produced_case,
            "produced_experiment": contact.produced_experiment,
            "produced_introduction": contact.produced_introduction,
        },
    )
    db.commit()
    return RedirectResponse(url="/contacts", status_code=303)


@app.get("/api/v1/research-export")
def research_export(db: Session = Depends(get_db)) -> dict:
    episodes = db.scalars(
        select(Episode)
        .options(selectinload(Episode.organization), selectinload(Episode.needs), selectinload(Episode.searches), selectinload(Episode.results))
        .where(Episode.synthetic.is_(False), Episode.sensitivity_level <= 2)
        .order_by(Episode.id)
    ).all()
    rows = []
    for ep in episodes:
        need = _active_need(ep)
        public = next((r for r in sorted(ep.searches, key=lambda x: x.id, reverse=True) if r.search_type == "PUBLIQUE"), None)
        result = ep.results[-1] if ep.results else None
        rows.append({
            "code": ep.code,
            "organization": ep.organization.name,
            "demand_level": ep.demand_level,
            "status": ep.status,
            "need_preexisting_frontiere": ep.need_preexisting_frontiere,
            "need_locked": bool(need and need.locked_at),
            "public_result": public.public_result if public else None,
            "result_status": result.result_status if result else None,
            "dominant_friction": result.dominant_friction if result else None,
            "frontiere_minutes": result.frontiere_minutes if result else 0,
            "institution_minutes": result.institution_minutes if result else 0,
        })
    return {"schema_version": "0.2", "episodes": rows}


@app.get("/evaluation", response_class=HTMLResponse)
def benchmark_page(request: Request, db: Session = Depends(get_db)):
    summary = benchmark_summary(db)
    rows = []
    for case in summary["cases"]:
        predictions = [p for p in summary["predictions"] if p.case_id == case.id]
        rows.append({
            "case": case,
            "expected_routes": json.loads(case.expected_routes_json),
            "expected_resource_forms": json.loads(case.expected_resource_forms_json),
            "predictions": [
                {"prediction": p, "metrics": benchmark_prediction_metrics(case, p)}
                for p in predictions
            ],
        })
    return templates.TemplateResponse(
        request=request,
        name="evaluation.html",
        context={"rows": rows, "methods": summary["methods"]},
    )


@app.post("/evaluation/{case_code}/reponse")
def add_benchmark_prediction(
    case_code: str,
    method: str = Form(...),
    method_version: str = Form("1.0"),
    routes: str = Form(""),
    resource_forms: str = Form(""),
    resources: str = Form(""),
    evidence_urls: str = Form(""),
    elapsed_seconds: float | None = Form(None),
    analyst_minutes: int = Form(0),
    verification_minutes: int = Form(0),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    case = db.scalar(select(BenchmarkCase).where(BenchmarkCase.code == case_code, BenchmarkCase.active.is_(True)))
    if case is None:
        raise HTTPException(404, "Cas d'évaluation introuvable")

    def items(text: str) -> list[str]:
        return [part.strip() for part in text.replace("\n", ",").split(",") if part.strip()]

    method_clean = method.strip()
    version_clean = method_version.strip() or "1.0"
    existing = db.scalar(
        select(BenchmarkPrediction).where(
            BenchmarkPrediction.case_id == case.id,
            BenchmarkPrediction.method == method_clean,
            BenchmarkPrediction.method_version == version_clean,
        )
    )
    if existing is not None:
        raise HTTPException(409, "Une prédiction existe déjà pour cette méthode et cette version sur ce cas.")
    prediction = BenchmarkPrediction(
        case_id=case.id,
        method=method_clean,
        method_version=version_clean,
        routes_json=json.dumps(items(routes), ensure_ascii=False),
        resource_forms_json=json.dumps(items(resource_forms), ensure_ascii=False),
        resources_json=json.dumps(items(resources), ensure_ascii=False),
        evidence_urls_json=json.dumps(items(evidence_urls), ensure_ascii=False),
        elapsed_seconds=max(0, elapsed_seconds) if elapsed_seconds is not None else None,
        analyst_minutes=max(0, analyst_minutes),
        verification_minutes=max(0, verification_minutes),
        notes=notes.strip() or None,
    )
    db.add(prediction)
    db.commit()
    return RedirectResponse(url=f"/evaluation#{case.code}", status_code=303)


@app.post("/evaluation/{case_code}/reveler")
def reveal_benchmark_case(case_code: str, db: Session = Depends(get_db)):
    case = db.scalar(select(BenchmarkCase).where(BenchmarkCase.code == case_code, BenchmarkCase.active.is_(True)))
    if case is None:
        raise HTTPException(404, "Cas d'évaluation introuvable")
    predictions = db.scalar(select(func.count(BenchmarkPrediction.id)).where(BenchmarkPrediction.case_id == case.id)) or 0
    if predictions < 1:
        raise HTTPException(409, "Au moins une prédiction est requise avant révélation.")
    case.revealed = True
    db.commit()
    return RedirectResponse(url=f"/evaluation#{case.code}", status_code=303)


@app.get("/api/v1/evaluation/aveugle")
def api_benchmark_blind(db: Session = Depends(get_db)) -> dict:
    cases = list(db.scalars(select(BenchmarkCase).where(BenchmarkCase.active.is_(True)).order_by(BenchmarkCase.code)).all())
    return {
        "cases": [
            {
                "code": case.code,
                "title": case.title,
                "prompt": case.prompt,
                "label_quality": case.label_quality,
                "revealed": case.revealed,
            }
            for case in cases
        ]
    }


@app.get("/api/v1/evaluation")
def api_benchmark(db: Session = Depends(get_db)) -> dict:
    summary = benchmark_summary(db)
    return {
        "case_count": len(summary["cases"]),
        "prediction_count": len(summary["predictions"]),
        "methods": summary["methods"],
    }


@app.get("/hypotheses", response_class=HTMLResponse)
def hypotheses_page(request: Request, db: Session = Depends(get_db)):
    hypotheses = hypothesis_summary(db)
    return templates.TemplateResponse(request=request, name="hypotheses.html", context={"hypotheses": hypotheses})
