from __future__ import annotations

from contextlib import asynccontextmanager
import json
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
    AuditEvent,
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
from .services import classify_public_search, dashboard_metrics, empirical_metrics, hypothesis_summary

BASE_DIR = Path(__file__).resolve().parent
@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version="0.4.0", lifespan=lifespan)
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
        raise HTTPException(409, "Le besoin et son contrefactuel doivent être verrouillés avant cette étape.")
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


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "frontiere-institut-interet-public", "version": "0.4.0"}


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


@app.get("/empirique", response_class=HTMLResponse)
def empirical_dashboard(request: Request, db: Session = Depends(get_db)):
    metrics = empirical_metrics(db)
    return templates.TemplateResponse(
        request=request,
        name="empirical.html",
        context={"metrics": metrics},
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
        name="episode_detail.html",
        context={
            "episode": ep,
            "need": active_need,
            "need_locked": bool(active_need and active_need.locked_at),
            "reusable_knowledge": reusable_knowledge,
            "reuse_events": reuse_events,
        },
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
    _require_locked_need(db, ep)
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
    db.flush()
    ep.status = "INVESTIGATION"
    locked_need = _require_locked_need(db, ep)
    _audit(
        db,
        event_type="RECHERCHE_PUBLIQUE_ENREGISTREE",
        entity_type="SEARCH_RUN",
        entity_id=run.id,
        episode_id=ep.id,
        payload={"need_version_id": locked_need.id, "public_result": result, "complete": complete_b, "analyst_minutes": max(0, analyst_minutes)},
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
    db: Session = Depends(get_db),
):
    if state not in {"R0", "R1", "R2", "R3", "R4", "R5"}:
        raise HTTPException(400, "État de ressource invalide")
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404)
    locked_need = _require_locked_need(db, ep)
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
    db.flush()
    _audit(
        db,
        event_type="RESSOURCE_ETAT_ENREGISTRE",
        entity_type="RESOURCE",
        entity_id=resource.id,
        episode_id=ep.id,
        payload={"need_version_id": locked_need.id, "search_type": search_type, "state": state, "source_channel": source_channel.strip() or "non précisé"},
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
    frontiere_minutes: int = Form(0),
    institution_minutes: int = Form(0),
    db: Session = Depends(get_db),
):
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise HTTPException(404)
    locked_need = _require_locked_need(db, ep)
    result = EpisodeResult(episode_id=ep.id, result_status=result_status, actual_intervention=actual_intervention.strip() or None, actual_route=actual_route.strip() or None, outcome_description=outcome_description.strip(), dominant_friction=dominant_friction.strip() or None, frontiere_minutes=max(0, frontiere_minutes), institution_minutes=max(0, institution_minutes))
    db.add(result)
    db.flush()
    ep.status = "RESULTAT_ENREGISTRE"
    _audit(
        db,
        event_type="RESULTAT_ENREGISTRE",
        entity_type="EPISODE_RESULT",
        entity_id=result.id,
        episode_id=ep.id,
        payload={"need_version_id": locked_need.id, "result_status": result_status, "dominant_friction": dominant_friction.strip() or None},
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
    if not need.counterfactual_plan: missing.append("contrefactuel")
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
        raise HTTPException(409, "Une révision doit conserver situation, résultat, contrefactuel et hypothèse.")
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


@app.get("/hypotheses", response_class=HTMLResponse)
def hypotheses_page(request: Request, db: Session = Depends(get_db)):
    hypotheses = hypothesis_summary(db)
    return templates.TemplateResponse(request=request, name="hypotheses.html", context={"hypotheses": hypotheses})
