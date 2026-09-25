"""Deterministic complaint normalization and explicit-fact extraction."""

from __future__ import annotations

import re
from threading import Lock

from pydantic import BaseModel, Field

FACT_KEYS = frozenset({
    "has_protector", "retain_protector", "touch_sensitivity_enabled",
    "screen_visible", "touch_working", "alternate_input_available",
    "inner_screen_visible", "cover_screen_visible",
    "inner_touch_working", "cover_touch_working",
    "hdmi_compatible", "backup_complete", "prior_steps_failed",
})


class NormalizedComplaint(BaseModel):
    raw_query: str
    technical_query: str
    feature_area: str
    requested_operation: str | None = None
    setting: str | None = None
    device_model: str | None = None
    app_reference: str | None = None
    negated: bool = False
    facts: dict[str, bool | None] = Field(default_factory=dict)
    fact_evidence: dict[str, str] = Field(default_factory=dict)
    unresolved_interpretation: str | None = None

    def compatibility_key(self) -> tuple[object, ...]:
        """Ambiguity and unknowns stay in answer-cache identity."""
        return (
            self.feature_area, self.requested_operation, self.setting,
            self.device_model, self.app_reference, self.negated,
            tuple((key, self.facts.get(key)) for key in sorted(FACT_KEYS)),
        )


class ComplaintNormalizer:
    _instance: ComplaintNormalizer | None = None
    _instance_lock = Lock()

    @classmethod
    def get_instance(cls) -> ComplaintNormalizer:
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    @staticmethod
    def normalize(query: str) -> NormalizedComplaint:
        lower = query.lower()
        feature = "device"
        feature_patterns = [
            ("touch", r"touch|sensitivity|protector|gesture|screen (?:does not|doesn't) respond"),
            ("email", r"email|gmail|mail server"),
            ("bluetooth", r"bluetooth|pairing|music share"),
            ("wifi", r"wi[- ]?fi|wireless network"),
            ("multi window", r"multi.?window|split.?screen|app pair|pop.?up view"),
            ("screen mirroring", r"mirroring|smart view|cast.*tv"),
            ("screen", r"screen|display|black|blank|flicker|rotate|camera"),
            ("data transfer", r"smart switch|transfer|backup|secure folder"),
            ("battery", r"battery|charg|power"),
        ]
        for name, pattern in feature_patterns:
            if re.search(pattern, lower):
                feature = name
                break

        operation = None
        if re.search(r"\b(disable|turn off|switch off|deactivate)\b", lower):
            operation = "disable"
        elif re.search(r"\b(enable|turn on|switch on|activate)\b", lower):
            operation = "enable"
        elif re.search(r"\b(update|adjust|change|set to)\b", lower):
            operation = "update"
        elif re.search(r"\b(open|find|where is|navigate to)\b", lower):
            operation = "open"
        setting = None
        for candidate in ("touch sensitivity", "bluetooth scanning", "bluetooth", "auto factory reset", "factory data reset", "adaptive brightness", "wi-fi scanning", "wi-fi", "multi window"):
            if candidate in lower:
                setting = candidate
                break
        device_match = re.search(r"\b(?:galaxy\s+)?(?:s\d{1,2}|z\s*(?:fold|flip)\s*\d*|a\d{1,2}|tab\s*\w+)\b", lower)
        device = re.sub(r"^(?:galaxy|samsung)\s*", "", device_match.group(0), flags=re.IGNORECASE).replace(" ", "").upper() if device_match else None
        app_match = re.search(r"\b(?:samsung kids|smart switch|gmail|outlook|camera)\b", lower)
        app = app_match.group(0) if app_match else None
        facts: dict[str, bool | None] = {}
        evidence: dict[str, str] = {}

        def add(key: str, value: bool, pattern: str) -> None:
            match = re.search(pattern, lower)
            if match:
                if key in facts and facts[key] != value:
                    facts[key] = None
                    evidence[key] = "conflicting query statements"
                elif key not in facts:
                    facts[key] = value
                    evidence[key] = match.group(0)

        add("has_protector", True, r"(?:have|has|using|with|wearing) (?:a |the )?(?:screen )?(?:protector|protective film)")
        add("has_protector", False, r"(?:no|without|removed|not using) (?:a |the )?(?:screen )?(?:protector|protective film)")
        add("retain_protector", True, r"(?:keep|retain|leave on) (?:my |the )?(?:screen )?(?:protector|film)")
        add("retain_protector", False, r"(?:remove|take off) (?:my |the )?(?:screen )?(?:protector|film)")
        add("retain_protector", True, r"(?:screen protector|protective film)[^.!?]{0,40}\b(?:keep|retain) it\b")
        add("retain_protector", False, r"(?:screen protector|protective film)[^.!?]{0,40}\b(?:remove|take off) it\b")
        add("touch_sensitivity_enabled", True, r"touch sensitivity (?:is )?(?:on|enabled)")
        add("touch_sensitivity_enabled", False, r"touch sensitivity (?:is )?(?:off|disabled)")
        add("screen_visible", False, r"(?:nothing visible|screen (?:is |went |became )?(?:completely )?(?:black|blank)|no image|cannot see (?:anything|the screen))")
        add("screen_visible", True, r"(?:screen (?:is )?visible|can see (?:the )?screen|display (?:still )?works)")
        for display in ("inner", "cover"):
            add(f"{display}_screen_visible", False,
                rf"(?:{display} (?:screen|display) (?:is |went |became )?(?:completely )?(?:black|blank)|(?:cannot|can't) see (?:the )?{display} (?:screen|display))")
            add(f"{display}_screen_visible", True,
                rf"(?:{display} (?:screen|display) (?:is |still )?(?:visible|working|lit)|can see (?:the )?{display} (?:screen|display))")
            add(f"{display}_touch_working", False,
                rf"(?:{display} (?:screen|display) (?:touch )?(?:does not|doesn't|isn't) (?:work|respond)|{display} touch (?:does not|doesn't|isn't) work)")
            add(f"{display}_touch_working", True,
                rf"(?:{display} (?:screen|display) touch (?:still )?works|{display} touch (?:is )?working)")
        add("touch_working", False, r"(?:touch (?:does not|doesn't|isn't) work|screen (?:does not|doesn't) respond to touch|unresponsive touch)")
        add("touch_working", True, r"(?:touch (?:still )?works|can use touch)")
        add("alternate_input_available", True, r"(?:have|using|connected) (?:a )?(?:usb )?(?:mouse|keyboard)")
        add("alternate_input_available", False, r"(?:no|without) (?:usb )?(?:mouse|keyboard)")
        add("hdmi_compatible", True, r"(?:hdmi (?:output )?(?:is )?(?:working|works|supported|compatible))")
        add("hdmi_compatible", False, r"(?:hdmi (?:output )?(?:not supported|incompatible))")
        add("backup_complete", True, r"(?:backup (?:is )?complete|already backed up)")
        add("backup_complete", False, r"(?:not backed up|no backup)")
        add("prior_steps_failed", True, r"(?:tried (?:everything|all steps)|previous steps failed|nothing (?:else )?worked)")
        add("prior_steps_failed", False, r"(?:have not tried|haven't tried) (?:the )?(?:previous|other) steps")
        return NormalizedComplaint(
            raw_query=query, technical_query=query.strip(), feature_area=feature,
            requested_operation=operation, setting=setting, device_model=device,
            app_reference=app, negated=bool(re.search(r"\b(?:not|don't|doesn't|can't|cannot|without)\b", lower)),
            facts=facts, fact_evidence=evidence,
            unresolved_interpretation=None if feature != "device" else "feature area not explicit",
        )
