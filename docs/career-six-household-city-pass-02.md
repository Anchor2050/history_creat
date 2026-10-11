# Career-six household + city pass 02

Date: 2026-10-11

Branch: `chatgpt/career-six-cohort`

Status: **noncanonical structural replay pass**.

This pass follows `career-six-continuity-pass-01.md`. It keeps the v1 and v2 simulators available as regression baselines and adds `career_six_household_city_v3.py`.

The purpose is to replace two overly compressed objects:

1. “family pressure” as one scalar; and
2. “got a job” as one sector label.

The new object is a life decision made over a **household network × city bundle × career opportunity**.

## 1. Families are now networks

### Three only-child men

For Zhou Ye, Gao Yuan and Luo Cheng, the user-specified facts remain fixed:

- only child;
- parents were dual-income workers at the 2026 starting point;
- probability doctorate;
- zero public papers at the 2026 starting point.

V3 creates a father node and a mother node for each household. Their precise ages, retirement buffers and health trajectories are scenario variables. Because the men have no sibling node, there is no invented brother/sister who can absorb care by default.

This still does **not** mean the only child must return home or abandon a career. Paid care, parental retirement resources, housing security, job flexibility, city distance and the severity of actual health needs all affect the feasible set.

### Three women with two older brothers

For Tang Yu, He Xin and Song Nan, each of the two older brothers is now a separate scenario node with his own:

- age gap;
- city;
- income capacity;
- care willingness;
- partner/child load;
- relationship quality.

Two brothers therefore no longer equal “two units of free care.” One brother may live nearby but be heavily constrained by his own household; another may earn more but live far away; both may help, one may help, or practical substitution may remain weak.

The women’s parents’ employment history was not supplied by the user, so V3 does not freeze one. It remains an open scenario dimension.

## 2. Care is produced by bargaining and capacity

From 2030 onward, the yearly household update constructs:

- total parental care need;
- sibling substitution capacity, if siblings exist;
- paid-care substitution capacity;
- the focal actor’s residual care share;
- unmet care.

The focal person’s mobility then responds to the residual burden.

The important causal distinction is:

> family structure changes the **substitution set**; actual burden still depends on health, money, sibling lives, relationship quality and service access.

This prevents two symmetrical errors: assuming an only child automatically sacrifices the career, or assuming a daughter with two brothers automatically has no elder-care burden.

## 3. A career opportunity now produces a concrete offer

The v2 sequence was roughly:

`win scarce opportunity -> pass threshold -> employed in sector`.

V3 changes it to:

`win scarce opportunity -> pass qualification -> receive city-specific offer -> evaluate life bundle -> accept or reject`.

Every offer contains fictional replay parameters for:

- sector;
- city type;
- monthly gross pay;
- housing cost;
- daily commute;
- welfare / social-insurance continuity proxy;
- opportunity density;
- distance from the family anchor;
- contract security;
- time flexibility;
- relocation cost.

These numbers are **engineering priors**, not empirical salary estimates and not claims about real cities or employers.

## 4. City archetypes

V3 currently uses five fictional city bundles:

- `beijing_core`: high opportunity density and wage multiplier, high housing/commute and high family distance;
- `provincial_capital`: intermediate wage, housing and opportunity density;
- `regional_university_city`: cheaper and somewhat more flexible, with thinner outside options;
- `home_prefecture`: low housing and family distance, but much lower opportunity density;
- `pharma_cluster`: strong industry opportunity and pay, with higher housing and family distance.

A sector can generate several city bundles. “State-owned enterprise,” “public institution,” “faculty job” and “pharma” therefore no longer imply one geography.

This is important because the same person can rationally reject one SOE offer and accept another SOE offer without having changed values.

## 5. Three kinds of failure are now separate

V3 keeps three histories distinct.

### Qualification failure

The person got access to the relevant route but did not clear the competence / examination / fit threshold.

### Shared-capacity block

Another person consumed the scarce high-touch referral, mock interview or project slot first. The causal graph records the holder.

### Bundle rejection

The person qualified and received an offer, but the offer was not actually exercisable or attractive enough after housing, commute, family distance, care obligations, welfare continuity and future option value were charged against it.

This distinction matters for biography. Three people can all still be “job searching” in November while having arrived there through very different histories.

## 6. Household pressure can reprice an existing job

The 2032 and 2034 reassessment now sees the person’s actual employment bundle.

A previously acceptable job may become harder to exercise if:

- parental care need rises;
- sibling substitution weakens;
- paid care is insufficient;
- the job is geographically distant;
- time flexibility is low.

When family-distance pressure dominates, the person can search for a **closer version of the same career**. A target change is not mandatory.

When career satisfaction itself collapses, a sector change remains possible.

This separates “I no longer want this profession” from “I still want this profession, but this geography no longer works.”

## 7. Links to the original characters remain costly and bidirectional

V3 inherits continuity-v2’s rule that Lin Jing, Chen Lan and Xu Hang pay time pressure when they support the new cohort.

It also retains outcome back-propagation:

- public-sector / university-administration outcomes can make Lin Jing’s outside option more concrete;
- Song Nan’s industry outcome can strengthen Chen Lan’s health-data / industry network;
- Zhou Ye or Tang Yu outcomes can strengthen Xu Hang’s verification reputation.

A relationship can therefore impose early time cost and produce later option value. The return is neither immediate nor guaranteed.

## 8. Validation status

A dedicated test file now covers:

- exact fixed family structures from the user prompt;
- individual brother nodes rather than one sibling scalar;
- city-bundle fields;
- multiple cities for the same sector;
- a family-care gap that can make a won offer infeasible;
- the full 2026–2035 horizon;
- retained feedback to Lin / Chen / Xu;
- seed-dependent 2035 destinations;
- separation of qualification failure, capacity block and bundle rejection.

The repository checkout still cannot be cloned in the current execution environment because outbound DNS resolution fails. Therefore this pass does **not** claim that the repository test suite has been executed from a branch checkout.

The next run should execute the tests if a working checkout becomes available. Until then the committed tests are invariants, not a claimed green CI result.

## 9. What remains weak

Three major objects remain compressed.

### A. Money is still too static

Initial cash exists, but wages, rent, family transfers, savings, home purchase and job-loss buffers do not yet flow through a proper personal ledger. The city bundle therefore affects offer evaluation more strongly than it affects later wealth.

### B. Partners and children are still open blanks

That is correct as a starting principle, but by 2030–2035 some replay branches should contain partnership / child formation because these can change city mobility, care substitution and job flexibility. They must remain branches, not demographic obligations.

### C. Employers do not yet remember workers deeply enough

A job currently gives sector/city terms and later satisfaction. The employer should eventually remember reliability, refusal, client failures, teaching burden, management responsibility, layoffs, promotion and training decisions. That memory should change later re-entry and referral options.

## 10. Next high-value pass

The next structural pass should add a **personal cash / housing ledger** and connect it to household and city decisions.

In particular:

`salary -> rent / housing -> savings -> paid care capacity -> mobility -> job choice -> later earnings`

should become a closed causal loop.

Only after that loop exists should the branch spend heavily on selecting a literary “best world,” because otherwise family and city choices still lack one of their most important long-run state variables: accumulated money and housing lock-in.
