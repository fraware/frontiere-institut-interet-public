from datetime import date
from pydantic import BaseModel, Field


class EpisodeCreate(BaseModel):
    organization_name: str = Field(min_length=2, max_length=240)
    organizational_unit: str | None = None
    title: str = Field(min_length=3, max_length=300)
    current_situation: str = Field(min_length=10)
    desired_outcome: str = Field(min_length=5)
    demand_level: str = "D0"
    sensitivity_level: int = Field(default=1, ge=1, le=4)
    nature: str = "actuel"
    need_preexisting_frontiere: bool | None = None
    latest_useful_date: date | None = None
    sponsor: str | None = None
    counterfactual_plan: str | None = None
    initial_frontiere_hypothesis: str | None = None
