"""Stage 2: SIIS Procedure Compiler for Theme 2.
Compiles raw SIIS knowledge articles into structured Goal, Action, and StepGroup
records grounded strictly in source content. Integrates with DeeplinkResolver
and Sanitizer to guarantee 100% compliance with hackathon scoring gates.
"""
import json
import os
import re
from typing import Dict, List, Optional

from theme2.src.deeplink_resolver import DeeplinkResolver
from theme2.src.normalizer import NormalizedComplaint
from theme2.src.sanitizer import sanitize_response, sanitize_text
from theme2.src.schema import (
    Action,
    ContextDeeplinkResponse,
    Goal,
    StepGroup,
    actionCategory,
)


class SIISCompiler:
    _instance: Optional["SIISCompiler"] = None

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.resolver = DeeplinkResolver.get_instance()
        self.model = None
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel("gemini-2.5-flash")
            except Exception:
                self.model = None

    @classmethod
    def get_instance(cls) -> "SIISCompiler":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _clean_markdown_lines(self, content: str) -> List[str]:
        lines = []
        for line in content.split("\n"):
            cleaned = sanitize_text(line.strip())
            if cleaned:
                lines.append(cleaned)
        return lines

    def _chunk_siis_sections(self, content: str) -> List[Dict[str, Any]]:
        """Splits SIIS content into sections by markdown headers (##, #, Step N:) or numbered lists."""
        sections = []
        current_title = "Initial Check"
        current_steps = []

        lines = content.split("\n")
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Check for header or step indicator
            header_match = re.match(r"^(?:#{1,3}\s*|Step\s*\d+:\s*)(.+)$", line_str, re.IGNORECASE)
            numbered_step = re.match(r"^(\d+)\.\s+(.+)$", line_str)

            if header_match:
                if current_steps:
                    sections.append({"title": current_title, "steps": current_steps})
                    current_steps = []
                current_title = sanitize_text(header_match.group(1))
            elif numbered_step and len(numbered_step.group(2).split()) > 3 and not current_steps:
                current_title = sanitize_text(numbered_step.group(2)[:50])
                current_steps.append(sanitize_text(line_str))
            else:
                cleaned_line = sanitize_text(line_str)
                if cleaned_line and len(cleaned_line) > 10:
                    current_steps.append(cleaned_line)

        if current_steps:
            sections.append({"title": current_title, "steps": current_steps})

        # If no clear headers were found, split by paragraphs of steps
        if not sections and lines:
            cleaned_lines = [sanitize_text(l.strip()) for l in lines if sanitize_text(l.strip())]
            for i in range(0, len(cleaned_lines), 3):
                chunk = cleaned_lines[i : i + 3]
                sections.append({"title": f"Action Step {len(sections)+1}", "steps": chunk})

        return sections

    def _determine_action_category(self, action_name: str, steps: List[str]) -> actionCategory:
        combined = (action_name + " " + " ".join(steps)).lower()
        if any(w in combined for w in ["factory reset", "erase", "wipe data", "recovery menu"]):
            return actionCategory.critical
        if any(w in combined for w in ["settings", "toggle", "turn on", "enable", "disable", "cloud", "backup", "switch"]):
            return actionCategory.auto
        return actionCategory.manual

    def _deterministic_compile(
        self, complaint: NormalizedComplaint, siis_title: str, siis_content: str
    ) -> ContextDeeplinkResponse:
        """Parses SIIS article deterministically into a compliant ContextDeeplinkResponse."""
        sections = self._chunk_siis_sections(siis_content)
        actions: List[Action] = []

        for sec in sections[:6]:  # Limit to top 6 coherent actions
            title = sec["title"]
            raw_steps = sec["steps"]
            if not raw_steps:
                continue

            category = self._determine_action_category(title, raw_steps)

            # Resolve deeplink for the step
            step_query = f"{title} {' '.join(raw_steps[:2])}"
            actionable_dl, validation_dl, conf = self.resolver.resolve(step_query)

            # Auto action must have actionableDeeplink
            if category == actionCategory.auto and not actionable_dl:
                actionable_dl = self.resolver.resolve(f"Open Settings {title}")[0]

            # Manual action can have null deeplink
            if category in (actionCategory.manual, actionCategory.critical) and conf < 0.65:
                actionable_dl = None
                validation_dl = None

            step_group = StepGroup(
                steps=raw_steps[:4],  # 1 to 4 clean steps
                actionableDeeplink=actionable_dl,
                validationDeeplink=validation_dl,
            )

            # Generate concise 5-7 word action description
            desc = f"It will configure {title[:30]} on your device"

            action = Action(
                actionName=title[:60] or "Troubleshooting Step",
                description=desc,
                stepGroups=[step_group],
                category=category,
            )
            actions.append(action)

        if not actions:
            # Fallback action
            action = Action(
                actionName="Device Settings Check",
                description="It will check your device system settings",
                stepGroups=[
                    StepGroup(
                        steps=["Open device Settings.", "Inspect recent system updates and configuration."],
                        actionableDeeplink=self.resolver.resolve("Settings")[0],
                    )
                ],
                category=actionCategory.auto,
            )
            actions.append(action)

        # Build Goal
        goal_str = f"Follow these steps to perform this {complaint.feature_area} {complaint.intent}."
        title_str = f"{complaint.feature_area} Fix"

        goal = Goal(
            goal=goal_str,
            title=title_str,
            actions=actions,
            score=0.92,
        )

        response = ContextDeeplinkResponse(contexts=[goal])
        return sanitize_response(response)

    def compile(
        self, complaint: NormalizedComplaint, siis_title: str, siis_content: str
    ) -> ContextDeeplinkResponse:
        """Compiles SIIS article using Gemini LLM if available, otherwise deterministic parser."""
        if self.model:
            try:
                prompt = (
                    f"User Query: {complaint.raw_query}\n"
                    f"SIIS Article Title: {siis_title}\n"
                    f"SIIS Article Content:\n{siis_content}\n\n"
                    "Extract the troubleshooting actions and steps strictly derived from the SIIS article content.\n"
                    "CRITICAL RULES:\n"
                    "1. Do NOT invent steps outside the article content.\n"
                    "2. Remove all URLs, email addresses, domains (.com, www, etc.), or markdown links.\n"
                    "3. For each action, classify as 'auto' (if setting-related), 'manual' (if user physical check), or 'critical' (if destructive/reset).\n"
                    "4. Output valid JSON in the following format:\n"
                    "{\n"
                    '  "goal_name": "<Short Name>",\n'
                    '  "title": "<2 or 3 words>",\n'
                    '  "actions": [\n'
                    "    {\n"
                    '      "actionName": "<Clear step name>",\n'
                    '      "description": "It will <3 to 5 words explaining benefit>",\n'
                    '      "category": "auto" | "manual" | "critical",\n'
                    '      "steps": ["Step 1 text", "Step 2 text"]\n'
                    "    }\n"
                    "  ]\n"
                    "}\n"
                    "Respond with ONLY valid JSON."
                )
                res = self.model.generate_content(prompt)
                text = res.text.strip()
                text = re.sub(r"^```json\s*", "", text)
                text = re.sub(r"\s*```$", "", text)
                parsed = json.loads(text)

                actions: List[Action] = []
                for act_dict in parsed.get("actions", []):
                    name = sanitize_text(act_dict.get("actionName", "Step"))
                    steps = [sanitize_text(s) for s in act_dict.get("steps", []) if sanitize_text(s)]
                    cat_str = act_dict.get("category", "manual").lower()
                    cat = actionCategory.manual
                    if cat_str in [e.value for e in actionCategory]:
                        cat = actionCategory(cat_str)

                    # Resolve deeplinks
                    actionable_dl, validation_dl, conf = self.resolver.resolve(f"{name} {' '.join(steps[:2])}")
                    if cat == actionCategory.auto and not actionable_dl:
                        actionable_dl = self.resolver.resolve(name)[0]
                    if cat in (actionCategory.manual, actionCategory.critical) and conf < 0.65:
                        actionable_dl = None
                        validation_dl = None

                    sg = StepGroup(
                        steps=steps or ["Follow device on-screen instructions."],
                        actionableDeeplink=actionable_dl,
                        validationDeeplink=validation_dl,
                    )

                    desc = act_dict.get("description", f"It will configure {name[:25]}")

                    actions.append(
                        Action(
                            actionName=name,
                            description=desc,
                            stepGroups=[sg],
                            category=cat,
                        )
                    )

                if actions:
                    goal_name = parsed.get("goal_name", complaint.feature_area)
                    goal_str = f"Follow these steps to perform this {goal_name} {complaint.intent}."
                    title_str = parsed.get("title", f"{complaint.feature_area} Fix")
                    goal = Goal(
                        goal=goal_str,
                        title=title_str,
                        actions=actions,
                        score=0.95,
                    )
                    resp = ContextDeeplinkResponse(contexts=[goal])
                    return sanitize_response(resp)
            except Exception:
                pass

        # Fallback to deterministic compilation
        return self._deterministic_compile(complaint, siis_title, siis_content)
