# First long-goal result: endogenous social causality

Branch: `chatgpt/endogenous-social-topology`

## Goal

The first long work unit was accepted only if a 4-world x 160-week controlled
pilot could produce at least three explicit cross-actor causal chains where an
earlier choice changed another actor's feasible options. At least one chain also
had to return after >=26 weeks, and personal cash could not go negative anywhere
along the simulated path.

## What was built

- `consequence_topology.py`: shared scarce resources, institutional memory,
  domain-specific reputation, actor entry/exit state, causal traces.
- `social_engine.py`: scenario-consistent cash flow, household care/time burden,
  frozen same-period actor views, restricted communication.
- `world_social_adapter.py`: transactional connection to the existing World
  Ledger and permissions; failed cash/resource operations roll back both layers.
- `topology_pilot_v2.py`: corrected controlled 160-week pilot with explicit
  counterfactual checks.
- tests covering capacity, causality, frozen views, information paths, World
  integration, rollback, lifecycle and long-horizon acceptance.

## Important failed attempt

The first pilot was rejected even though it reported three chains per world.

Audit found two design errors:
1. its household cash process could drive Chen Lan far below zero;
2. some claimed competition was structurally prearranged rather than verified by
   a counterfactual change in another actor's option set.

The original entry point is now a compatibility wrapper around v2 so the flawed
logic cannot silently become the canonical pilot.

## Corrected pilot

Seeds: 101, 202, 303, 404.
Horizon: 160 weeks each.

A chain qualifies only when:
- at least two actors are involved;
- the causal graph contains at least two explicit nodes;
- the downstream option exists in the counterfactual without the upstream
  allocation and disappears with the upstream allocation.

The corrected pilot produces four structural chain types:

1. **Admin displacement**
   Chen's household load can create a real need for the one active administrative
   exception slot. If she receives it first, Lin's later request is unavailable.

2. **Recommendation displacement**
   Lin's earlier application can consume a one-cycle priority recommendation,
   changing Chen's feasible job-search route.

3. **Feedback paid-work collision**
   Chen responds to the blocked recommendation by accepting bounded paid work.
   That consumes the same project-hour pool from which she later refers Lin,
   producing a Lin -> Chen -> Lin feedback loop.

4. **Delayed institutional-memory echo**
   The blocked referral is retained as Mingheng institutional memory and returns
   32 weeks later as a reason for a new opportunity.

## Formula-equivalent local execution

The sandbox still cannot import the GitHub branch directly, so the corrected
pilot formulas were executed locally in an equivalent audit script. This is not
claimed as a full repository unittest run.

Observed structural result:

| seed | admin chain | recommendation chain | feedback chain | delayed echo | minimum cash stays >= 0 |
|---:|:---:|:---:|:---:|:---:|:---:|
| 101 | yes | yes | yes | yes | yes |
| 202 | yes | yes | yes | yes | yes |
| 303 | yes | yes | yes | yes | yes |
| 404 | yes | yes | yes | yes | yes |

Minimum cash seen in the audit remained positive. The tightest path was Xu Hang,
ending near 3270 in the formula-equivalent run; Chen Lan's minimum remained above
roughly 5000 across the four seeds before post-graduation income improved the
buffer.

## Judgment

**This long-goal acceptance criterion passes at the mechanism level.**

The important improvement is not the count of chains. The system now supports a
real causal pattern:

> one actor consumes scarce capacity -> another actor loses an option -> the
> second actor chooses an alternative -> that alternative changes a shared pool
> -> the consequence returns to the first actor or a third actor later.

That was absent from the previous pressure-history model.

## What this does not prove

This is still a controlled pilot and remains noncanonical fiction. It does not
show that unconstrained 32 x 160 simulation will spontaneously produce
masterpiece-scale histories. The next work unit should remove more hand-scheduled
collision timing and let lifecycle, organizations, family obligations and
network transmission generate those collisions endogenously.
