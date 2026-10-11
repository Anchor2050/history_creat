# Career-six StoryBox convergence pass 05

Date: 2026-10-11

Branch: `chatgpt/career-six-cohort`

Status: **noncanonical architecture convergence pass**.

## Why this pass exists

The previous passes improved career search, family care, city offers, cash flow, housing, and income priors. That work made the six added doctoral characters more realistic, but it also created a structural drift: the six-person simulator was becoming a parallel model whose links to Lin Jing, Chen Lan, Xu Hang and the rest of the original cast were increasingly shallow.

This pass corrects that drift.

The project now treats the original StoryBox/Reverie machinery as the **micro-social cognition and memory layer**, while the newer long-horizon modules act as the **hard social-physics layer**.

The intended stack is:

`career / household / city / cash / housing hard state`

`-> socially plausible opportunity to meet`

`-> StoryBox Persona perceive/retrieve/plan/chat/memory replay`

`-> resulting events, information, promises, refusals and changed relationships`

`-> write consequences back into the long-horizon world`

`-> later Storyteller synthesis`

Story generation remains downstream of lived event history.

## 1. Fourteen people now form one ensemble

The main ensemble is:

- 林静 / Lin Jing
- 陈岚 / Chen Lan
- 许航 / Xu Hang
- 吴澄 / Wu Cheng
- 沈雁 / Shen Yan
- 顾维 / Gu Wei
- 赵珂 / Zhao Ke
- 孙洁 / Sun Jie
- 周野 / Zhou Ye
- 高原 / Gao Yuan
- 罗诚 / Luo Cheng
- 唐雨 / Tang Yu
- 何欣 / He Xin
- 宋楠 / Song Nan

They are deliberately **not** initialized as an all-to-all friendship network.

`docs/scenarios/career-six-social-graph-v1.json` defines layered ties such as:

- roommates;
- same doctoral class / cohort;
- former research group;
- mentor-student;
- work/project peers;
- alumni / methods-network contacts;
- career-information peers;
- introduced acquaintances.

The schema also supports `childhood_friend`. No childhood-friend pair has been invented among the fourteen because the user did not specify which two people share that history. It can be added later as a fixed historical fact or used for peripheral characters without changing the engine.

## 2. Strong ties, weak ties, periodic contact and chance contact

A relationship now carries state:

- origin and tie kind;
- trust;
- closeness;
- expected contact interval;
- introduction power;
- last contact;
- shared events;
- whether the relationship came through a third-person introduction.

Relationships can strengthen through repeated contact and decay when people stop seeing one another.

Recurring social rituals currently include:

- the probability-doctoral classmates' meal;
- the survival-analysis classmates' meal;
- old-friend meals among the original younger cast;
- methods/alumni meetups;
- cross-school doctoral friend dinners;
- summer short trips;
- year-end gatherings.

Occasional event types include:

- conference meals;
- weddings / life events;
- recruitment-information sessions;
- project meals;
- weekend outings;
- accidental overlap in the same city;
- dormant group chats becoming active again.

Attendance is conditional on work pressure, job-search state, city, cash, care load and event type. An invitation therefore does not guarantee attendance.

## 3. Friend-of-friend introductions are causal

People who do not know one another do not automatically receive a relationship edge merely because the author wants them to interact.

Inside a social event, a new tie can arise when:

1. both people actually attend;
2. a mutual contact is present and can plausibly introduce them; or
3. the event is genuinely open-context, such as a conference meal or recruitment session;
4. the pair has enough context overlap for an interaction to be plausible;
5. the seeded draw produces an introduction.

The new relationship begins weak. Later contact may strengthen it, or it may remain a weak tie for years.

This allows chains such as:

`classmate dinner -> friend brings another friend -> weak introduction -> months later job information -> later project collaboration`

without pre-writing the final connection.

## 4. Every person keeps a private/professional small theatre

`narrative/longform/ensemble_social_replay_v6.py` gives all fourteen people a `PERSONAL_SCENES` entry and a yearly `personal_scene_pulse` from 2026 through 2035.

This is important for the older / institutional characters. Wu Cheng, Shen Yan, Gu Wei, Zhao Ke and Sun Jie cannot exist only as service providers for the six new doctoral characters.

Examples of their independent scene lines include:

- Wu Cheng: supervisory attention, project deadlines, and invisible labor shifted to reliable people;
- Shen Yan: scarce mentoring time and the gap between willingness to help and ease of asking;
- Gu Wei: verifiability, recommendation risk, and when to spend professional reputation;
- Zhao Ke: delivery, client pressure, budgets, repeated favors, and collaborator trust;
- Sun Jie: queues, institutional boundaries, and being treated as a doorway into a system.

Each younger character likewise retains career and private scene lines. A private scene can remain mostly private; under pressure it may pull in one or two trusted contacts and become a social micro-window.

## 5. StoryBox/Reverie is now explicitly reused

The original repository's useful interaction pipeline is kept:

`Persona -> perceive -> retrieve -> plan -> execute -> long-term memory`.

The new bridge is `narrative/longform/reverie_micro_bridge_v6.py`.

It reuses the repository's existing:

- memory retrieval;
- relationship summarization;
- single-utterance generation;
- bilateral long-term chat-memory writes;
- event manager;
- time manager.

### Remote communication correction

The original `reverie/persona/cognitive/execute.py::chat` physically teleports the initiating persona to the target's current location before chatting. That is not acceptable for a 2026-2035 multi-city world.

The bridge therefore adds channel-explicit chat for:

- phone;
- private WeChat;
- WeChat group;
- email;
- video call;
- in-person contact.

Remote contact writes memories and events **without changing physical location**.

An in-person conversation is permitted only after the social scheduler has already established co-presence.

## 6. Micro-replay packets

The decade is not replayed minute by minute.

`ensemble_social_replay_v6` outputs bounded `micro_replay_packets` around socially or biographically meaningful windows.

A packet contains:

- dates;
- participants;
- interaction mode;
- location/channel;
- introductions;
- each participant's current hard constraints;
- StoryBox-compatible Persona scratch seeds;
- known relationship memories;
- the requirement that no unearned knowledge be exposed;
- the requirement that resulting events and chat memories be written back.

The bridge can materialize one packet as a normal StoryBox-style story directory containing:

- `world.yaml`;
- `personas/<actor>/scratch.json`;
- `personas/<actor>/spatial_memory.json`;
- `personas/<actor>/long_term_memory.json`;
- `micro_packet.json`.

Fine-grained dialogue is intentionally left to Reverie. The scheduler does not write fake dialogue itself.

## 7. Pair conversation selection inside a gathering

A five-person dinner should not produce ten equally deep pair conversations.

The bridge ranks possible pair interactions. It gives special attention to:

- fresh introductions;
- meaningful existing ties;
- mid-strength ties that can transmit new information across circles.

Co-present strangers who were never introduced are not selected for a private conversation plan.

This prevents group events from degenerating into an unrealistic all-to-all information broadcast.

## 8. Structural smoke result

Because the current execution environment still cannot clone the branch through outbound DNS, the repository test suite has not been executed from a checkout.

The new scheduler and bridge source were syntax-checked. A formula-equivalent isolated structural smoke harness was also run using the same fourteen actor IDs, representative career snapshots, the same social-event logic, and the same introduction rules.

For one reference seed the harness produced:

- 190 candidate micro-replay windows;
- 30 final social ties;
- 11 ties created later through event introduction;
- 140 personal-scene pulses (14 people × 10 years);
- no main actor with zero micro-scene participation in that reference run.

These counts are diagnostic only. They are not expected empirical frequencies and they are not canon.

Dedicated tests have been committed for the ensemble and bridge invariants. This pass does **not** claim those tests have run from the GitHub checkout.

## 9. What is now genuinely connected

The architecture can now represent chains of this form:

`Zhou Ye's job-search failure`

`-> he calls Xu Hang because of remembered verification conversations`

`-> Xu Hang decides whether to spend time helping`

`-> a later dinner puts Xu Hang, Chen Lan and Zhou Ye together`

`-> Chen Lan introduces an industry / SOE contact`

`-> the referral occupies a scarce slot`

`-> Gao Yuan's feasible set changes`

`-> Gao Yuan discusses the setback with his probability classmates`

`-> Luo Cheng updates his own view of institutional work`.

Likewise:

`Song Nan's pharma work`

`-> project meal with Zhao Ke`

`-> Chen Lan joins through existing work ties`

`-> a later methods/alumni event exposes Tang Yu to a more concrete industry story`

`-> Tang Yu may update her faculty-vs-industry thinking`

`-> Shen Yan later encounters that changed research agenda through her own mentor scene`.

These are now possible causal paths rather than hand-written pairwise score increments.

## 10. Remaining structural weakness

The six added actors currently have much deeper long-horizon hard state than the original eight.

The original eight now have social memory, personal scenes and pressure, but they do **not yet** all have equally explicit 2026-2035 models for:

- income and savings;
- housing;
- family members and care;
- city migration;
- job changes;
- health;
- long-run employment terms.

That asymmetry is the next major engineering problem.

The correct next step is **not** another six-person `v7` parameter layer. It is to promote the original cast into the same hard-world interface so that all fourteen personas can change cities, lose or gain jobs, take care of family, pay for housing, and alter one another's feasible sets under one common state model.

Only after that should the project spend significant model budget replaying hundreds of micro-windows and selecting a literary trunk.

## 11. Canon rule

No 2035 life outcome is canon in this pass.

No social introduction generated by a single seed is canon.

No single StoryBox conversation should become canon solely because it is vivid.

A candidate event enters the historical/literary trunk only after:

1. the hard-world preconditions are feasible;
2. the relationship path that produced the meeting is auditable;
3. the involved Persona memories contain the needed information;
4. the event survives reasonable replay variation or is explicitly retained as a conditional branch;
5. downstream consequences are carried forward instead of reset.
