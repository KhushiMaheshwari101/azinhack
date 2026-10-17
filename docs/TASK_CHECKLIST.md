# ReadyCheck task checklist

## Product and user research
- [ ] Interview 3–5 shoppers about unresolved refund/replacement cases.
- [ ] Pick one narrow journey and define what counts as a successful audit.
- [ ] Do not collect real complaint documents for the hackathon demo.

## TinyFish
- [ ] Confirm API key and wallet status before live runs.
- [x] Use Search restricted to the company domain.
- [x] Fetch candidate policy/contact pages first.
- [x] Invoke Agent only when static fetch/extraction fails.
- [x] Keep max steps/time bounded and display live vs demo mode clearly.

## ML / evidence
- [ ] Label page types for evaluation.
- [ ] Measure extraction precision/recall per field.
- [x] Check every displayed value appears in its quote.
- [x] Report uncertain or missing values as unclear; never invent them.
- [x] Keep checklist rules explainable and reviewed.

## Product polish
- [x] Add result freshness timestamp and checked source list.
- [x] Allow editing/copying the complaint draft.
- [x] Add loading, timeout, empty, rate-limit, and provider-error states.
- [x] Add accessible labels and keyboard navigation.
- [x] Prepare a short demo script and sample domain.

## Before real users / production
- [ ] Authentication and per-user case isolation.
- [ ] Encrypted private file storage and deletion workflow.
- [ ] Retention, privacy notice, consent, and legal review.
- [ ] API rate limits, SSRF protections, spend caps, monitoring, backups.
- [ ] Security review and tested disaster recovery.
