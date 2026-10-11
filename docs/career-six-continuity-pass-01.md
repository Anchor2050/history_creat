# Career-six continuity pass 01

Date: 2026-10-11

Branch: `chatgpt/career-six-cohort`

Status: **noncanonical structural replay pass**.

This pass preserves the original `career_six_2035.py` baseline and adds `career_six_continuity_v2.py` as a stronger continuation layer. The purpose is to repair three structural weaknesses before doing more literary replay.

## 1. Problem found: 2029–2031 could become dead time

The baseline only ran first-job cycles in 2026, 2027 and 2028. A character who remained unemployed after 2028 could then sit in `search` until the 2032 re-entry mechanism. That gap is too artificial for a long-horizon life history.

V2 therefore keeps annual high-stakes job cycles running through 2031. Repeated failure and capacity exclusion accumulate separately. Either can contribute to a later career-target revision, but no character is forced to abandon the original target after a fixed number of failures.

The 2026 target remains historical memory in `target_2026`; `current_target` may change at most twice under accumulated pressure in this pass.

## 2. Shared opportunities now create cross-person causal chains

The high-touch public-sector mock/interview resource has capacity one in V2. This does not mean only one person in the world can prepare for public-sector recruitment. It represents one scarce, high-quality tailored slot inside this small social network.

When one actor receives the slot, another actor seeking the same resource can be blocked. The blocked event stores the holder and takes the holder's allocation node as an explicit cause. This produces a real graph of the form:

`A receives scarce slot -> B loses that slot this cycle -> B's search pressure changes -> B may later revise target`.

This is materially different from two independent career scores moving in parallel.

## 3. Interaction with the original cast now has a cost

The baseline made cross-cohort interactions expand the original characters' networks and outside options. That made mentoring/networking too close to a free benefit.

V2 adds `time_pressure` to Lin Jing, Chen Lan and Xu Hang. Every substantive cross-cohort exchange that helps a new actor also consumes a small amount of the original actor's discretionary capacity.

Successful new-character outcomes can then propagate back positively:

- Gao Yuan / He Xin / Luo Cheng can make Lin Jing's public-sector option more concrete;
- Song Nan can strengthen Chen Lan's health-data / industry translation network;
- Zhou Ye / Tang Yu can strengthen Xu Hang's verification reputation.

The same relationship can therefore create both burden and later option value.

## 4. Isolated smoke result

The GitHub checkout still cannot be cloned in the current execution environment because outbound DNS resolution fails. Therefore this document does **not** claim that the repository test suite has run from the branch checkout.

The V2 module was syntax-checked, then executed in an isolated formula-equivalent smoke harness with the same six actor identities, targets, readiness rules and a minimal compatible consequence-topology implementation.

Observed smoke results:

| seed | 2029–2031 job-cycle rows | capacity conflicts | notable 2035 variation |
|---|---:|---:|---|
| 1 | 9 | 4 | Zhou Ye ends on counselor route; Luo Cheng on public-institution route |
| 7 | 10 | 9 | Gao Yuan still has no settled sector; Zhou Ye and Luo Cheng both changed route |
| 23 | 7 | 4 | Zhou Ye stays on SOE route; Gao Yuan reaches counselor route; He Xin reaches pharma |

All three runs produced a holder-linked capacity conflict. In the smoke harness the first conflict was already visible in 2026: He Xin held the scarce public-sector high-touch slot and Gao Yuan was blocked for that cycle. This is a candidate structural mechanism, not canon.

Original-character time pressure also rose in all three smoke runs because the new cohort consumed real attention. That prevents the six added characters from receiving costless help from the existing cast.

## 5. Historical meaning of this pass

The useful new historical object is not 'who gets which job'. It is **search continuity under shared opportunity scarcity**.

A doctoral graduate can now spend several years in a path where:

1. a preferred route remains attractive;
2. access to high-quality preparation or recommendation is scarce;
3. another person's success can narrow one's immediate feasible set;
4. repeated structural exclusion and repeated merit failure are recorded separately;
5. accumulated pressure can cause a target revision;
6. a later success can feed back into the network that helped produce it;
7. the helpers paid time before receiving any later network return.

This gives the 2026–2035 branch a more plausible route from small ordinary scarcity to long-run biography.

## 6. What remains weak

This pass still treats family care as an annual bargaining load rather than a concrete household network. The two-older-brothers families do not yet contain individually modeled brothers with different cities, incomes, spouses and willingness to provide care. The only-child families also lack explicit parental retirement, housing and health histories.

City choice is still under-specified. A sector label does not yet carry a concrete city bundle of wage, housing, commute, social insurance continuity, family distance and re-entry cost.

The next high-value structural pass should therefore connect **household members + city-specific offers + sector-specific employment terms** before selecting any literary winner world.
