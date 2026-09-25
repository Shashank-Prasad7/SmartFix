"""Typed, source-addressable internal procedure representation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SourceBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    start: int
    end: int
    text: str
    section_id: str
    kind: Literal["heading", "body"]


class ConditionRef(BaseModel):
    fact: str
    expected: bool
    source_id: str
    text: str


class CompiledAction(BaseModel):
    id: str
    name: str
    source_ids: list[str]
    steps: list[str]
    category: Literal["auto", "manual", "critical"]
    operation: Literal["open", "enable", "disable", "update", "manual"]
    setting: str | None = None
    catalog_id: str | None = None
    conditions: list[ConditionRef] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    prerequisite_ids: list[str] = Field(default_factory=list)
    alternative_group: str | None = None


class Procedure(BaseModel):
    id: str
    title: str
    feature_area: str
    actions: list[CompiledAction]


class LedgerEntry(BaseModel):
    source_id: str
    disposition: Literal["procedural", "attached context", "non-procedural"]
    reason: str


class CompiledArticle(BaseModel):
    article_hash: str
    title: str
    blocks: list[SourceBlock]
    procedures: list[Procedure]
    ledger: list[LedgerEntry]

    def validate_structure(self) -> None:
        block_ids = {block.id for block in self.blocks}
        if len(block_ids) != len(self.blocks) or {entry.source_id for entry in self.ledger} != block_ids:
            raise ValueError("Source block accounting is incomplete")
        action_ids: set[str] = set()
        for procedure in self.procedures:
            if not procedure.actions:
                raise ValueError("Empty procedure")
            for action in procedure.actions:
                if action.id in action_ids or not action.steps or not set(action.source_ids) <= block_ids:
                    raise ValueError("Invalid action references")
                if not set(action.prerequisite_ids) <= action_ids:
                    raise ValueError("Invalid prerequisite order")
                action_ids.add(action.id)
