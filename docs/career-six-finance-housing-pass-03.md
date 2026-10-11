# Career-six finance + housing pass 03

Date: 2026-10-11

Branch: `chatgpt/career-six-cohort`

Status: **noncanonical structural replay pass; financial priors not yet calibrated**.

This pass follows the household/city pass and adds `career_six_finance_housing_v4.py`.

Its purpose is to close the loop:

`job bundle -> monthly cash flow -> housing / care affordability -> mobility -> later job bundle`.

## 1. Money now moves through the existing Ledger

V4 reuses `narrative/longform/ledger.py` rather than inventing a second accounting system.

For each of the six new characters the ledger starts from the exact cash value already present in the scenario. It then uses explicit external/sink accounts for:

- employment income;
- living expenses;
- rent / mortgage / secondary rent;
- paid elder care;
- relocation and housing purchase.

The ledger enforces non-negative balances and double-entry conservation. If a person cannot pay the full modeled monthly cost, V4 pays only the available amount and records the remainder as an explicit `monthly_expense_unmet` event.

Thus poverty pressure cannot be created by allowing an account to silently go negative.

## 2. City choice now changes later wealth

After a job is accepted, the housing state follows the work city.

A renter moving to a new city starts paying that city bundle's rent prior.

A homeowner who later works in another city can carry both:

- the old-city mortgage; and
- new-city rent.

That carry cost enters later offer evaluation.

This creates a path by which an early apparently reasonable housing choice can reduce later mobility without treating home ownership as inherently good or bad.

## 3. Home purchase is conditional, not a life-stage script

V4 only considers purchase in 2031, 2033 and 2035.

A purchase requires:

- employment;
- sufficient cash for the modeled down payment plus a buffer;
- adequate job stability;
- a stochastic branch that depends partly on stability, housing security and remaining mobility.

If purchased:

- the down payment leaves the personal cash account;
- mortgage cost begins in later months;
- equity accumulates approximately through modeled principal repayment;
- mobility falls through a lock-in parameter.

No character is required to buy a home by a certain age.

## 4. Housing lock-in can change a later offer decision

V4 extends the v3 offer evaluation.

If a character owns a mortgaged home in City A and considers an offer in City B, the evaluation charges:

- ongoing mortgage carry cost;
- a lock-in penalty;
- the new city's housing bundle.

If the offer remains good enough, it can still be accepted. If not, the same sector opportunity may become non-exercisable even though the person is qualified.

This produces a useful long-horizon mechanism:

`early stability -> home purchase -> later family/career shock -> expensive mobility -> changed feasible set`.

## 5. Care and money now feed each other

The v3 household layer used cash as one input to paid-care capacity.

V4 updates cash every month, so later household updates see the accumulated result of prior employment and housing history.

The loop is therefore:

1. work produces income;
2. city and housing consume income;
3. savings determine part of paid-care capacity;
4. paid care changes residual family burden;
5. family burden changes mobility;
6. mobility and housing lock-in change later offer feasibility;
7. later work changes income again.

This is the first pass in the six-person branch where cash, housing, care and career are mechanically coupled over multiple years.

## 6. Important unresolved issue: doctoral / search income

The user supplied initial cash, family structure, field and initial career goals for the six people, but did **not** supply recurring doctoral stipends, family monthly transfers, scholarships, unemployment support or temporary-work income.

V4 therefore does not silently invent those streams. In its current form, pre-employment people live from the supplied initial cash buffer until employment income begins.

That is useful as a stress-test prior, but it is **not** suitable as an empirical claim about doctoral living standards and must not be used to conclude that a character is poor, dependent or forced into a job in canon.

Before financial outcomes are promoted into a literary trunk, the branch should add an explicit scenario layer for:

- doctoral stipend / scholarship;
- possible family transfers;
- temporary teaching / research / freelance income;
- post-graduation search support;
- taxes and social-insurance deductions.

Those should be scenario variables with provenance, not facts inferred from gender or family background.

## 7. Validation status

A dedicated v4 test file checks:

- exact initial cash accounts;
- partial payment without negative cash;
- money conservation across the ledger;
- monthly finance rows through 2035;
- housing lock-in entering later offer evaluation;
- conditional home purchase;
- equity / lock-in state after purchase;
- persistence of feedback to Lin Jing, Chen Lan and Xu Hang.

The current environment still cannot clone the GitHub repository because outbound DNS resolution fails. The tests are committed as invariants but are **not claimed to have run from a repository checkout**.

## 8. Historical meaning

The important object added by this pass is **option value financed through time**.

A high salary can buy care capacity but can also come with expensive housing and geographic distance. A cheaper city can release cash but reduce professional re-entry density. A home can stabilize one decade and make a later move expensive. A family burden can be partly purchased away, but purchasing care consumes the same cash buffer that supports relocation or unemployment.

The model therefore has a route for the same yuan to compete across:

- present consumption;
- housing;
- elder care;
- unemployment buffer;
- relocation;
- future career option value.

That is closer to the branch's central historical question than a single income or happiness score.

## 9. Next high-value pass

The next pass should not add more dramatic events yet.

It should first add an explicit **pre-employment income scenario** and then run a multi-seed audit asking:

- which conclusions disappear once doctoral/search income is varied;
- which housing purchases are robust versus artifacts of a cash prior;
- whether only-child versus two-brother differences survive after money and paid care are varied;
- whether some city/career outcomes are being driven by hard-coded thresholds rather than genuine causal interaction.

Only mechanisms robust to that audit should move closer to the branch's historical trunk.
