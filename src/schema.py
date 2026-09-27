"""Pydantic v2 schemas for the Smart Guided Troubleshooting Engine.
Maintains exact compatibility with official student_kit/schema.py
and adds request/utility models.
"""
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class OfficialModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BaseDeeplink(OfficialModel):
    deeplink: str


class Deeplink(BaseDeeplink):
    description: str
    message: str | None = ""
    classes: dict[str, str] | None = None
    originalType: str | None = None


class Condition(str, Enum):
    greater = "greater"
    equal = "equal"
    less = "less"


class ResultTypes(str, Enum):
    boolean = "boolean"
    intNum = "integer"
    string = "str"
    floatNum = "float"


class actionCategory(str, Enum):
    auto = "auto"
    manual = "manual"
    critical = "critical"


class ValidationDeepLink(BaseDeeplink):
    key: str
    resultType: ResultTypes | None = None
    condition: Condition | None = None
    value: str | None = None


class StepGroup(OfficialModel):
    steps: list[str]
    validationDeeplink: ValidationDeepLink | None = None
    actionableDeeplink: Deeplink | None = None


class Action(OfficialModel):
    actionName: str
    description: str
    stepGroups: list[StepGroup]
    category: actionCategory | None = actionCategory.manual


class Goal(OfficialModel):
    goal: str
    title: str
    actions: list[Action]
    score: float


class ContextDeeplinkResponse(OfficialModel):
    """RAG response containing a list of Goal objects."""
    contexts: list[Goal] = Field(default_factory=list)


# --- Request and Submission Models ---

class SIISPayload(OfficialModel):
    title: str
    content: str


class TroubleshootRequest(OfficialModel):
    query: str
    siis_response: SIISPayload


class PreviewRequest(TroubleshootRequest):
    facts: dict[str, bool | None] | None = None


class ResultItem(OfficialModel):
    query: str
    query_variations: list[str]
    response: ContextDeeplinkResponse
