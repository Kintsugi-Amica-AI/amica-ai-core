# Decision Engine Flow

1. Receive a trigger type from mobile, backend, or AI module.
2. Validate the trigger against supported SOS triggers.
3. Return a decision with priority and context.
4. Backend creates the SOS alert when `trigger_sos` is true.
