# 08 · From clean public data to dirty data with a real user

## Why

The Scania files are public, documented and already split. Real work is different: data arrives late, from several systems, with broken units, duplicated assets, free text and a person who owns the decision and changes their mind. This document is the plan to prove the same method under those conditions without weakening the evidence already in this repository.

## Principle

Each track adds realism, and each keeps the rules of phases 1–7: a written problem contract, data checks before modelling, one sealed evaluation, and claims limited to what the evidence supports. Synthetic data is always labelled synthetic; partner data is never published raw.

## Three tracks (from fastest to strongest)

| Track | Data | User | Realism | Time | Proves |
|---|---|---|---|---|---|
| **A · Stress test** | Scania data with injected real-world defects | Simulated (written persona) | Medium | 1 week | The pipeline detects and survives dirty inputs |
| **B · Public dirty data** | Real, messy public vehicle-safety records | Public question, interviewed practitioner | High | 3–4 weeks | Cleaning, linking and free text on data nobody prepared |
| **C · Real partner** | A company's own maintenance or quality records | A named decision owner | Highest | 6–10 weeks | Requirements, privacy, iteration and adoption |

### Track A · Stress test the current pipeline

Inject the defects that real fleet data shows, one at a time, into copies of the data. The frozen model and threshold are never changed. Results are descriptive.

| Defect | How it is injected | What should catch it |
|---|---|---|
| Sensor dropout blocks | Whole histogram families set to missing for 5–30 % of trucks | SQL contract (missing-rate bound); cost impact report |
| Unit or scale change | One counter multiplied by 1,000 or reset to zero | Contract range checks on per-feature quantiles |
| Duplicate assets | 2 % of rows duplicated with small noise | Contract duplicate check |
| Mixed missing markers and decimals | `na`, `N/A`, `-`, empty, `1.234,5` | Parser fails loudly, never silently coerces |
| Schema drift | Column renamed, column added, order shuffled | Contract column-set check; API rejects unknown readings (already done) |
| Label delay and noise | 10 % of failures recorded as healthy | Cost-bound report: how much of the cost is label noise |
| Prevalence shift | Failure rate moved from 1.7 % to 4 % | Workshop-load alert outside 41–48 checks per 1,000 |

Deliverables: `aps_intel.stress`, new contract checks, `docs/09_stress_test.md` with the cost of each defect, and a monitoring rule for the service.

### Track B · Public data that nobody cleaned

Candidate sources, same domain (vehicle air brakes and maintenance). Access, licence and size must be confirmed before starting:

- **NHTSA vehicle complaints and recalls (ODI):** free-text complaints with component codes, including air-brake systems. Duplicates, typos, inconsistent vehicle models.
- **FMCSA roadside inspection violations:** brake-related out-of-service violations by carrier and date. Codes change over time; carriers appear under several names.
- **Mexican open data (datos.gob.mx):** check for federal transport inspection or fleet records; useful for local relevance if a usable set exists.

Question to answer, framed with a practitioner (see interview guide): *which brake-related complaints or violations signal a systemic problem early enough to plan inspections?* Here the work is linking records, normalising entities, extracting signal from text and handling time. Modelling is a small part.

### Track C · A real partner with real records

Target partners: a fleet operator, a transport company, a maintenance workshop or a manufacturing quality department, where an ISO 9001 audit network gives natural access. Typical data: work orders, maintenance logs, nonconformity and corrective-action records (CAPA), telematics exports, all mostly in Excel.

| Step | Output | Evidence published |
|---|---|---|
| 1. Framing interview (60 min) | Decision, decision owner, cost of each error, success metric in their units | Problem contract (anonymised) |
| 2. Data request | Checklist below; sample extract first | Data dictionary (no values) |
| 3. Legal and privacy | NDA and data-processing agreement; Mexican personal-data law (LFPDPPP; confirm the current version with the partner's counsel) | Statement of what may be published |
| 4. Anonymisation | Hash asset and person IDs, drop names, shift dates, bucket locations, remove free-text personal data | Anonymisation protocol and checks |
| 5. Data contract and audit | Defects found, how each was resolved, owner sign-off | Audit report with counts only |
| 6. Model and decision | Same phase discipline; sealed evaluation on the latest period | Metrics agreed with the owner |
| 7. Pilot and feedback | Two-week shadow run: the model recommends, the person decides | Feedback log, decision log |
| 8. Publication | Code, a synthetic replica with the same schema and defect profile, aggregated results approved by the partner | Repository and case study |

**Collaboration evidence.** With the partner's permission, requirements and feedback are recorded as GitHub issues and discussions, changes go through reviewed pull requests, and acceptance criteria are signed off. This is the evidence that a public dataset cannot produce.

## Templates

**Framing interview guide**
1. What decision do you make today, how often, and who makes it?
2. What does a missed failure cost you? What does an unnecessary inspection cost? (time, parts, downtime, penalties)
3. How do you decide today, and what would make you trust a recommendation?
4. Which records exist, where, since when, and who maintains them?
5. What would success look like in three months, in your own units?
6. What must never happen (a safety-critical miss, an unexplainable recommendation)?

**Data request checklist**
- Asset list with stable IDs, model, age and usage.
- Event history: failures, repairs and inspections with dates and component codes.
- Readings or telematics, with units and sampling frequency.
- Known data problems, system changes and their dates.
- A sample of 100 rows before the full extract.

**Acceptance criteria (agreed before modelling)**
- Primary metric and target in the partner's units.
- Maximum workshop load the operation can absorb.
- Required explanation per recommendation.
- Evaluation period kept sealed until the final run.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| No partner available | Run Tracks A and B; they stand alone as portfolio evidence |
| Partner forbids publication | Publish method, synthetic replica and anonymised metrics only, as agreed in writing |
| Personal data in free text | Automatic and manual redaction before any data leaves the partner |
| Data too small or inconsistent | Report it honestly as a data-readiness finding; that is a valid deliverable |
| Scope creep | Problem contract signed at step 1; changes go through issues |

## Plan

1. **Weeks 1–2, Track A:** done ([09](09_stress_test_and_monitoring.md)): stress-test module, monitoring rule and report. Duplicate-key check waits for a real asset ID.
2. **Weeks 2–5, Track B:** one public source, entity cleaning and text pipeline, one practitioner interview.
3. **Weeks 4–12, Track C:** approach 3–5 companies, sign one, follow the eight steps, publish the case study.
