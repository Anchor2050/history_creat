# Round-Based Narrative Engine v1

## Core idea

The novel is generated from a multiplayer state-transition system, not from a list of chapters.

A chapter is only a readable rendering of selected state changes from one or more rounds.

The deeper loop is:

**world state -> round trigger -> role-local observations -> private interpretations -> actions -> collisions -> public consequences -> hidden consequences -> map / relationship / information updates -> next round**

This is closer to script-murder games, Werewolf, social deduction, strategy games and emergent-history simulation than to a conventional outline-first novel.

The point is not to turn the novel into a game transcript. The game logic stays backstage; prose shows only what creates reader tension and human consequence.

---

## Why rounds matter

Rounds solve several problems that flat chapter planning did not solve:

1. **No roster-driven introductions.** A character enters only when a round reaches their information, authority, location, interest or relationship.
2. **Information asymmetry becomes structural.** Different actors may be rational while holding incompatible beliefs because they literally know different things.
3. **Mystery can grow without author cheating.** Evidence enters world state at a specific round; later discoveries reveal earlier blind spots rather than inventing explanations after the fact.
4. **Characters preserve continuity.** A person carries memory, temperament, commitments, grudges, skills and prior failures into the next round.
5. **Maps can expand.** New locations and institutions unlock only when the active incident reaches them.
6. **Power is operational.** Who can freeze a system, speak publicly, access logs, approve money, call a meeting or delay a report becomes part of the state.
7. **History emerges.** A later round inherits all earlier choices, misunderstandings and institutional changes.

---

## Round state

Each round has seven state layers.

### 1. Hard world state
Things true regardless of what characters believe:
- date/time;
- active institutions;
- system versions;
- money/budget constraints;
- deadlines;
- public rules;
- physical locations;
- who has formal authority;
- what actually happened.

### 2. Map state
The currently reachable narrative world:
- rooms/offices/hospitals/campuses/companies/cities;
- channels: phone, group chat, email, meeting, public platform;
- institutional edges between locations;
- travel / access cost;
- whether a place or group has been exposed to the reader.

The map expands only when an active path reaches it.

### 3. Actor state
For each actor:
- current goal;
- fear / protected value;
- obligations;
- current fatigue / pressure;
- skills;
- role power;
- reputation;
- unresolved past issue;
- relationship state;
- Campbell long-arc position (backend only).

### 4. Information state
Maintain four layers:
- **truth**: what actually happened;
- **public information**: known to everyone in scene / institution / public;
- **private information**: known only to selected actors;
- **beliefs**: what each actor thinks happened.

Beliefs may be wrong without characters being stupid.

### 5. Mystery state
Each open question is a node:
- question;
- current hypotheses;
- evidence supporting / weakening each hypothesis;
- who knows each piece;
- next possible tests;
- false-but-reasonable explanations;
- eventual truth status.

A mystery should not equal a single hidden answer. Good central mysteries branch into technical, institutional and human layers.

### 6. Power state
Track concrete powers, not abstract status:
- can approve;
- can delay;
- can disclose;
- can access logs/data;
- can allocate people;
- can sign;
- can impose deadlines;
- can shape public narrative;
- can refuse cooperation;
- can absorb or externalize cost.

### 7. Tension state
For every live line:
- what must happen soon;
- what may go wrong;
- what actors disagree about;
- what the reader knows but a character does not;
- what a character knows but reader does not;
- what has been promised and not paid off.

---

## Round phases

A round normally follows these phases. They need not all be shown in prose.

### Phase A: world update
An exogenous or inherited change occurs.

Examples:
- new batch arrives;
- deadline shortens;
- screenshot leaks;
- a superior asks for an explanation;
- a model rerun produces a conflicting result;
- a student complains;
- someone leaves town;
- a budget line is frozen.

### Phase B: perception
Each active actor receives only the information available to them.

No omniscient sharing.

### Phase C: interpretation
Characters form local explanations using their expertise, interests, biases and memory.

Different people may reach different reasonable conclusions.

### Phase D: action selection
Each actor chooses an action:
- inspect;
- conceal;
- escalate;
- delay;
- verify;
- blame;
- protect someone;
- protect institution;
- protect process;
- publish;
- ask for help;
- do nothing.

Action must arise from actor state, not plot convenience.

### Phase E: collision
Actions interact.

This is the main source of plot.

Examples:
- technical team freezes system while hospital insists on continuing service;
- administrator needs a report before verification is complete;
- researcher refuses a conclusion that manager needs today;
- someone shares a screenshot to protect themselves and creates a public crisis.

### Phase F: resolution
The world updates according to hard constraints, authority and action interaction.

No character gets outcomes just because the story needs them.

### Phase G: writeback
Update:
- facts;
- beliefs;
- trust;
- reputation;
- access;
- map;
- mystery hypotheses;
- open debts;
- future options.

Then next round begins.

---

## Round cadence

Rounds are not equal to chapters.

One chapter may contain:
- one high-pressure round;
- several short rounds;
- half a round shown from one viewpoint.

One round may span:
- one phone call;
- one workday;
- 72 hours;
- several weeks if little state changes.

Use **state-change density**, not calendar time, to decide chapter boundaries.

---

## Character entry rule

A new important character enters when at least one condition becomes true:

1. the current mystery requires information only they possess;
2. an institution sends the active event into their jurisdiction;
3. a current actor deliberately seeks them out;
4. their action independently changes the same world state;
5. map expansion makes contact unavoidable.

Never introduce someone because the ensemble feels incomplete.

When a character first appears, the round should immediately expose:
- one goal;
- one pressure;
- one asymmetry of information or power;
- one behavioral fingerprint.

No biography paragraph required.

---

## Map expansion

Treat places like game-map unlocks.

Initial map should be small.

For the risk-list incident, possible progression:

**project office**
-> **technical operations room**
-> **hospital follow-up desk**
-> **research group**
-> **public-institution coordination room**
-> **company management meeting**
-> **external public/media space**

Do not show all locations early.

Each new location must contain:
- a new capability;
- a new information source;
- a new constraint;
- or a new faction.

If it adds none of these, it is decorative and should be cut.

---

## Mystery progression

A round should normally do at least one of these:
- confirm one hypothesis;
- weaken one hypothesis;
- reveal that two seemingly separate clues share a cause;
- reveal that one clue had multiple causes;
- expose an actor's mistaken belief;
- create a new question that is causally downstream of an old one.

Avoid endless mystery inflation.

Before adding a major mystery node, pay off or materially transform an older one.

The ideal pattern is not:

`question -> answer`

but:

`question -> plausible answer -> contradiction -> narrower question -> partial answer -> human consequence`

---

## Social-deduction layer

The story may borrow from Werewolf / script-murder games without turning into literal hidden-role fiction.

Useful mechanics:
- uneven information;
- credible lying or omission;
- self-protective disclosure;
- people accusing based on incomplete evidence;
- public vote / decision before certainty;
- identity / reputation effects;
- coalition formation;
- temporary alliances;
- people who understand the truth but cannot prove it;
- people who hold power but understand less;
- people who know less yet accidentally make the correct decision.

Important: do not secretly assign one permanent "wolf" unless the story truly needs one. Structural conflict is stronger when multiple parties are locally rational.

---

## Reader layer

The reader is effectively another player with controlled information.

For every round decide:
- what the reader knows;
- what the focal actor knows;
- what another actor knows;
- what no one yet knows.

Three strong tension configurations:

### Reader ahead
Reader knows something the character does not.
Creates dread / anticipation.

### Character ahead
Character knows something the reader does not.
Creates curiosity / suspicion.

### Everyone behind truth
No actor has enough information yet.
Creates collective investigation / uncertainty.

Do not default to omniscient explanation.

---

## Sentence-purpose rule inside rounds

Every sentence must justify itself by one or more functions:
- move action;
- change available information;
- change belief;
- change power;
- change relationship;
- reveal a choice;
- set up or pay off an object/fact;
- orient space/time only when required for later action;
- control rhythm at a high-tension moment.

Atmosphere may remain only when it changes perception, decision or tension.

If removing a sentence leaves the round state unchanged and does not materially alter rhythm, remove it.

---

## Round quality checks

Before rendering prose, ask:

1. What changed since last round?
2. Who knows the change?
3. Who does not?
4. What does each actor now believe?
5. Which action follows naturally from those beliefs?
6. What conflict occurs when actions meet?
7. What new fact becomes true after the collision?
8. What unresolved question survives?
9. What map node, actor or institution becomes reachable now?
10. What earlier setup gets paid off?

If a round cannot answer these, it may be filler.

---

## Relation to StoryBox and the historical simulator

Historical simulation already had most of the required machinery:

**state -> visible information/memory -> personal state -> behavior -> interaction/exogenous event -> candidate -> feasibility -> writeback**

The adaptation layer should reuse this logic instead of replacing it with an outline-first novelist.

The key extension is:

- explicit round boundaries;
- explicit map state;
- explicit mystery graph;
- explicit private/public information;
- explicit power/action collision;
- explicit reader knowledge state;
- explicit payoff debt.

Thus the same engine can support:
- long historical simulation;
- mystery / incident arcs;
- institutional drama;
- relationship stories;
- career and family arcs;
- later literary rendering.

The prose is downstream of the simulation, not the simulation itself.
