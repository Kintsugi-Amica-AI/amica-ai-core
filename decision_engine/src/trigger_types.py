from enum import Enum


class TriggerType(str, Enum):
    TIMER_EXPIRED_NO_RESPONSE = "timer_expired_no_response"
    SECRET_PHRASE_DETECTED = "secret_phrase_detected"
    MANUAL_SOS_PRESSED = "manual_sos_pressed"
