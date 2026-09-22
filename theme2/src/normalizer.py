"""Stage 1: Complaint Normalizer for Theme 2.
Normalizes raw customer complaints into technical queries, intents,
and extracted device facts. Supports Gemini LLM with robust offline fallback.
"""
import os
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class NormalizedComplaint(BaseModel):
    raw_query: str
    technical_query: str
    feature_area: str
    intent: str = "Troubleshooting"  # "Troubleshooting" or "Configuration"
    device_model: Optional[str] = None
    facts: Dict[str, Optional[bool]] = {}


class ComplaintNormalizer:
    _instance: Optional["ComplaintNormalizer"] = None

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model = None
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel("gemini-2.5-flash")
            except Exception:
                self.model = None

    @classmethod
    def get_instance(cls) -> "ComplaintNormalizer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def normalize(self, query: str) -> NormalizedComplaint:
        """Normalizes user complaint into structured facts and technical intent."""
        # Try LLM first if available
        if self.model:
            try:
                prompt = (
                    f"Analyze this customer device complaint: '{query}'\n"
                    "Return a JSON with:\n"
                    "- technical_query: standard technical description of the problem\n"
                    "- feature_area: specific area (e.g., Screen Display, Battery, Network, Email, Data Transfer)\n"
                    "- intent: Troubleshooting or Configuration\n"
                    "- device_model: extracted device name if mentioned\n"
                    "- facts: dict of known facts such as screen_visible (bool/null), touch_working (bool/null), has_protector (bool/null)\n"
                    "Respond with ONLY valid JSON."
                )
                res = self.model.generate_content(prompt)
                text = res.text.strip()
                # Clean code blocks
                text = re.sub(r"^```json\s*", "", text)
                text = re.sub(r"\s*```$", "", text)
                import json
                parsed = json.loads(text)
                return NormalizedComplaint(
                    raw_query=query,
                    technical_query=parsed.get("technical_query", query),
                    feature_area=parsed.get("feature_area", "Device Issue"),
                    intent=parsed.get("intent", "Troubleshooting"),
                    device_model=parsed.get("device_model"),
                    facts=parsed.get("facts", {})
                )
            except Exception:
                pass  # Fall back to deterministic extractor

        # Deterministic / offline normalizer
        q_lower = query.lower()

        # Extract device model
        device_match = re.search(r'\b(galaxy\s+[a-z0-9\+]+(?:\s+ultra|\s+plus|\s+flip\s*\d*|\s+fold\s*\d*)?|samsung\s+[a-z0-9]+|tablet)\b', q_lower)
        device_model = device_match.group(1).title() if device_match else None

        # Determine feature area
        feature_area = "Device Issue"
        if any(w in q_lower for w in ["screen", "display", "flicker", "black", "blank", "dark"]):
            feature_area = "Screen Display"
        elif any(w in q_lower for w in ["battery", "drain", "charge", "power"]):
            feature_area = "Battery Power"
        elif any(w in q_lower for w in ["email", "gmail", "mail server"]):
            feature_area = "Email Connectivity"
        elif any(w in q_lower for w in ["touch", "lag", "unresponsive", "delay"]):
            feature_area = "Touch Sensitivity"
        elif any(w in q_lower for w in ["backup", "smart switch", "transfer data"]):
            feature_area = "Data Transfer"
        elif any(w in q_lower for w in ["bluetooth", "pair", "connect"]):
            feature_area = "Bluetooth Connection"

        # Determine intent
        intent = "Troubleshooting"
        if any(w in q_lower for w in ["how to enable", "configure", "set up", "how to use", "customize"]):
            intent = "Configuration"

        # Extract facts
        facts: Dict[str, Optional[bool]] = {}
        if "completely black" in q_lower or "completely blank" in q_lower or "shows no image" in q_lower:
            facts["screen_visible"] = False
        elif "screen flickers" in q_lower or "half black" in q_lower:
            facts["screen_visible"] = True

        if "doesn't respond to touch" in q_lower or "touch doesn't work" in q_lower:
            facts["touch_working"] = False
        elif "touch responsiveness is laggy" in q_lower or "inputs are delayed" in q_lower:
            facts["touch_working"] = True

        if "protector" in q_lower or "protective film" in q_lower:
            facts["has_protector"] = True

        # Generate technical query
        tech_words = [w for w in query.split() if w.lower() not in ["my", "i", "can't", "cant", "is", "a", "the", "and", "so"]]
        tech_q = " ".join(tech_words[:12]) if tech_words else query

        return NormalizedComplaint(
            raw_query=query,
            technical_query=tech_q,
            feature_area=feature_area,
            intent=intent,
            device_model=device_model,
            facts=facts
        )
