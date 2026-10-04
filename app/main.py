from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .config import settings
from .database import Base, engine, get_db
from .models import (
    Decision,
    Discovery,
    Evidence,
    Episode,
    EpisodeResult,
    FrictionEvent,
    Hypothesis,
    KnowledgeItem,
    NeedVersion,
    Organization,
    Resource,
    RouteAssessment,
    SearchRun,
    StakeholderContact,
)
from .services import classify_public_search, dashboard_metrics, hypothesis_summary

BASE_DIR = Path(__file__).resolve().parent
@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

MAX_UNAUTHENTICATED_SENSITIVITY = 2
EVIDENCE_QUALITIES = {"A", "B", "C", "D", "E"}
DATA_ENVIRONMENTS = {"RECHERCHE", "RESEAU", "CANDIDATURE", "INTEGRITE"}


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
        raise HTTPException(409, "Le besoin et son contrefactuel doivent être verrouillés avant cette étape.")
    return need


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "frontiere-institut-interet-public", "version": "0.2.0"}


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
        name="dashboard.html",
        context={"episodes": episodes, "metrics": metrics, "hypotheses": hypotheses[:5]},
    )


@app.get("/episodes/new", response_class=HTMLResponse)
def new_episode(request: Request):
    return templates.TemplateResponse(request=request, name="episode_new.html", context={})


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
        )
        .where(Episode.code == code)
    )
    if ep is None:
        raise HTTPException(404, "Épisode introuvable")
    active_need = _active_need(ep)
    return templates.TemplateResponse(
        request=request,
        name="episode_detail.html",
        context={"episode": ep, "need": active_need, "need_locked": bool(active_need and active_need.locked_at)},
    )


@app.post("/episodes/{code}/public-search")
def add_public_search(
    code: str,
    complete: str = Form("no"),
    relevant_found: str = Form("unknown"),
    mobilizable_found: str = Form("unknown"),
    analyst_minutes: int = Form(0),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404)
    complete_b = complete == "yes"
    rel = None if relevant_found == "unknown" else relevant_found == "yes"
    mob = None if mobilizable_found == "unknown" else mobilizable_found == "yes"
    result = classify_public_search(complete=complete_b, relevant_found=rel, mobilizable_found=mob)
    run = SearchRun(
        episode_id=ep.id,
        search_type="PUBLIQUE",
        complete_enough_to_conclude=complete_b,
        public_relevant_found=rel,
        public_mobilizable_found=mob,
        public_result=result,
        analyst_minutes=max(0, analyst_minutes),
        notes=notes.strip() or None,
    )
    db.add(run)
    ep.status = "INVESTIGATION"
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
    d = Decision(
        episode_id=ep.id,
        selected_option=selected_option.strip(),
        justification=justification.strip(),
        contradictory_evidence=contradictory_evidence.strip() or None,
        uncertainties=uncertainties.strip() or None,
        confidence=confidence,
    )
    db.add(d)
    ep.status = "ORIENTE"
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
    db: Session = Depends(get_db),
):
    if state not in {"R0", "R1", "R2", "R3", "R4", "R5"}:
        raise HTTPException(400, "État de ressource invalide")
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404)
    resource = db.scalar(select(Resource).where(Resource.display_name == display_name.strip(), Resource.resource_type == resource_type))
    if resource is None:
        resource = Resource(resource_type=resource_type, display_name=display_name.strip())
        db.add(resource); db.flush()
    run = db.scalar(
        select(SearchRun)
        .where(SearchRun.episode_id == ep.id, SearchRun.search_type == search_type)
        .order_by(SearchRun.id.desc())
        .limit(1)
    )
    if run is None:
        run = SearchRun(episode_id=ep.id, search_type=search_type, method_name="saisie opérateur")
        db.add(run); db.flush()
    existing = db.scalar(select(Discovery).where(Discovery.search_run_id == run.id, Discovery.resource_id == resource.id))
    if existing is None:
        db.add(Discovery(search_run_id=run.id, resource_id=resource.id, source_channel=source_channel.strip() or "non précisé", state=state))
    else:
        existing.state = state
        existing.source_channel = source_channel.strip() or existing.source_channel
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
    start = datetime.fromisoformat(started_at)
    end = datetime.fromisoformat(ended_at) if ended_at else None
    db.add(FrictionEvent(episode_id=ep.id, category=category, subcategory=subcategory.strip() or None, started_at=start, ended_at=end, owner=owner.strip() or None, blocking=blocking == "yes", reason=reason.strip() or None))
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
    frontiere_minutes: int = Form(0),
    institution_minutes: int = Form(0),
    db: Session = Depends(get_db),
):
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404)
    db.add(EpisodeResult(episode_id=ep.id, result_status=result_status, actual_intervention=actual_intervention.strip() or None, actual_route=actual_route.strip() or None, outcome_description=outcome_description.strip(), dominant_friction=dominant_friction.strip() or None, frontiere_minutes=max(0, frontiere_minutes), institution_minutes=max(0, institution_minutes)))
    ep.status = "RESULTAT_ENREGISTRE"
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
    db.add(KnowledgeItem(source_episode_id=ep.id, knowledge_type=knowledge_type, title=title.strip(), content=content.strip(), scope=scope.strip() or None, evidence_level=evidence_level))
    db.commit()
    return RedirectResponse(url=f"/episodes/{code}#connaissance", status_code=303)


@app.get("/hypotheses", response_class=HTMLResponse)
def hypotheses_page(request: Request, db: Session = Depends(get_db)):
    hypotheses = hypothesis_summary(db)
    return templates.TemplateResponse(request=request, name="hypotheses.html", context={"hypotheses": hypotheses})
