from decision_engine.src.decision_engine import evaluate_trigger
from decision_engine.src.trigger_types import TriggerType


def test_manual_sos_pressed_triggers_alert() -> None:
    result = evaluate_trigger(TriggerType.MANUAL_SOS_PRESSED.value)

    assert result["trigger_sos"] is True
    assert result["priority"] == "high"


def test_unknown_trigger_does_not_trigger_alert() -> None:
    result = evaluate_trigger("unknown")

    assert result["trigger_sos"] is False
    assert result["priority"] == "normal"
