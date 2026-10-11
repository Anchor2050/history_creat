# SCK mixed-motive benchmark contract v1 — Joint Project under private costs

Status: `noncanonical`, `benchmark_contract`, written **before** any episode was run.
Authority: peer decision `runtime/message-bus/messages/2026-10-11-0021-peer-decision-stop-secretmafia-tuning-move-mixed-motive.json`.
Substrate: `narrative/longform/sck_joint_project_env_v1.py`.
Date: 2026-10-11.

## Why this is an own-authored substrate, and what that costs us

The peer allowed "one existing or minimal local structured mixed-motive environment".
An existing TextArena substrate was surveyed first
(`tools/probe_mixed_motive_envs.py`), and none satisfied the contract:

| candidate | runs in textarena 0.7.4? | usable? |
|---|---|---|
| `PublicGoodsGame` | yes | no hidden variable at all; symmetric endowments and full information, so the belief variants could not engage |
| `MarketEntryGame` | yes | same problem: public, fixed market capacity, no private signal |
| `BlindAuction` | **no** | has genuine private item valuations, but `reset` raises `TypeError: State.__init__() got an unexpected keyword argument 'min_players'` because it constructs `textarena.core.State` with `min_players`/`max_players`/`check_truncated`, which that constructor does not accept |
| `LetterAuction` | no | needs the NLTK `words` corpus, which the sandbox proxy blocks |
| `IteratedStagHunt` | no | needs numpy, not installed |

**This is weaker evidence than a third-party environment and every result from it must carry that label.**
The guards against a self-authored benchmark flattering SCK are: parameters fixed in this
document before running, a fixed alternative policy in every comparison, an explicit
mechanism gate, and a mechanism diagnostic for every claimed gain.

## Agents and information

- 4 agents, one episode = 8 rounds.
- Each agent has a **persistent private cost type** `c_i ∈ {1, 2, 4}` drawn i.i.d. at reset with
  public probabilities `(0.4, 0.4, 0.2)`. The distribution is public; the assignment is not.
- Agent `i` knows its own `c_i` and never learns another agent's `c_i` directly.
- Cost types persist for the whole episode, so they are **learnable** from observed
  behaviour. This is the hidden variable the belief layer is meant to calibrate on.

## Legal actions, phase by phase

Each round has two simultaneous phases:

1. **Pledge phase.** Each agent submits `[Pledge k]`, `k ∈ {0,1,2,3}`, publicly before acting.
   A pledge is a non-binding public statement of intended contribution.
2. **Contribution phase.** Each agent submits `[Contribute k]`, `k ∈ {0,1,2,3}`.

Submissions within a phase are simultaneous: an agent cannot see the current phase's other
submissions before making its own. All submissions in a phase are published together when
the phase closes, so round `r`'s pledges are visible before round `r`'s contribution choice.

## Outcomes and utilities

```
S            = sum of the four contributions this round
success      = (S >= threshold)                 threshold = 6
payoff_i     = (bonus if success else 0) - c_i * contribution_i     bonus = 6
```

- Joint surplus of a round = `sum_i payoff_i`.
- Per-agent utility = cumulative payoff over the 8 rounds.
- Social utility = sum of per-agent utilities.

Deliberate tensions built into the parameters, all fixed before running:

- **Under-contribution fails.** All-zero gives everyone 0.
- **Over-contribution destroys value.** `4 × 3 = 12` contributions cost `3·(c_i)` each while the
  bonus stays 6. With types `(1,1,4,4)` the plan `(3,3,0,0)` yields joint surplus 18, while
  `(3,3,3,3)` yields `4·6 − (3+3+12+12) = −6`. Reaching the threshold is not enough; the
  burden must land on cheap agents and stop at the threshold.
- **Some groups should refuse the project.** With types `(4,4,4,4)` any 6 units of contribution
  cost at least 24 against a 24 total bonus, so the best joint outcome is to contribute
  nothing. Whether to attempt the project at all therefore depends on the *believed* type
  composition, which no agent can observe. This is the central mixed-motive decision.

Because contributing is cheaper for low-cost agents, contributions are a **credible signal of
type** (a costly-signalling structure), and a high-cost agent has an incentive to misrepresent
its type in order to justify free-riding.

## Persistence, public records and accountability

- Cumulative payoffs persist across rounds.
- Every round's pledges, contributions, success flag and payoffs become **public record**.
- The environment maintains a public per-agent `pledges_kept` / `pledges_broken` count.
  A pledge is *broken* when the agent pledged `k` and contributed something other than `k`.
  Breaking a pledge is **not** directly fined: its cost is that other agents' beliefs about
  that agent's reliability fall, and reliability is part of what an agent must estimate to
  predict others' contributions. Reputation is therefore endogenous, not cosmetic.

## Observability

Public to every agent:

- round index, threshold, bonus, contribution range, type values and their probabilities;
- every pledge and every contribution after its phase closes;
- the round's success flag and the round's **aggregate surplus**;
- each agent's `pledges_kept` / `pledges_broken`.

Private to agent `i`:

- `c_i`, its own cost type;
- its own cumulative payoff.

Never available to any policy:

- other agents' cost types;
- per-agent payoffs;
- the full-information optimum, which is computed only during evaluation.

### Observability revision v1.1 — made before any episode was run

The first draft of this section published per-agent payoffs. Writing the tests
showed that this destroys the benchmark: `payoff_i = success·bonus − c_i·x_i`, and
with both `success` and `x_i` public, any observer recovers `c_i` in a single
division. The hidden variable would have become public after one contributing
round, and the belief layer would have had nothing to infer — the same class of
mistake that made the SecretMafia belief channel inert.

Per-agent payoffs and per-agent cumulative payoffs are therefore **private**, and
only the aggregate surplus is published. That leaves one linear equation per round

```
sum_i c_i * x_i  =  success * bonus * num_agents  -  total_surplus
```

so the hidden types remain learnable but genuinely uncertain: the candidate space
is `|{1,2,4}|^4 = 81` vectors, pruned by each round's equation. The inference is
front-loaded — with varying contribution vectors the true vector is usually
narrowed sharply within a few rounds, and the earliest rounds are exactly where the
"attempt the project or refuse it" decision bites. `tests/test_sck_joint_project_env_v1.py`
verifies that the true vector always survives, that the candidate set shrinks after
the first informative round, and that it never grows.

No parameter in the "Agents and information", "Legal actions", "Outcomes and
utilities" or "Persistence" sections changed, and no episode had been run when this
revision was made.

## Evaluation-only quantities

- **Full-information optimum**: `max` over all `4^4` contribution vectors of the round's joint
  surplus given the *true* types. Used for the efficiency metric. Brute-forced, so it is exact.
- **Joint-surplus efficiency** = achieved joint surplus ÷ full-information optimum, per round and
  aggregated. Rounds where the optimum is 0 or negative are reported separately rather than
  folded into a ratio.
- **Pareto-optimal rounds**: rounds whose achieved joint surplus equals the optimum.
- **Per-agent regret** is computed only against a legitimate post-hoc counterfactual: the best
  contribution given the round's *realised* other-agent contributions and the agent's own type.
  It is a secondary diagnostic, exactly as peer decision 0016 Q5 requires, and never the
  acceptance metric.
- **Belief calibration**: Brier score of each agent's belief distribution over every other
  agent's true cost type.
- **Voluntary type disclosure**: count of utterances that state the speaker's own cost type.
  Here this is deliberate strategic signalling, not a leak, because the cost type is the only
  private fact and disclosing it is a legal strategic choice. Protected-fact leakage in the
  agreed sense is therefore reported as structurally zero for this substrate and labelled as
  such rather than presented as an achievement.

## Ablation and metrics

Variants `plain`, `memory`, `belief`, `belief_planning` from `storybox_sck_eval_v0.py`, plus at
least one **fixed alternative policy** that does not learn, so every comparison has a
non-adaptive opponent.

Primary questions and metrics, per peer decision 0021:

1. per-agent and social utility;
2. joint-surplus efficiency and Pareto-optimal round count;
3. belief calibration on the hidden cost types (Brier);
4. pledge violations and the reputation record;
5. information leakage, with the structural-zero caveat above;
6. robustness against the fixed alternative policy in a mixed table.

**Mechanism gate.** Any apparent utility gain must be attributed to an interpretable mechanism —
better type inference, contingent contribution, credible commitment, opponent adaptation, or
burden allocation — and not to a deterministic symmetry, tie-break or mirrored-policy artifact.
This gate exists because the SecretMafia cross-play gain turned out to be exactly such an
artifact (bloc voting by two mirrored agents).

## Held

MCTS, bi-level search, the deferred meta-game/institutional-awareness runtime, the deferred Peak
Play runtime, and SCK-to-risk-list-hospital-Scene reconnection all remain held until this
substrate shows a mechanism-attributable gain.

## Honesty clauses

- Parameters in this document were fixed before the first episode. Any later parameter change
  must be recorded as a new contract version with its reason, never edited in place.
- A negative result here is a valid outcome and must be reported as such.
- Results from an own-authored substrate are labelled as such wherever they are cited.
