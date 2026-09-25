"""Strict formatting enforcer and sanitizer for Theme 2.
Enforces all hackathon constraints:
- Gate G5: Zero URL leaks (recursively cleans text)
- A1: Goal regex compliance
- A1: Title word count (2-3 words)
- A1: Action description format (5-7 words starting with "It will")
- A1: Score in range [0.0, 1.0]
- A2: Auto action deeplink requirement
"""
import math
import re
from typing import Any

from theme2.src.schema import (
    ContextDeeplinkResponse,
    Deeplink,
    actionCategory,
)

# Regex pattern for prohibited URL fragments
URL_PATTERNS = [
    re.compile(r'https?://\S+', re.IGNORECASE),
    re.compile(r'www\.[a-zA-Z0-9_\-\.]+', re.IGNORECASE),
    re.compile(r'\b[a-zA-Z0-9_\-\.]+@(?:samsung|gmail|yahoo|[a-zA-Z0-9_\-]+)\.[a-zA-Z]{2,}\b', re.IGNORECASE),
    re.compile(r'\b[a-zA-Z0-9_\-\.]+\.(?:com|org|net|edu|gov|io|html|htm|php|jsp)\b', re.IGNORECASE),
    re.compile(r'!\[.*?\]\(.*?\)', re.IGNORECASE),  # Markdown images
    re.compile(r'\[(.*?)\]\(.*?\)', re.IGNORECASE),  # Markdown links -> keep text
    re.compile(r'<[^>]+>', re.IGNORECASE),           # HTML tags
]

GOAL_REGEX = re.compile(r'^Follow these steps to perform this [^.]+ (Troubleshooting|Configuration)\.$')
PROHIBITED = re.compile(r"https?://|www\.|\.(?:com|org|net|edu|gov|io|html|htm|php|jsp)\b|!\[|\[[^]]+\]\(|<\s*/?\s*(?:a|img)\b", re.IGNORECASE)


def sanitize_text(text: str) -> str:
    """Removes any URLs, domains, markdown links/images, and HTML tags from text."""
    if not text:
        return ""
    cleaned = text
    cleaned = re.sub(r"\b(?:kidshome\.pin@samsung\.com)\b", "the Samsung Kids PIN reset contact", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", "the listed contact", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'!\[[^]]*\]\([^)]*\)', '', cleaned)
    # Replace markdown links with their label
    cleaned = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', cleaned)
    # Remove markdown images
    # Strip HTML tags
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    # Strip http/https/www/domains/emails
    for pat in URL_PATTERNS[:4]:
        cleaned = pat.sub('', cleaned)
    # Clean redundant whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def validate_response(response: ContextDeeplinkResponse) -> None:
    """Reject incomplete, malformed, or leaking official success bodies."""
    if not response.contexts:
        raise ValueError("Empty contexts")
    for goal in response.contexts:
        if not GOAL_REGEX.fullmatch(goal.goal):
            raise ValueError("Invalid goal")
        if not 2 <= len(goal.title.split()) <= 3:
            raise ValueError("Invalid title")
        if not math.isfinite(goal.score) or not 0 <= goal.score <= 1:
            raise ValueError("Invalid score")
        if not goal.actions:
            raise ValueError("Empty actions")
        for action in goal.actions:
            if action.category is None:
                raise ValueError("Missing action category")
            if not action.actionName.strip() or not action.description.startswith("It will ") or not 5 <= len(action.description.split()) <= 7:
                raise ValueError("Invalid action")
            if not action.stepGroups:
                raise ValueError("Empty step groups")
            for group in action.stepGroups:
                if not group.steps or any(not step.strip() for step in group.steps):
                    raise ValueError("Empty steps")
                if action.category == actionCategory.auto and group.actionableDeeplink is None:
                    raise ValueError("Automatic action lacks link")
                if group.actionableDeeplink and not group.actionableDeeplink.deeplink.startswith("bixby://"):
                    raise ValueError("Invalid actionable URI")
                if group.validationDeeplink and not group.validationDeeplink.deeplink.startswith("bixby://"):
                    raise ValueError("Invalid validation URI")
    def check(value: Any) -> None:
        if isinstance(value, str) and PROHIBITED.search(value):
            raise ValueError("Prohibited URL or markup in output")
        if isinstance(value, dict):
            for key, item in value.items():
                check(key)
                check(item)
        elif isinstance(value, list):
            for item in value:
                check(item)
    check(response.model_dump())


def enforce_goal_format(goal_text: str, fallback_topic: str = "Device Issue") -> str:
    """Ensures goal matches: 'Follow these steps to perform this <Name> Troubleshooting.'"""
    cleaned = sanitize_text(goal_text)
    if GOAL_REGEX.match(cleaned):
        if not cleaned.endswith('.'):
            cleaned += '.'
        return cleaned
    
    # Extract topic from goal or use fallback
    topic = fallback_topic.strip()
    match = re.search(r'perform this\s+(.+?)(?:\s+Troubleshooting|\s+Configuration|$)', cleaned, re.IGNORECASE)
    if match and match.group(1).strip():
        topic = match.group(1).strip()
    else:
        # Clean topic
        topic = re.sub(r'^(Follow these steps to|perform this|Troubleshooting|Configuration)\s*', '', topic, flags=re.IGNORECASE)
        topic = topic.strip() or "Device Issue"

    # Normalize topic words
    words = [w.capitalize() for w in topic.split() if w]
    topic_str = " ".join(words[:4]) if words else "Device Issue"
    return f"Follow these steps to perform this {topic_str} Troubleshooting."


def enforce_title_word_count(title_text: str, fallback_topic: str = "Device Fix") -> str:
    """Ensures title is exactly 2 to 3 whitespace-separated words."""
    cleaned = sanitize_text(title_text)
    words = [w for w in cleaned.split() if w]
    if 2 <= len(words) <= 3:
        return " ".join(words)
    if len(words) > 3:
        return " ".join(words[:3])
    if len(words) == 1:
        return f"{words[0]} Troubleshooting"
    # Empty
    fallback_words = fallback_topic.split()
    if 2 <= len(fallback_words) <= 3:
        return " ".join(fallback_words)
    return "Device Issue Troubleshooting"[:28].strip()


def enforce_description_format(desc_text: str, action_name: str = "Settings") -> str:
    """Ensures action description is exactly 5 to 7 words and starts with 'It will'."""
    cleaned = sanitize_text(desc_text)
    
    # Strip any leading 'it will' to re-add cleanly
    cleaned = re.sub(r'^it will\s+', '', cleaned, flags=re.IGNORECASE).strip()
    
    words = cleaned.split()
    if not words:
        # Default 6-word phrase
        return "It will configure your device settings now"
    
    # We need 3 to 5 words following 'It will' (total 5 to 7 words)
    target_count = min(max(len(words), 3), 5)
    selected_words = words[:target_count]
    
    # Pad if fewer than 3 words
    padding = ["device", "settings", "now", "properly"]
    pad_idx = 0
    while len(selected_words) < 3 and pad_idx < len(padding):
        selected_words.append(padding[pad_idx])
        pad_idx += 1
        
    return f"It will {' '.join(selected_words)}"


def create_dummy_deeplink(screen_name: str = "Settings") -> Deeplink:
    """Creates a compliant bixby://dummy_positive placeholder."""
    clean_screen = " ".join((sanitize_text(screen_name) or "Settings").split()[:3])
    return Deeplink(
        deeplink="bixby://dummy_positive",
        description=enforce_description_format(f"open {clean_screen} settings screen"),
        message=f"Open {clean_screen} in device Settings",
        originalType="onClickURL"
    )


def sanitize_response(response: ContextDeeplinkResponse) -> ContextDeeplinkResponse:
    """Recursively validates and sanitizes all fields in ContextDeeplinkResponse."""
    for goal in response.contexts:
        # 1. Enforce goal string regex
        goal.goal = enforce_goal_format(goal.goal, goal.title)
        
        # 2. Enforce title word count (2-3 words)
        goal.title = enforce_title_word_count(goal.title)
        
        # 3. Clamp score in [0.0, 1.0]
        try:
            val = float(goal.score)
            if not math.isfinite(val):
                val = 0.85
            goal.score = round(max(0.0, min(1.0, val)), 2)
        except (TypeError, ValueError):
            goal.score = 0.85

        for action in goal.actions:
            # Clean actionName
            action.actionName = sanitize_text(action.actionName) or "Troubleshooting Step"
            
            # 4. Enforce description format (5-7 words, starts with "It will")
            action.description = enforce_description_format(action.description, action.actionName)
            
            for group in action.stepGroups:
                # Clean steps
                clean_steps = []
                for st in group.steps:
                    c = sanitize_text(st)
                    if c:
                        clean_steps.append(c)
                if not clean_steps:
                    raise ValueError("All source steps were removed by sanitization")
                group.steps = clean_steps
                
                # Check actionable deeplink
                if group.actionableDeeplink:
                    group.actionableDeeplink.description = sanitize_text(group.actionableDeeplink.description)
                    if group.actionableDeeplink.message:
                        group.actionableDeeplink.message = sanitize_text(group.actionableDeeplink.message)
                
                # An unsupported automatic action must never acquire a dummy.
                if action.category == actionCategory.auto and not group.actionableDeeplink:
                    raise ValueError("Automatic action lacks an approved catalog link")
                
                # Check validation deeplink
                if group.validationDeeplink:
                    group.validationDeeplink.key = sanitize_text(group.validationDeeplink.key)
                    if group.validationDeeplink.value:
                        group.validationDeeplink.value = sanitize_text(group.validationDeeplink.value)

    return response
