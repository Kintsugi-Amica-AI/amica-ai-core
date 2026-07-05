from typing import Any

from .alert_rules import should_trigger_sos


def evaluate_trigger(trigger_type: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate a safety trigger and return a mobile/backend friendly result."""
    trigger_sos = should_trigger_sos(trigger_type)

    return {
        "trigger_sos": trigger_sos,
        "trigger_type": trigger_type,
        "priority": "high" if trigger_sos else "normal",
        "context": context or {},
    }
