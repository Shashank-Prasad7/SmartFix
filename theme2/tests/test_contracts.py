"""Unit tests for contract and formatting guarantees (G2-G5, A1-A2)."""
import re
import pytest
from theme2.src.sanitizer import (
    GOAL_REGEX,
    create_dummy_deeplink,
    enforce_description_format,
    enforce_goal_format,
    enforce_title_word_count,
    sanitize_response,
    sanitize_text,
)
from theme2.src.schema import (
    Action,
    ContextDeeplinkResponse,
    Deeplink,
    Goal,
    StepGroup,
    actionCategory,
)


def test_goal_regex_enforcement():
    valid1 = "Follow these steps to perform this Screen Damage Troubleshooting."
    valid2 = "Follow these steps to perform this Battery Optimization Configuration."
    
    assert GOAL_REGEX.match(valid1)
    assert GOAL_REGEX.match(valid2)

    # Broken goals should be corrected
    fixed1 = enforce_goal_format("Fix my broken screen please", fallback_topic="Screen Damage")
    assert GOAL_REGEX.match(fixed1)
    assert fixed1.endswith(".")


def test_title_word_count():
    assert enforce_title_word_count("Screen display damage") == "Screen display damage"
    # Too long
    assert enforce_title_word_count("My screen is completely black and dead") == "My screen is"
    # Single word
    assert enforce_title_word_count("Display") == "Display Troubleshooting"


def test_action_description_format():
    # Must start with "It will" and be 5-7 words
    desc1 = enforce_description_format("backup all your data now safely")
    words1 = desc1.split()
    assert desc1.startswith("It will ")
    assert 5 <= len(words1) <= 7

    desc2 = enforce_description_format("It will fix it")
    words2 = desc2.split()
    assert desc2.startswith("It will ")
    assert 5 <= len(words2) <= 7


def test_zero_url_leaks():
    dirty_text = "Visit http://samsung.com or https://example.com/help or www.test.com or send email to support@samsung.com [click here](http://evil.com) <a href='link'>link</a>"
    cleaned = sanitize_text(dirty_text)
    
    assert "http://" not in cleaned
    assert "https://" not in cleaned
    assert "www." not in cleaned
    assert ".com" not in cleaned
    assert "<a" not in cleaned
    assert "![" not in cleaned


def test_auto_action_deeplink_guarantee():
    # An auto action with null deeplink must be given a compliant dummy deeplink
    group = StepGroup(steps=["Step 1"], actionableDeeplink=None)
    action = Action(
        actionName="Configure Wifi",
        description="Configure Wifi",
        stepGroups=[group],
        category=actionCategory.auto
    )
    goal = Goal(
        goal="Follow these steps to perform this Network Troubleshooting.",
        title="Network Fix",
        actions=[action],
        score=0.9
    )
    resp = ContextDeeplinkResponse(contexts=[goal])

    sanitized = sanitize_response(resp)
    act = sanitized.contexts[0].actions[0]
    assert act.stepGroups[0].actionableDeeplink is not None
    assert act.stepGroups[0].actionableDeeplink.deeplink.startswith("bixby://")
    assert act.description.startswith("It will ")
    assert 5 <= len(act.description.split()) <= 7
