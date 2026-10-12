# Financial integrations and tactile interfaces

Use this checklist only when the repository research concerns financial applications or native button feedback. Verify current maintainer and provider documentation; names and API eligibility change.

## Identify the integration layer

Distinguish market/news data, social discussion data, account/position access, order submission, order status, and settlement. A market-data SDK does not imply broker access. A connector for one broker does not control other finance apps installed on the phone.

For an IBKR candidate, distinguish TWS/IB Gateway socket integration from Web API access and third-party customer onboarding. Check the requirements for the intended account and region in current official documentation. Do not treat a personal-account prototype as evidence that a public multi-user app has been approved.

For other brokers, record official versus community SDK status, authentication method, read-only capability, paper versus live environments, and relevant data entitlements. Do not represent source availability as an account connection. Account access must be configured through an authorized path; research does not authorize retrieving brokerage credentials or sending portfolio data to an AI provider.

## Financial multi-agent candidates

Look for the actual data connectors and provenance handling, not merely analyst role prompts. Evaluate:

- Timestamp, publication time, exchange timezone, freshness, and missing-source behavior.
- Corporate actions, currencies, numerical calculations, and deterministic checks.
- Duplicate news, unverified social claims, and separation of sentiment, attention, and credibility.
- Exposure-aware relevance to actual holdings, including indirect sector and supply-chain effects.
- Point-in-time data integrity, fees, slippage, and look-ahead leakage when evaluating backtests.
- Separate order proposal, risk checks, user authorization, submission, and broker-confirmed outcome.

Do not equate analyst agreement, confidence wording, GitHub popularity, or backtest results with future returns. For a first prototype, read-only or paper-mode integration often provides the most useful validation without requiring live transactions. Honor the user's requested scope rather than universally prohibiting legitimate execution features.

## Native haptics versus web animation

A CSS press effect or sound is not physical haptic feedback. Verify current support for the target device, OS, browser, or native wrapper. An iOS-native haptics bridge may be required even when the existing app is web-based. Check plugin APIs and installation requirements rather than presenting an unsupported browser call as working vibration.

Tie feedback to precise events: button pressed, request accepted, report ready, order submitted, order filled. Never signal a fill merely because a request was sent. Report whether behavior was inspected in source, simulated, or tested on the actual phone. No actual device test means the physical feel remains unverified.
