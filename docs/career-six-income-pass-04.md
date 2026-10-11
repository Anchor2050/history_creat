# Career-six explicit income pass 04

Date: 2026-10-11

Branch: `chatgpt/career-six-cohort`

Status: **noncanonical sensitivity layer**.

This pass resolves the largest limitation recorded in `career-six-finance-housing-pass-03.md`: pre-employment income is no longer silently treated as zero.

## What changed

A new scenario file, `docs/scenarios/career-six-income-priors-v1.json`, makes the following uncertain streams explicit:

- doctoral stipend / scholarship income;
- family monthly support;
- post-graduation search-period support;
- temporary work during doctoral and search stages;
- employment net-pay share.

All values remain fictional engineering priors pending empirical calibration.

The family-support range is intentionally shared across all six people. Gender, only-child status and having two older brothers do not directly determine the amount.

`narrative/longform/career_six_income_v5.py` draws one auditable income profile per actor and seed, stores those profiles in every run, and routes every income stream through the same double-entry ledger used by the finance/housing pass.

## Why this matters

The branch can now distinguish two very different histories that previously looked identical:

1. a person accepts a job because the job bundle itself is attractive;
2. a person accepts the same job because a weak pre-employment cash buffer makes continued search difficult.

Likewise, home purchase or paid elder care can now be tested for robustness to stipend/support assumptions.

The intended audit question is no longer “what happened under one cash prior?” It is:

> Which career, housing and care mechanisms survive when plausible pre-employment income streams vary?

## Sensitivity output

V5 includes `summarize_income_sensitivity` as a compact diagnostic. Across supplied seeds it records:

- home-purchase counts by actor;
- months with unmet modeled expenses;
- number of distinct final sector/city destinations;
- offer-rejection counts.

The summary is explicitly marked `noncanonical`. It does not rank lives and does not select a literary winner world.

## Validation status

A dedicated test file checks:

- no gender/sibling rule is encoded into family-support amounts;
- all six actors receive explicit income profiles;
- profiles vary by seed;
- stipend/family/search/temporary-work pools are explicit ledger accounts;
- doctoral months can receive stipend before employment;
- total money remains conserved within the modeled ledger;
- income priors remain visible in run output;
- the sensitivity summary cannot present itself as canonical selection.

The current execution environment still cannot clone the repository because outbound DNS resolution fails. These tests are committed invariants; this pass does **not** claim they have run from a branch checkout.

## Current architecture after four passes

The six-person branch now contains a causal path of the following form:

`doctoral income / family support`

`-> cash buffer`

`-> ability to keep searching / relocate / buy paid care`

`-> competition for scarce career preparation or recommendation`

`-> qualification outcome`

`-> city-specific job offer`

`-> wage + housing + commute + welfare + family distance`

`-> accept / reject`

`-> monthly saving or hardship`

`-> parental care substitution + sibling bargaining`

`-> housing purchase or continued renting`

`-> geographic lock-in`

`-> 2032/2034 career reassessment and re-entry`

`-> feedback into Lin Jing / Chen Lan / Xu Hang's own option networks`.

This is substantially more entangled than the original independent-score scout.

## Next gate

The next useful step is an executed multi-seed audit once a runnable checkout is available. That audit should attack, rather than celebrate, the current architecture.

In particular it should ask whether:

- only-child characters are still mechanically accumulating more care burden after paid care and income vary;
- two-brother families are being granted unrealistically cheap substitution;
- home purchase dominates outcomes because of an arbitrary down-payment formula;
- public-sector scarcity is too concentrated in one synthetic slot;
- high-opportunity cities are being penalized or rewarded too strongly by hard-coded bundle weights;
- the original characters' time costs are large enough to alter their own long-run paths rather than merely add a small bookkeeping penalty.

No current result should enter the branch's literary trunk until it survives that adversarial sensitivity pass.
