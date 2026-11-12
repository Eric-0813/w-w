# Native haptics versus web animation

Use this reference when researching physical button feedback or tactile interfaces.

A CSS press effect or sound is not physical haptic feedback. Verify current support for the target device, OS, browser, or native wrapper. An iOS-native haptics bridge may be required even when the existing app is web-based. Check plugin APIs and installation requirements rather than presenting an unsupported browser call as working vibration.

Tie feedback to precise events: button pressed, request accepted, report ready, order submitted, order filled. Never signal a fill merely because a request was sent. Report whether behavior was inspected in source, simulated, or tested on the actual phone. No actual device test means the physical feel remains unverified.
