# Six-character cohort integration, 2026–2035

Branch: `chatgpt/career-six-cohort`

Base: `chatgpt/endogenous-social-topology`

Status: **noncanonical long-horizon extension**. The original Chen Lan / Lin Jing / Xu Hang trunk remains authoritative; this branch adds six people and lets their choices alter the same social graph without rewriting the existing trunk by fiat.

## Added cohort

| ID | Name | 2026 fixed starting facts | Initial target |
|---|---|---|---|
| `zhou_ye` | 周野 | 男；虚构五线城市语境；独生子女；父母双职工；数学博士、概率论；公开论文 0 | 国企 |
| `gao_yuan` | 高原 | 男；虚构五线城市语境；独生子女；父母双职工；数学博士、概率论；公开论文 0 | 公务员 |
| `luo_cheng` | 罗诚 | 男；虚构五线城市语境；独生子女；父母双职工；数学博士、概率论；公开论文 0 | 高校辅导员 |
| `tang_yu` | 唐雨 | 女；家中老三；两个哥哥；生存分析 | 高校 |
| `he_xin` | 何欣 | 女；家中老三；两个哥哥；生存分析 | 公务员 / 事业单位 |
| `song_nan` | 宋楠 | 女；家中老三；两个哥哥；生存分析 | 医药企业 |

The women’s exact 2026 publication records were not supplied, so they remain open variables. Wealth, marriage, fertility, health, sibling relationship quality and final career outcomes also remain open.

## Direct links into the original cast

The extension deliberately uses existing people as causal participants rather than cameo appearances.

- 周野 ↔ 许航: reproducibility / reliability work. This can improve Zhou’s technical credibility and Xu’s verification reputation.
- 周野 ↔ 陈岚: stable-employment comparison. Their conversations expose the exchange rate among income, organizational security, family distance and unowned time.
- 高原 ↔ 林静: public-sector preparation and information exchange. It expands Lin’s public-sector outside option while Gao receives interview / process knowledge.
- 罗诚 ↔ 孙洁: student-affairs reality and counselor recruitment process. Procedural information is allowed; guaranteed admission is not.
- 罗诚 ↔ 林静: university administrative work and research work become reciprocal comparison lives.
- 唐雨 ↔ 沈雁: methods feedback without automatic authorship or job guarantee.
- 唐雨 ↔ 许航: survival-analysis verification work; failed replication can become professional trust rather than a shame event.
- 何欣 ↔ 林静: public-sector / academic / city-choice comparison.
- 何欣 ↔ 孙洁: public-institution procedure information; Sun Jie cannot bypass recruitment authority.
- 宋楠 ↔ 陈岚: translating statistical training into organizational and client responsibility.
- 宋楠 ↔ 赵珂: paid health-data project channel under real budget and delivery constraints.

These links are two-way where the original three are involved. The added cohort changes Lin’s outside-option set, Chen’s health-data translation network and Xu’s verification reputation.

## Long-horizon interaction anchors

### 2026 — same exit window, different ladders

All six enter during the original 2026 doctoral world. Their immediate pressure is first-job conversion rather than a retrospective life summary. The probability PhDs have no published papers at the start, so the doctorate credential, technical credibility, examination skill and organizational narrative are priced separately. The survival-analysis group faces a different conversion problem: research capital can point toward university, public service or pharma.

The first interactions with Lin, Chen, Xu, Sun, Shen and Zhao occur here. No one is granted an outcome because an existing character likes them.

### 2027 — visible divergence

Chen’s material ascent outside academia becomes a live comparison for Zhou and Song. Xu’s reliability work becomes useful to Zhou and Tang. Gao and He see through Lin that an apparently slower academic path still carries option value.

This year is designed to produce different interpretations of “stability,” not one correct answer.

### 2028 — repeated failure may change the target

The engine now permits repeated recruitment failure to change a person’s search direction. A 2026 target is an initial preference, not a 2035 destiny label. Zhou can leave the SOE route; Gao can leave civil-service preparation; Luo can leave the counselor route; Tang and Song can cross between academic and industry paths; He can move among public-institution, counselor and industry routes.

The change requires accumulated history and a seeded branch. It is never triggered directly by gender or sibling structure.

### 2029 — responsibility and reliability are repriced

The original trunk’s verification / responsibility arc becomes a bridge. Tang’s collaboration with Xu and Song’s contact with Chen allow the added cohort to experience the same historical repricing through different occupations.

### 2030 — family structure enters as a bargaining state

Only-child status and having two older brothers change the feasible care-sharing set, but the simulator draws a bargaining share rather than assigning a moral duty. This affects time and mobility. It cannot directly choose a job, marriage or city.

### 2031 — care is information before sacrifice

The original Lin care shock is treated as a world anchor. Gao and He can observe that a family health event need not mechanically imply resignation or permanent return. Zhou, as an only child, may face a narrower family substitution set, but his actual response remains contingent on job flexibility, money and family bargaining.

### 2032 — city choice becomes a bundle

Lin’s outside-city offer and care/housing calculation become a shared comparison point. The six added characters evaluate jobs together with housing, commute, welfare continuity, family distance and re-entry cost. Career reassessment is allowed in this year.

### 2033 — socially useful work can remain underpriced

Xu’s verification-value / market-price gap is visible to Zhou and Tang. It gives the world a route where high social value does not automatically create status or salary.

### 2034 — stability is stress-tested

Chen’s constrained training budget and demand pressure provide a real counterexample to “private sector equals money” and “stable sector equals no risk.” Mid-career search / re-entry can occur here, including return toward a previous sector.

### 2035 — no single winner table

The extension ends with annual state snapshots, family-care load, career history, network effects and a causal topology. It does not compute one happiness score or rank the nine younger characters. The original 2035 trunk rule remains: success resources stay partially unbundled.

## Executable invariants

`narrative/longform/career_six_2035.py` enforces the following:

1. the six fixed 2026 identities and targets are preserved in `target_2026`;
2. current targets may change after repeated failure or later reassessment;
3. shared referral / interview / project capacity is explicit;
4. family structure affects care bargaining and mobility, not destiny;
5. interactions write reputation / option changes into the same `ConsequenceTopology` class used by the base branch;
6. Lin, Chen and Xu are changed by the new cohort, not merely referenced;
7. every run is marked `noncanonical_scout`;
8. 2026–2035 annual snapshots are retained for literary replay.

## Validation status

A dedicated test file covers the fixed user constraints, the full 2026–2035 horizon, links to existing actors, family-pressure non-determinism, topology membership and the requirement that different seeds can produce different 2035 destinations.

The current execution environment could not clone GitHub because outbound DNS resolution was unavailable, so the repository test suite is **not claimed as remotely or locally executed from the branch checkout**. The new Python module was syntax-checked and its core logic was run in an isolated equivalent smoke harness; repository CI should still be treated as the authoritative integration check when available.
