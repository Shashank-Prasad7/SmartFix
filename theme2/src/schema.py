"""Pydantic v2 schemas for the Smart Guided Troubleshooting Engine.
Maintains exact compatibility with official student_kit/schema.py
and adds request/utility models.
"""
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class BaseDeeplink(BaseModel):
    deeplink: str


class Deeplink(BaseDeeplink):
    description: str
    message: Optional[str] = ""
    classes: Optional[Dict[str, str]] = None
    originalType: Optional[str] = None


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
    resultType: Optional[ResultTypes] = None
    condition: Optional[Condition] = None
    value: Optional[str] = None


class StepGroup(BaseModel):
    steps: List[str]
    validationDeeplink: Optional[ValidationDeepLink] = None
    actionableDeeplink: Optional[Deeplink] = None


class Action(BaseModel):
    actionName: str
    description: str
    stepGroups: List[StepGroup]
    category: Optional[actionCategory] = actionCategory.manual


class Goal(BaseModel):
    goal: str
    title: str
    actions: List[Action]
    score: float


class ContextDeeplinkResponse(BaseModel):
    """RAG response containing a list of Goal objects."""
    contexts: List[Goal] = Field(default_factory=list)


# --- Request and Submission Models ---

class SIISPayload(BaseModel):
    title: str
    content: str


class TroubleshootRequest(BaseModel):
    query: str
    siis_response: SIISPayload


class PreviewRequest(TroubleshootRequest):
    facts: Optional[Dict[str, Optional[bool]]] = None


class ResultItem(BaseModel):
    query: str
    query_variations: List[str]
    response: ContextDeeplinkResponse
