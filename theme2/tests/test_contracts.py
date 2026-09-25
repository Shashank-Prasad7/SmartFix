"""Unit tests for contract and formatting guarantees (G2-G5, A1-A2)."""
import pytest
from pydantic import ValidationError

from theme2.src.sanitizer import (
    GOAL_REGEX,
    enforce_description_format,
    enforce_goal_format,
    enforce_title_word_count,
    sanitize_response,
    sanitize_text,
    validate_response,
)
from theme2.src.schema import (
    Action,
    ContextDeeplinkResponse,
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
    # Missing catalog evidence must not manufacture a dummy deeplink.
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

    with pytest.raises(ValueError, match="approved catalog link"):
        sanitize_response(resp)


def _valid_response():
    return ContextDeeplinkResponse(contexts=[Goal(
        goal="Follow these steps to perform this Screen Repair Troubleshooting.",
        title="Screen Repair", score=0.5,
        actions=[Action(actionName="Restart device", description="It will guide the device restart",
                        stepGroups=[StepGroup(steps=["Press Power for 20 seconds."])],
                        category=actionCategory.manual)],
    )])


@pytest.mark.parametrize("field,value", [
    ("goal", "Follow these steps to perform this Screen Repair Troubleshooting"),
    ("title", "One"),
    ("score", float("nan")),
    ("score", -0.1),
    ("score", 1.1),
])
def test_success_mutations_are_rejected_at_goal_level(field, value):
    response = _valid_response()
    setattr(response.contexts[0], field, value)
    with pytest.raises(ValueError):
        validate_response(response)


@pytest.mark.parametrize("description", [
    "Configure your device now", "It may guide the device restart",
    "It will restart", "It will guide the device restart procedure safely today",
])
def test_success_mutations_are_rejected_at_action_level(description):
    response = _valid_response()
    response.contexts[0].actions[0].description = description
    with pytest.raises(ValueError):
        validate_response(response)


@pytest.mark.parametrize("field", ["contexts", "actions", "stepGroups", "steps"])
def test_success_mutations_are_rejected_for_empty_lists(field):
    response = _valid_response()
    if field == "contexts":
        response.contexts = []
    elif field == "actions":
        response.contexts[0].actions = []
    elif field == "stepGroups":
        response.contexts[0].actions[0].stepGroups = []
    else:
        response.contexts[0].actions[0].stepGroups[0].steps = []
    with pytest.raises(ValueError):
        validate_response(response)


def test_official_schema_rejects_extra_diagnostic_fields():
    payload = _valid_response().model_dump()
    payload["trace"] = {"request_id": "secret"}
    with pytest.raises(ValidationError):
        ContextDeeplinkResponse.model_validate(payload)


@pytest.mark.parametrize("fragment", [
    "https://example.org/help", "www.example.net", "example.com",
    "example.html", "[support](https://example.org)",
    "![photo](https://example.org/a.png)", "<a href='x'>support</a>",
    "<img src='x'>",
])
def test_official_validator_rejects_prohibited_fragments(fragment):
    response = _valid_response()
    response.contexts[0].actions[0].stepGroups[0].steps[0] = f"Press Power. {fragment}"
    with pytest.raises(ValueError, match="Prohibited"):
        validate_response(response)
