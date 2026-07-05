from .trigger_types import TriggerType


SUPPORTED_SOS_TRIGGERS = {
    TriggerType.TIMER_EXPIRED_NO_RESPONSE.value,
    TriggerType.SECRET_PHRASE_DETECTED.value,
    TriggerType.MANUAL_SOS_PRESSED.value,
}


def should_trigger_sos(trigger_type: str) -> bool:
    """Return whether a trigger type should create an SOS alert."""
    return trigger_type in SUPPORTED_SOS_TRIGGERS
