# Career-six research pass: mobility, welfare continuity, and delayed job conversion

Date: 2026-10-11

Branch scope: `chatgpt/career-six-cohort` only.

Status: **research input for noncanonical replay**. This note does not alter the historical trunk and does not assert future policy after the cited observation date.

## Why this pass

Continuity v2 repaired the artificial 2029–2031 search gap and made scarce network opportunities causal. Its next weakness is that `city_state` remains almost inert: changing sector or city does not yet carry concrete welfare-continuity or re-entry consequences. That makes migration too cheap and family proximity too abstract.

This pass separates observed institutional facts from scenario assumptions and engineering parameters so that the next simulator layer can make a job offer a bundle rather than a sector label.

## Observed institutional facts

### Graduate employment is a continuing process after graduation

The Ministry of Education's 2025 employment campaign explicitly emphasized expanding market-oriented positions, campus recruitment, public employment services, and support continuing after students leave school. The July 2025 follow-up described service handoff for graduates still unemployed after leaving school and continuing public employment services rather than treating graduation day as a terminal state.

Sources:

- Ministry of Education, 2025-06-06, `教育部部署开展2025届高校毕业生就业“百日冲刺”行动`: https://www.moe.gov.cn/jyb_xwfb/gzdt_gzdt/s5987/202506/t20250606_1193195.html
- Ministry of Education, 2025-07-28, `高校毕业生离校后就业工作推进会召开`: https://www.moe.gov.cn/jyb_xwfb/gzdt_gzdt/moe_1485/202507/t20250728_1199682.html

Historical implication: a character remaining in search after doctoral exit should retain access to some public or institutional search channels, but the quality of tailored referrals may decay or become scarcer. V2's continuous search is therefore directionally defensible; future code should distinguish ordinary public search support from scarce high-touch network slots.

### Medical-insurance continuity can make a move path-dependent

The National Healthcare Security Administration states that employees transferring basic medical-insurance relationships after a contribution interruption of no more than three months may, subject to destination rules, make up contributions without a benefit waiting period. It also warns that continuity is tied to benefit enjoyment. National transfer rules support cross-province processing and reduced the standard processing time to no more than 15 working days.

Sources:

- NHSA, 2025-05-07, `我的职工医保中断了，可以补缴吗？`: https://www.nhsa.gov.cn/art/2025/5/7/art_14_16463.html
- NHSA policy interpretation of the Basic Medical Insurance Transfer and Continuation Interim Measures, 2021-11-26: https://www.nhsa.gov.cn/art/2021/11/26/art_53_7412.html

Historical implication: mobility should not be represented as a permanent binary penalty. A move can be administratively feasible while still carrying timing risk if employment gaps lengthen. The simulator should track an employment/coverage gap clock and let the same city move have different consequences depending on when it occurs.

### Pension portability reduces one barrier but does not erase employment-term differences

Cross-region pension transfer is an active administrative object. In the Beijing–Tianjin–Hebei region, a 2025 agreement shortened enterprise employee basic-pension transfer processing from the national 15-working-day benchmark to five working days, in some cases same-day after acceptance. This is evidence that portability frictions can vary by region and can fall over time.

Source:

- Ministry of Human Resources and Social Security / China Employment, 2025-08-05, `京津冀：企业职工养老保险跨省转移“提速”办理`: https://chinajob.mohrss.gov.cn/c/2025-08-05/444121.shtml

Historical implication: `welfare_continuity` should have components. Basic pension portability, medical-insurance continuity, occupational/enterprise annuity eligibility, housing support, and job tenure should not collapse into one score.

### Housing prices and employment conditions can move in different directions

The National Bureau of Statistics' 2025 statistical communiqué reports 72.504 million employed persons nationwide, 47.535 million urban employed persons, 12.67 million new urban jobs, and an average surveyed urban unemployment rate of 5.2%. It also reports broad housing-price weakness at the end of 2025: among 70 large and medium cities, second-hand housing prices fell month-on-month in all 70 in December.

Source:

- National Bureau of Statistics, 2026-02-28, `中华人民共和国2025年国民经济和社会发展统计公报`: https://www.stats.gov.cn/xxgk/sjfb/tjgb2020/202602/t20260228_1962662.html

Historical implication: the engine must not use a single macro prosperity scalar to move wages, hiring, and housing together. A weaker housing market can lower purchase cost while weak hiring raises income uncertainty. This changes the topology of a move: someone may be able to afford housing yet be less willing to lock in because job re-entry is fragile.

## Scenario assumptions for the next replay layer

These are **not observed facts** and must remain seeded/noncanonical.

1. Each serious offer will carry `city`, `employment_form`, `monthly_disposable_income_band`, `housing_burden`, `commute_hours`, `family_travel_hours`, `welfare_components`, and `reentry_cost`.
2. A character may reject a higher-income offer because the combined bundle worsens care substitution, coverage-gap risk, or future re-entry. Rejection must leave a causal trace and can alter another character's opportunity set if the offer/referral is scarce.
3. Five-line-city family background will be represented through specific parent residence, housing and travel links. It will not mechanically imply return migration.
4. For Tang Yu, He Xin and Song Nan, two older brothers will become distinct household actors with separately seeded city, work flexibility and willingness. Their existence expands the bargaining set; it does not guarantee care substitution.
5. For Zhou Ye, Gao Yuan and Luo Cheng, only-child status narrows the sibling substitution set but money, spouse/partner, extended kin, purchased care and employer flexibility remain possible substitutes.
6. Welfare continuity will modify feasible timing, not assign moral value to a sector.

## Engineering parameters to keep visibly synthetic

The following numbers, when introduced, should be labeled engineering parameters and sensitivity-tested rather than presented as empirical estimates:

- maximum acceptable one-way family travel time before mobility cost steepens;
- coverage-gap penalty after one, two, or three months;
- housing-burden bands;
- value assigned to employer housing support or annuity participation;
- probability that a sibling can substitute care in a given year;
- decay rate of high-touch referral access after repeated unsuccessful cycles;
- re-entry cost after leaving a public institution, university, SOE, or pharma employer.

## Structural replay targets

The next code pass should be judged by topology, not by whether the six end in aesthetically varied jobs.

A successful replay should be able to generate chains such as:

`Song Nan accepts a distant pharma offer -> her family care share is renegotiated -> one brother supplies more time but loses work flexibility -> Tang Yu hears a more credible account of industry mobility through Song -> Tang rejects or accepts a later offer differently`.

Or:

`Gao Yuan uses a scarce public-sector preparation slot -> He Xin loses tailored preparation that cycle -> He takes a public-institution offer in another city -> the move creates a short insurance-transfer gap and higher family travel cost -> later care pressure makes re-entry to the previous city more valuable -> Lin Jing updates her own public-sector comparison because He Xin's path supplied real information`.

The important feature is that macro and institutional conditions change edges and feasible sets, not only scalar scores.

## Truth / goodness / beauty filter

**Truth:** keep administrative portability distinct from actual household affordability and job security. A transferable benefit does not make a move costless.

**Goodness:** whenever care is substituted, record who pays in time, cash, career flexibility, or relationship strain. Purchased care and sibling help can fail without anyone becoming a villain.

**Beauty:** reuse the same resource at different ages. A 2027 referral can be a coveted opportunity, a 2031 reason someone feels indebted, and a 2034 source of hesitation when asked to recommend another person. A cheap apartment can first mean freedom, later lock-in, and later still become the place from which parental care is coordinated.

## Immediate implementation order

1. Add explicit household members and parent states without changing fixed user facts.
2. Add city/offer bundles and a welfare-gap clock.
3. Let offer acceptance/rejection create downstream availability for other actors.
4. Add tests that family structure changes distributions but cannot directly select a career outcome.
5. Run multi-seed structural replay and only promote mechanisms that survive plausible parameter variation.

No canonical 2035 outcome is selected in this pass.
