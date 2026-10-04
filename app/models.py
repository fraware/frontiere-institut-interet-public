from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(240), unique=True, index=True)
    organization_type: Mapped[str] = mapped_column(String(80), default="administration")
    public_sector: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    episodes: Mapped[list[Episode]] = relationship(back_populates="organization")


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    organizational_unit: Mapped[str | None] = mapped_column(String(240), nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(60), default="QUALIFICATION", index=True)
    demand_level: Mapped[str] = mapped_column(String(4), default="D0", index=True)
    sensitivity_level: Mapped[int] = mapped_column(Integer, default=1)
    nature: Mapped[str] = mapped_column(String(40), default="actuel")
    need_preexisting_frontiere: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    detected_at: Mapped[date] = mapped_column(Date, default=date.today)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization: Mapped[Organization] = relationship(back_populates="episodes")
    needs: Mapped[list[NeedVersion]] = relationship(back_populates="episode", cascade="all, delete-orphan")
    searches: Mapped[list[SearchRun]] = relationship(back_populates="episode", cascade="all, delete-orphan")
    route_assessments: Mapped[list[RouteAssessment]] = relationship(back_populates="episode", cascade="all, delete-orphan")
    decisions: Mapped[list[Decision]] = relationship(back_populates="episode", cascade="all, delete-orphan")
    friction_events: Mapped[list[FrictionEvent]] = relationship(back_populates="episode", cascade="all, delete-orphan")
    results: Mapped[list[EpisodeResult]] = relationship(back_populates="episode", cascade="all, delete-orphan")
    knowledge_items: Mapped[list[KnowledgeItem]] = relationship(back_populates="source_episode")
    evidence_items: Mapped[list[Evidence]] = relationship(back_populates="episode", cascade="all, delete-orphan")


class NeedVersion(Base):
    __tablename__ = "need_versions"
    __table_args__ = (UniqueConstraint("episode_id", "version", name="uq_need_episode_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    current_situation: Mapped[str] = mapped_column(Text)
    desired_outcome: Mapped[str] = mapped_column(Text)
    dependent_decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    delay_consequence: Mapped[str | None] = mapped_column(Text, nullable=True)
    urgency: Mapped[str] = mapped_column(String(30), default="moyenne")
    latest_useful_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sponsor: Mapped[str | None] = mapped_column(String(240), nullable=True)
    counterfactual_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    initial_frontiere_hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    episode: Mapped[Episode] = relationship(back_populates="needs")
    capability_requirements: Mapped[list[CapabilityRequirement]] = relationship(back_populates="need", cascade="all, delete-orphan")


class Capability(Base):
    __tablename__ = "capabilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(240), index=True)
    domain: Mapped[str] = mapped_column(String(140), index=True)
    function: Mapped[str] = mapped_column(String(180))
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="PROVISOIRE")
    taxonomy_version: Mapped[str] = mapped_column(String(20), default="0.1")


class CapabilityRequirement(Base):
    __tablename__ = "capability_requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    need_id: Mapped[int] = mapped_column(ForeignKey("need_versions.id"), index=True)
    capability_id: Mapped[int] = mapped_column(ForeignKey("capabilities.id"), index=True)
    requirement_type: Mapped[str] = mapped_column(String(20), default="IMPERATIVE")
    depth: Mapped[str] = mapped_column(String(80), default="intermediaire")
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    constraints: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_method: Mapped[str | None] = mapped_column(Text, nullable=True)

    need: Mapped[NeedVersion] = relationship(back_populates="capability_requirements")
    capability: Mapped[Capability] = relationship()


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int | None] = mapped_column(ForeignKey("episodes.id"), nullable=True, index=True)
    evidence_type: Mapped[str] = mapped_column(String(80), default="document")
    title: Mapped[str] = mapped_column(String(300))
    source: Mapped[str | None] = mapped_column(String(300), nullable=True)
    evidence_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    quality: Mapped[str] = mapped_column(String(2), default="C")
    sensitivity_level: Mapped[int] = mapped_column(Integer, default=1)
    data_environment: Mapped[str] = mapped_column(String(40), default="RECHERCHE")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    episode: Mapped[Episode | None] = relationship(back_populates="evidence_items")


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(50), index=True)
    display_name: Mapped[str] = mapped_column(String(280), index=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="ACTIVE")
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sensitivity_level: Mapped[int] = mapped_column(Integer, default=2)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SearchRun(Base):
    __tablename__ = "search_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), index=True)
    search_type: Mapped[str] = mapped_column(String(40), default="PUBLIQUE", index=True)
    method_name: Mapped[str] = mapped_column(String(140), default="recherche structuree")
    method_version: Mapped[str] = mapped_column(String(20), default="1.0")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    complete_enough_to_conclude: Mapped[bool] = mapped_column(Boolean, default=False)
    public_relevant_found: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    public_mobilizable_found: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    public_result: Mapped[str | None] = mapped_column(String(4), nullable=True)
    analyst_minutes: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    episode: Mapped[Episode] = relationship(back_populates="searches")
    discoveries: Mapped[list[Discovery]] = relationship(back_populates="search_run", cascade="all, delete-orphan")


class Discovery(Base):
    __tablename__ = "discoveries"
    __table_args__ = (UniqueConstraint("search_run_id", "resource_id", name="uq_discovery_search_resource"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    search_run_id: Mapped[int] = mapped_column(ForeignKey("search_runs.id"), index=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id"), index=True)
    source_channel: Mapped[str] = mapped_column(String(180), default="inconnu")
    state: Mapped[str] = mapped_column(String(4), default="R0")
    state_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    mission_specific_interest: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    available_as_of: Mapped[date | None] = mapped_column(Date, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    search_run: Mapped[SearchRun] = relationship(back_populates="discoveries")
    resource: Mapped[Resource] = relationship()


class RouteAssessment(Base):
    __tablename__ = "route_assessments"
    __table_args__ = (UniqueConstraint("episode_id", "route_code", name="uq_episode_route"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), index=True)
    route_code: Mapped[str] = mapped_column(String(40))
    route_label: Mapped[str] = mapped_column(String(160))
    status_initial: Mapped[str] = mapped_column(String(40), default="INFORMATION_INSUFFISANTE")
    status_current: Mapped[str] = mapped_column(String(40), default="INFORMATION_INSUFFISANTE")
    evidence_for: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_against: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocking_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action: Mapped[str | None] = mapped_column(Text, nullable=True)

    episode: Mapped[Episode] = relationship(back_populates="route_assessments")


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), index=True)
    decision_type: Mapped[str] = mapped_column(String(80), default="ORIENTATION")
    selected_option: Mapped[str] = mapped_column(String(180))
    options_considered: Mapped[str | None] = mapped_column(Text, nullable=True)
    justification: Mapped[str] = mapped_column(Text)
    contradictory_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    uncertainties: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(String(30), default="moyenne")
    decided_by: Mapped[str] = mapped_column(String(180), default="analyste")
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    locked: Mapped[bool] = mapped_column(Boolean, default=True)

    episode: Mapped[Episode] = relationship(back_populates="decisions")


class FrictionEvent(Base):
    __tablename__ = "friction_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), index=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    subcategory: Mapped[str | None] = mapped_column(String(80), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(180), nullable=True)
    blocking: Mapped[bool] = mapped_column(Boolean, default=False)
    avoidable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    prerequisite_event_id: Mapped[int | None] = mapped_column(ForeignKey("friction_events.id"), nullable=True)

    episode: Mapped[Episode] = relationship(back_populates="friction_events")


class EpisodeResult(Base):
    __tablename__ = "episode_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), index=True)
    result_status: Mapped[str] = mapped_column(String(50))
    actual_intervention: Mapped[str | None] = mapped_column(String(180), nullable=True)
    actual_route: Mapped[str | None] = mapped_column(String(180), nullable=True)
    first_useful_contribution_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    direct_cost_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    frontiere_minutes: Mapped[int] = mapped_column(Integer, default=0)
    institution_minutes: Mapped[int] = mapped_column(Integer, default=0)
    dominant_friction: Mapped[str | None] = mapped_column(String(80), nullable=True)
    outcome_description: Mapped[str] = mapped_column(Text)
    additionality_outcome: Mapped[str] = mapped_column(String(30), default="INDETERMINE")
    additionality_time: Mapped[str] = mapped_column(String(30), default="INDETERMINE")
    additionality_quality: Mapped[str] = mapped_column(String(30), default="INDETERMINE")
    additionality_cost: Mapped[str] = mapped_column(String(30), default="INDETERMINE")
    additionality_learning: Mapped[str] = mapped_column(String(30), default="INDETERMINE")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    episode: Mapped[Episode] = relationship(back_populates="results")


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_episode_id: Mapped[int | None] = mapped_column(ForeignKey("episodes.id"), nullable=True, index=True)
    knowledge_type: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(260))
    content: Mapped[str] = mapped_column(Text)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_level: Mapped[str] = mapped_column(String(2), default="C")
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    source_episode: Mapped[Episode | None] = relationship(back_populates="knowledge_items")
    reuses: Mapped[list[ReuseEvent]] = relationship(back_populates="knowledge", cascade="all, delete-orphan")


class ReuseEvent(Base):
    __tablename__ = "reuse_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    knowledge_id: Mapped[int] = mapped_column(ForeignKey("knowledge_items.id"), index=True)
    destination_episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), index=True)
    decision_changed: Mapped[bool] = mapped_column(Boolean, default=False)
    estimated_minutes_saved: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accessible_to_new_analyst: Mapped[bool] = mapped_column(Boolean, default=True)
    effect_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reused_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    knowledge: Mapped[KnowledgeItem] = relationship(back_populates="reuses")
    destination_episode: Mapped[Episode] = relationship()


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(260))
    definition: Mapped[str] = mapped_column(Text)
    strengthening_criterion: Mapped[str] = mapped_column(Text)
    weakening_criterion: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="OUVERTE")
    preregistered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class StakeholderContact(Base):
    __tablename__ = "stakeholder_contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    institution: Mapped[str] = mapped_column(String(240), index=True)
    function: Mapped[str] = mapped_column(String(240))
    person: Mapped[str | None] = mapped_column(String(180), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=3, index=True)
    hypothesis_tested: Mapped[str] = mapped_column(Text)
    single_ask: Mapped[str] = mapped_column(Text)
    data_sought: Mapped[str | None] = mapped_column(Text, nullable=True)
    minimal_success: Mapped[str] = mapped_column(Text)
    next_intro_sought: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_to_send: Mapped[str | None] = mapped_column(String(180), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="PLANIFIE", index=True)
    first_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    followup_due_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    meeting_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    produced_evidence: Mapped[bool] = mapped_column(Boolean, default=False)
    produced_case: Mapped[bool] = mapped_column(Boolean, default=False)
    produced_experiment: Mapped[bool] = mapped_column(Boolean, default=False)
    produced_introduction: Mapped[bool] = mapped_column(Boolean, default=False)
    outcome_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), index=True)
    activity_type: Mapped[str] = mapped_column(String(50), index=True)
    actor: Mapped[str] = mapped_column(String(180), default="équipe Frontière")
    active_minutes: Mapped[int] = mapped_column(Integer, default=0)
    waiting_minutes: Mapped[int] = mapped_column(Integer, default=0)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
