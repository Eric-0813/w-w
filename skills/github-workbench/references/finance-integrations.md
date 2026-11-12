# Financial integrations

Use this checklist when researching financial applications, broker connectors, or financial multi-agent repositories. Verify current maintainer and provider documentation; names and API eligibility change. It evaluates integrations rather than performing securities or portfolio analysis.

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

## Make the assessment reviewable

For each serious candidate, record the supported market/account/region, data source and access requirements, integration layer, and remaining setup. Tie capability claims to an implementation file or current provider documentation. Label evidence as documented, inspected in code, locally tested, or unverified; use a commit permalink for inspected code.

When useful, summarize the evidence in this compact table:

| Capability | Source / commit | Evidence level | Requirement or gap |
| --- | --- | --- | --- |
| Requested capability | Direct supporting link | Documented / inspected / tested / unverified | What is still needed |

Distinguish unavailable data from an observed zero. A missing connector, delayed feed, untested paper environment, or undocumented account requirement stays visible in the conclusion. End with the smallest experiment that can resolve the remaining integration uncertainty within the user's requested scope.
