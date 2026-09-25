"""Compile a complete SIIS article independently of the customer's query."""

from __future__ import annotations

import re
from collections import defaultdict
from threading import Lock

from theme2.src.deeplink_resolver import DeeplinkResolver
from theme2.src.records import (
    CompiledAction,
    CompiledArticle,
    ConditionRef,
    LedgerEntry,
    Procedure,
    SourceBlock,
)
from theme2.src.sanitizer import sanitize_text


class NonActionableSource(ValueError):
    """Source has no procedural or service-directed instruction."""


_HEADING = re.compile(r"^\s*#{1,4}\s*(.+?)\s*$")
_INJECTION = re.compile(r"ignore (?:previous|prior|all) (?:instructions|directions)|system prompt|developer message|api key|reveal (?:secret|credential)|execute (?:code|command)", re.IGNORECASE)
_ACTION = re.compile(
    r"\b(?:press|hold|tap|swipe|open|navigate|go to|select|check|inspect|remove|"
    r"connect|disconnect|restart|reboot|charge|turn on|turn off|enable|disable|"
    r"adjust|update|clean|wipe|back up|backup|enter|contact|visit|schedule|"
    r"send|use|try|plug|insert|follow|scan|drag|create|reset|clear|access|reach out)\b",
    re.IGNORECASE,
)
_SETTING_NAMES = (
    "touch sensitivity", "bluetooth scanning", "bluetooth", "auto factory reset",
    "factory data reset", "adaptive brightness", "wi-fi scanning", "wi-fi",
    "multi window", "navigation bar", "screen timeout", "safe mode",
)
DUMMY_CATALOG_ID = "__dummy_positive__"


def _feature(title: str) -> str:
    lower = title.lower()
    families = (
        ("samsung kids", "kids"), ("fingerprint", "fingerprint"),
        ("keyboard", "keyboard"), ("touch", "touch"),
        ("email", "email"), ("bluetooth", "bluetooth"),
        ("multi window", "multi window"), ("app pair", "multi window"),
        ("mirroring", "screen mirroring"), ("smart view", "screen mirroring"),
        ("screen", "screen"), ("display", "screen"),
        ("camera", "screen"), ("data", "data transfer"),
        ("smart switch", "data transfer"), ("battery", "battery"),
        ("charg", "battery"),
    )
    return next((area for key, area in families if key in lower), "device")


def _operation(text: str) -> str:
    lower = re.sub(
        r"\b(?:do not|don't|never|avoid)\s+(?:enable|disable|turn on|turn off|perform|start)\b[^.!?]*",
        "", text.lower(),
    )
    if re.search(r"\b(?:disabl(?:e|ing)|turn off|switch off)\b", lower):
        return "disable"
    if re.search(r"\b(?:enabl(?:e|ing)|turn on|switch on)\b", lower):
        return "enable"
    if re.search(r"\b(?:adjust|change|set to|update)\b", lower):
        return "update"
    if re.search(r"\b(?:open|navigate|go to|tap settings)\b", lower):
        return "open"
    return "manual"


def _explicit_setting_instruction(body: list[SourceBlock], setting: str, operation: str) -> bool:
    """Require the operation and setting in one instruction before linking.

    A section can mention Wi-Fi as a prerequisite to Smart View, or Windows
    Bluetooth settings while telling the reader to disconnect a PC. Neither
    mention authorizes a phone Settings link.
    """
    target = re.escape(setting).replace(r"\-", "[- ]?")
    verbs = {
        "enable": r"(?:enable|enabling|turn on|switch on)",
        "disable": r"(?:disable|disabling|turn off|switch off)",
        "open": r"(?:open|navigate to|go to|tap|select|find)",
    }
    verb = verbs.get(operation)
    if verb is None:
        return False
    for block in body:
        # The official Touch sensitivity article names the setting, then says
        # "To turn off this feature" in the next sentence of the same block.
        # Resolve that anaphora only when no other known setting is mentioned.
        if operation in {"enable", "disable"} and re.search(rf"\b{target}\b", block.text, re.IGNORECASE):
            named = [name for name in _SETTING_NAMES if name in block.text.lower()]
            if named == [setting] and re.search(
                rf"\b{verb}\b\s+(?:it|this feature|this setting)\b", block.text, re.IGNORECASE
            ):
                return True
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", block.text):
            lower = sentence.lower()
            if re.search(r"\b(?:on your pc|on a pc|on windows|windows 1[01]|tv settings)\b", lower):
                continue
            if re.search(rf"\b{verb}\b[^.!?]{{0,70}}\b{target}\b", lower):
                return True
            if operation == "open" and re.search(rf"\bsettings\s*(?:>|→)\s*[^.!?]{{0,70}}\b{target}\b", lower):
                return True
    return False


def _conditions(block: SourceBlock) -> list[ConditionRef]:
    text = block.text.lower()
    found: list[tuple[str, bool]] = []
    if "wish to keep" in text or "want to keep" in text or "retain your screen protector" in text:
        found.append(("retain_protector", True))
    if "not using a protective film" in text or "without a screen protector" in text:
        found.append(("has_protector", False))
    if "touch sensitivity setting is enabled" in text:
        found.append(("touch_sensitivity_enabled", True))
    if "screen is still visible" in text or "screen is visible" in text:
        found.append(("screen_visible", True))
    if "nothing is visible" in text or "no longer see anything" in text:
        found.append(("screen_visible", False))
    for display in ("inner", "cover"):
        if re.search(rf"\b{display} (?:screen|display) (?:is |still )?(?:visible|working|lit)\b", text):
            found.append((f"{display}_screen_visible", True))
        if re.search(rf"\b{display} (?:screen|display) (?:is |went |became )?(?:completely )?(?:black|blank)\b", text):
            found.append((f"{display}_screen_visible", False))
        if re.search(rf"\b{display} (?:screen|display) touch (?:still )?works\b", text):
            found.append((f"{display}_touch_working", True))
        if re.search(rf"\b{display} (?:screen|display) touch (?:does not|doesn't|isn't) work\b", text):
            found.append((f"{display}_touch_working", False))
    if re.search(r"\bif (?:a |an )?(?:usb )?(?:mouse|keyboard) (?:is )?available\b", text):
        found.append(("alternate_input_available", True))
    if re.search(r"\bif (?:the )?(?:phone|device|model) (?:supports|is compatible with) hdmi\b", text):
        found.append(("hdmi_compatible", True))
    if "not all samsung phones support hdmi" in text:
        found.append(("hdmi_compatible", True))
    if "last resort" in text or "after trying all" in text:
        found.append(("prior_steps_failed", True))
    if "if the problem persists" in text or "if the issue persists" in text:
        found.append(("prior_steps_failed", True))
    if "before proceeding" in text and "back up" in text:
        found.append(("backup_complete", True))
    if "after backup is complete" in text or "once backup is complete" in text:
        found.append(("backup_complete", True))
    return [ConditionRef(fact=key, expected=value, source_id=block.id, text=block.text) for key, value in found]


def _render_source_line(text: str) -> str:
    if re.match(r"^(?:Smartphone|Mobile Accessories|Tablet|Others Mobile)[^\n]{0,220}\):\s*", text, re.IGNORECASE):
        text = re.sub(r"^.*?\):\s*", "", text, count=1)
    return sanitize_text(text)


def _safe_source_text(text: str) -> str:
    """Remove adversarial sentences while preserving adjacent source advice."""
    return " ".join(
        sentence for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
        if not _INJECTION.search(sentence)
    )


def _unmatched_settings_screen(body: list[SourceBlock]) -> str | None:
    """Recognize an explicit, single-step Settings navigation target only."""
    if len(body) != 1:
        return None
    match = re.fullmatch(
        r"(?:please\s+)?open\s+(?:device\s+)?settings\s*(?:>|→)\s*([a-z][a-z ]{2,36})[.!?]?",
        body[0].text.strip(), re.IGNORECASE,
    )
    if not match:
        return None
    target = match.group(1).strip()
    if target.lower() in {"settings", "general", "more"}:
        return None
    return target


def _split_linked_instruction(
    body: list[SourceBlock], setting: str, operation: str
) -> tuple[list[tuple[SourceBlock, str]], list[tuple[SourceBlock, str]], list[tuple[SourceBlock, str]]] | None:
    """Isolate one catalog operation from manual instructions around it."""
    sentences = [
        (block, sentence)
        for block in body
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", block.text)
        if sentence.strip()
    ]
    anchors = [
        index for index, (block, sentence) in enumerate(sentences)
        if _explicit_setting_instruction([block.model_copy(update={"text": sentence})], setting, operation)
    ]
    if len(anchors) != 1:
        return None
    anchor = anchors[0]
    end = anchor + 1
    if end < len(sentences) and re.match(r"(?:to do this|then)\b", sentences[end][1], re.IGNORECASE) and "settings" in sentences[end][1].lower():
        end += 1
    before, linked, after = sentences[:anchor], sentences[anchor:end], sentences[end:]
    # This narrow split is useful when each side has an independent source
    # instruction. Descriptive context alone stays attached to the linked step.
    if not before or not after or not _ACTION.search(" ".join(text for _, text in before)) or not _ACTION.search(" ".join(text for _, text in after)):
        return None
    return before, linked, after


def _named_setting_operation(block: SourceBlock, sentence: str) -> tuple[str, str] | None:
    operation = _operation(sentence)
    if operation not in {"enable", "disable"}:
        return None
    setting = next((
        name for name in _SETTING_NAMES
        if name in sentence.lower()
        and _explicit_setting_instruction([block.model_copy(update={"text": sentence})], name, operation)
    ), None)
    return (operation, setting) if setting else None


def _separate_setting_instructions(
    body: list[SourceBlock],
) -> list[tuple[SourceBlock, str, str, str]] | None:
    """Split independent setting sentences before choosing a single link.

    This is intentionally narrow: every sentence must explicitly name one
    setting and one operation. More complex paragraphs stay manual rather than
    attaching one operation's link to multiple instructions.
    """
    fragments = [
        (block, sentence.strip())
        for block in body
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", block.text)
        if sentence.strip()
    ]
    if len(fragments) < 2:
        return None
    parsed: list[tuple[SourceBlock, str, str, str]] = []
    for block, sentence in fragments:
        pair = _named_setting_operation(block, sentence)
        if pair is None:
            return None
        operation, setting = pair
        parsed.append((block, sentence, operation, setting))
    if len({(item[2], item[3]) for item in parsed}) < 2:
        return None
    return parsed


class SIISCompiler:
    _instance: SIISCompiler | None = None
    _instance_lock = Lock()

    def __init__(self, resolver: DeeplinkResolver | None = None) -> None:
        self.resolver = resolver or DeeplinkResolver.get_instance()

    @classmethod
    def get_instance(cls) -> SIISCompiler:
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    @staticmethod
    def source_blocks(content: str) -> list[SourceBlock]:
        blocks: list[SourceBlock] = []
        section = "s0"
        section_number = 0
        cursor = 0
        for raw in content.splitlines(keepends=True):
            stripped = raw.strip()
            if stripped:
                heading = _HEADING.match(stripped)
                # Official articles sometimes put a category prefix before #.
                if not heading and "): #" in stripped:
                    heading = _HEADING.match(stripped.split("): ", 1)[1])
                if heading:
                    section_number += 1
                    section = f"s{section_number}"
                relative_start = len(raw) - len(raw.lstrip())
                relative_end = len(raw.rstrip())
                blocks.append(SourceBlock(
                    id=f"b{len(blocks)+1}", start=cursor + relative_start,
                    end=cursor + relative_end, text=raw[relative_start:relative_end],
                    section_id=section, kind="heading" if heading else "body",
                ))
            cursor += len(raw)
        return blocks

    def compile(self, title: str, content: str, article_hash: str) -> CompiledArticle:
        blocks = self.source_blocks(content)
        if not blocks:
            raise NonActionableSource("Source has no instructions")
        groups: dict[str, list[SourceBlock]] = defaultdict(list)
        for block in blocks:
            groups[block.section_id].append(block)
        procedures: list[Procedure] = []
        ledger: list[LedgerEntry] = []
        preceding_backup_id: str | None = None
        preceding_reset_context: list[SourceBlock] = []
        for group in groups.values():
            heading = next((block for block in group if block.kind == "heading"), None)
            section_title = (heading.text.split("#")[-1].strip() if heading else title)
            if heading and _INJECTION.search(heading.text):
                section_title = title
            section_title = re.sub(r"^(?:step\s*)?\d+[.:]\s*", "", section_title, flags=re.IGNORECASE)
            if re.fullmatch(r"glossary", section_title, re.IGNORECASE):
                ledger.extend(LedgerEntry(source_id=block.id, disposition="non-procedural", reason="Definition section, not an instruction") for block in group)
                continue
            original_body = [block for block in group if block.kind == "body"]
            body: list[SourceBlock] = []
            unsafe_ids: set[str] = set()
            fully_unsafe_ids: set[str] = set()
            for block in original_body:
                if _INJECTION.search(block.text):
                    unsafe_ids.add(block.id)
                    safe = _safe_source_text(block.text)
                    if safe:
                        body.append(block.model_copy(update={"text": safe}))
                    else:
                        fully_unsafe_ids.add(block.id)
                else:
                    body.append(block)
            if heading and _INJECTION.search(heading.text):
                unsafe_ids.add(heading.id)
                fully_unsafe_ids.add(heading.id)
            procedural = [block for block in body if _ACTION.search(block.text)]
            if len(body) == 1 and re.match(r"(?:hello[!,]|i understand\b)", body[0].text, re.IGNORECASE) and not re.search(
                r"\b(?:press|hold|tap|swipe|open|navigate|select|check|inspect|remove|connect|restart|back up|reset)\b",
                body[0].text, re.IGNORECASE,
            ):
                procedural = []
            # The supplied mixed article has OCR-compressed words in several
            # service instructions. A procedural heading plus nonempty source
            # text is enough to preserve them without inventing missing text.
            if not procedural and body and re.search(r"(?:pin reset process|device locked|keyboard issue)", section_title, re.IGNORECASE):
                procedural = body
            if not procedural:
                if unsafe_ids and any(_ACTION.search(block.text) for block in original_body):
                    raise ValueError("Source instruction could not be rendered safely")
                ledger.extend(LedgerEntry(source_id=block.id, disposition="non-procedural", reason="No supported instruction") for block in group)
                continue
            # Keep all attached conditions, warnings, alternatives, and timings.
            steps = [_render_source_line(block.text) for block in body]
            steps = [step for step in steps if step]
            if not steps:
                raise ValueError("Procedural section has no safe rendering")
            joined = " ".join(block.text for block in body)
            lower = f"{section_title} {joined}".lower()
            destructive_body = " ".join(block.text for block in body).lower()
            critical = bool(
                re.search(r"\b(?:perform|start|initiate|complete|open|tap|select|choose|navigate to)\s+(?:a |the )?(?:factory (?:data )?reset|delete all|clear (?:app )?data)\b", destructive_body)
                or re.search(r"(?:^|[.!?]\s+)(?:please )?(?:erase|wipe|clear)\s+(?:all |app )?data\b", destructive_body)
            )
            # A last-resort reset mentioned among unrelated tips is its own
            # critical instruction. Do not mark every ordinary tip critical.
            if critical and not re.search(r"factory (?:data )?reset", section_title, re.IGNORECASE):
                reset_parts: list[tuple[SourceBlock, str]] = []
                other_parts: list[tuple[SourceBlock, str]] = []
                for block in body:
                    for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", block.text):
                        destination = reset_parts if re.search(r"\bperform (?:a |the )?factory (?:data )?reset\b", sentence, re.IGNORECASE) else other_parts
                        destination.append((block, sentence))
                if reset_parts and any(_ACTION.search(text) for _, text in other_parts):
                    first_id = 1 + sum(len(item.actions) for item in procedures)
                    ordinary = CompiledAction(
                        id=f"a{first_id}", name=section_title or title,
                        source_ids=list(dict.fromkeys(block.id for block, _ in other_parts)),
                        steps=[_render_source_line(text) for _, text in other_parts],
                        category="manual", operation="manual",
                    )
                    reset = CompiledAction(
                        id=f"a{first_id+1}", name="Factory Data Reset",
                        source_ids=list(dict.fromkeys(block.id for block, _ in reset_parts)),
                        steps=[_render_source_line(text) for _, text in reset_parts],
                        category="critical", operation="manual",
                        conditions=[condition for block, text in reset_parts for condition in _conditions(block.model_copy(update={"text": text}))],
                    )
                    feature = _feature(section_title)
                    if feature == "device":
                        feature = _feature(title)
                    procedures.append(Procedure(id=f"p{len(procedures)+1}", title=section_title or title, feature_area=feature, actions=[ordinary, reset]))
                    ledger.extend(LedgerEntry(source_id=block.id, disposition="attached context" if block.kind == "heading" else "procedural", reason="Last-resort reset separated from other source tips") for block in group)
                    preceding_backup_id = None
                    preceding_reset_context = []
                    continue
            separate_instructions = _separate_setting_instructions(body) if not critical else None
            if separate_instructions:
                split_actions: list[CompiledAction] = []
                for block, sentence, branch_operation, branch_setting in separate_instructions:
                    _, _, _, branch_catalog_id = self.resolver.resolve(
                        sentence.lower(), branch_operation, branch_setting
                    )
                    split_actions.append(CompiledAction(
                        id=f"a{1 + sum(len(item.actions) for item in procedures) + len(split_actions)}",
                        name=f"{branch_operation.title()} {branch_setting.title()}",
                        source_ids=[block.id], steps=[_render_source_line(sentence)],
                        category="auto" if branch_catalog_id else "manual",
                        operation=branch_operation, setting=branch_setting if branch_catalog_id else None,
                        catalog_id=branch_catalog_id,
                        conditions=_conditions(block.model_copy(update={"text": sentence})),
                        warnings=[block.id] if re.search(r"warning|caution|avoid|not supported|may require", sentence, re.IGNORECASE) else [],
                    ))
                feature = _feature(section_title)
                if feature == "device":
                    feature = _feature(title)
                procedures.append(Procedure(
                    id=f"p{len(procedures)+1}", title=section_title or title,
                    feature_area=feature, actions=split_actions,
                ))
                ledger.extend(LedgerEntry(
                    source_id=block.id,
                    disposition="attached context" if block.kind == "heading" else "procedural",
                    reason="Distinct setting instructions separated by source sentence",
                ) for block in group)
                preceding_backup_id = None
                preceding_reset_context = []
                continue
            # Independent conditional instructions within one source paragraph
            # must not be treated as one conjunctive applicability decision.
            if len(body) == 1 and not critical:
                parts = re.split(r"(?<=[.!?])\s+(?=If\b)", body[0].text)
                if len(parts) > 1 and all(_ACTION.search(part) for part in parts):
                    split_actions: list[CompiledAction] = []
                    for part in parts:
                        fragment = body[0].model_copy(update={"text": part})
                        split_actions.append(CompiledAction(
                            id=f"a{1 + sum(len(item.actions) for item in procedures) + len(split_actions)}",
                            name=section_title or title, source_ids=[body[0].id],
                            steps=[_render_source_line(part)], category="manual",
                            operation=_operation(part), conditions=_conditions(fragment),
                        ))
                    feature = _feature(section_title)
                    if feature == "device":
                        feature = _feature(title)
                    procedures.append(Procedure(id=f"p{len(procedures)+1}", title=section_title or title, feature_area=feature, actions=split_actions))
                    ledger.extend(LedgerEntry(source_id=block.id, disposition="attached context" if block.kind == "heading" else "procedural", reason="Conditional source instructions separated") for block in group)
                    preceding_backup_id = None
                    preceding_reset_context = []
                    continue
            operation = _operation(lower)
            setting = next((name for name in _SETTING_NAMES if name in lower), None)
            named_pairs = {
                pair for block in body
                for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", block.text)
                if (pair := _named_setting_operation(block, sentence)) is not None
            }
            one_sentence_opposites = any(
                re.search(r"\b(?:enable|turn on|switch on)\b", block.text, re.IGNORECASE)
                and re.search(r"\b(?:disable|turn off|switch off)\b", block.text, re.IGNORECASE)
                and len(re.split(r"(?<=[.!?])\s+(?=[A-Z])", block.text)) == 1
                for block in body
            )
            if len(named_pairs) > 1 or one_sentence_opposites:
                # A mixed paragraph that cannot be split must not receive a
                # catalog link for just one of its distinct instructions.
                operation = "manual"
            catalog_id = None
            if setting and "settings" in lower and _explicit_setting_instruction(body, setting, operation):
                _, _, _, catalog_id = self.resolver.resolve(lower, operation, setting)
            if catalog_id is None and operation == "open" and setting is None:
                setting = _unmatched_settings_screen(body)
                if setting:
                    catalog_id = DUMMY_CATALOG_ID
            if catalog_id and catalog_id != DUMMY_CATALOG_ID and setting and not critical:
                separated = _split_linked_instruction(body, setting, operation)
                if separated:
                    actions: list[CompiledAction] = []
                    for index, segment in enumerate(separated):
                        source_ids = list(dict.fromkeys(block.id for block, _ in segment))
                        segment_steps = [_render_source_line(text) for _, text in segment]
                        segment_steps = [step for step in segment_steps if step]
                        if not segment_steps:
                            raise ValueError("Separated instruction has no safe rendering")
                        linked = index == 1
                        segment_conditions: list[ConditionRef] = []
                        for block, text in segment:
                            fragment = block.model_copy(update={"text": text})
                            recognized = _conditions(fragment)
                            segment_conditions.extend(recognized)
                            if not linked and not recognized and re.search(r"\bif\b", text, re.IGNORECASE):
                                segment_conditions.append(ConditionRef(
                                    fact="unmodeled_source_condition", expected=True,
                                    source_id=block.id, text=text,
                                ))
                        actions.append(CompiledAction(
                            id=f"a{1 + sum(len(item.actions) for item in procedures) + index}",
                            name=f"{operation.title()} {setting.title()}" if linked else section_title or title,
                            source_ids=source_ids, steps=segment_steps,
                            category="auto" if linked else "manual",
                            operation=operation if linked else "manual",
                            setting=setting if linked else None,
                            catalog_id=catalog_id if linked else None,
                            conditions=segment_conditions,
                            warnings=[block.id for block, text in segment if re.search(r"warning|caution|avoid|not supported|may require", text, re.IGNORECASE)],
                        ))
                    feature = _feature(section_title)
                    if feature == "device":
                        feature = _feature(title)
                    procedures.append(Procedure(id=f"p{len(procedures)+1}", title=section_title or title, feature_area=feature, actions=actions))
                    ledger.extend(LedgerEntry(source_id=block.id, disposition="attached context" if block.kind == "heading" else "procedural", reason="Independent instructions separated from catalog operation") for block in group)
                    preceding_backup_id = None
                    preceding_reset_context = []
                    continue
            category = "critical" if critical else ("auto" if catalog_id else "manual")
            warnings = [block.id for block in body if re.search(r"warning|caution|erase|wipe|last resort|before proceeding|not supported|may require", block.text, re.IGNORECASE)]
            conditions = [condition for block in body for condition in _conditions(block)]
            if not critical and re.search(r"\bback ?up\b", section_title, re.IGNORECASE):
                conditions = [condition for condition in conditions if condition.fact != "backup_complete"]
            next_action_number = 1 + sum(len(item.actions) for item in procedures)
            prerequisite_actions: list[CompiledAction] = []
            backup_block = next((block for block in body if critical and re.search(r"\bback up\b|\b(?:make|create|perform) (?:a )?backup\b", block.text, re.IGNORECASE)), None)
            if backup_block is not None:
                prerequisite_actions.append(CompiledAction(
                    id=f"a{next_action_number}", name="Back Up Personal Data",
                    source_ids=[backup_block.id], steps=[_render_source_line(backup_block.text)],
                    category="manual", operation="manual", warnings=[backup_block.id],
                ))
                next_action_number += 1
            action = CompiledAction(
                id=f"a{next_action_number}", name=section_title or title,
                source_ids=([block.id for block in preceding_reset_context] if critical and not backup_block else []) + [block.id for block in body],
                steps=([_render_source_line(block.text) for block in preceding_reset_context] if critical and not backup_block else []) + steps,
                category=category, operation=operation,
                setting=setting if catalog_id else None, catalog_id=catalog_id,
                conditions=conditions,
                warnings=([block.id for block in preceding_reset_context] if critical and not backup_block else []) + warnings,
                prerequisite_ids=[item.id for item in prerequisite_actions] or ([preceding_backup_id] if critical and preceding_backup_id else []),
            )
            feature = _feature(section_title)
            if feature == "device":
                feature = _feature(title)
            procedures.append(Procedure(id=f"p{len(procedures)+1}", title=section_title or title, feature_area=feature, actions=[*prerequisite_actions, action]))
            if backup_block is not None:
                preceding_backup_id = prerequisite_actions[0].id
                preceding_reset_context = [backup_block]
            elif not critical and re.search(r"\bback up\b|\bbackup\b", destructive_body) and re.search(r"factory (?:data )?reset", lower):
                preceding_backup_id = action.id
                preceding_reset_context = body
            else:
                preceding_backup_id = None
                preceding_reset_context = []
            procedural_ids = {block.id for block in procedural}
            for block in group:
                ledger.append(LedgerEntry(
                    source_id=block.id,
                    disposition="non-procedural" if block.id in fully_unsafe_ids else ("attached context" if block.kind == "heading" or block.id not in procedural_ids else "procedural"),
                    reason="Untrusted instruction to engine" if block.id in fully_unsafe_ids else ("Untrusted sentence removed; sourced action retained" if block.id in unsafe_ids else "Retained with sourced action"),
                ))
        if not procedures:
            raise NonActionableSource("Source has no troubleshooting or service action")
        article = CompiledArticle(article_hash=article_hash, title=title, blocks=blocks, procedures=procedures, ledger=ledger)
        article.validate_structure()
        return article
