# StoryBox Scene / Multi-Game Engine v2

> adaptation-only design. This extends the round-based engine. It does not alter frozen historical history.

## 1. Core hierarchy

The runtime hierarchy is:

**World → Event Arc → Game → Scene → Round → Action**

These levels are not literary chapter labels.

- **World**: persistent people, institutions, maps, resources, relationships, reputation, obligations, secrets and hard constraints.
- **Event Arc**: a large causal process containing one or more event nodes and multiple games. Example: a cross-institution risk-list incident from first anomaly through audit and institutional aftermath.
- **Game**: one bounded strategic problem with a dominant objective and convergence rule. Example: what can be truthfully reported within 72 hours.
- **Scene**: a bounded encounter in one location/channel/time window with a concrete local purpose. A scene may contain several rounds of interaction.
- **Round**: one cycle of perception → belief update → action → collision → hard-world resolution → writeback.
- **Action**: one actor's local move, including speaking, withholding, verifying, escalating, refusing, waiting or doing nothing.

A novel chapter may render one scene, part of one scene, several scenes, or selected material from several rounds. Chapter boundaries are a Storyteller decision, not a StoryBox state boundary.

## 2. Why Scene exists

A scene is more than one exchange.

Example:

1. Luo asks whether the list was already used.
2. Hospital side says it was exported but claims it was only preparatory.
3. Project office asks who saw the export.
4. Hospital asks why an old version was running.
5. Technical side refuses the implied causal conclusion and requests the exact input snapshot.
6. New evidence arrives before anyone reaches agreement.

These are multiple rounds inside one scene. The scene ends only when the local action set materially changes: new evidence arrives, someone leaves, a deadline interrupts, authority changes, the parties reach a local commitment, or no further legal move remains.

A scene must therefore have:

- `scene_id`
- `game_id`
- location/channel
- start trigger
- participants and observers
- local objective(s)
- information boundaries
- round list
- scene exit condition
- scene outcome / state deltas
- unresolved carry

## 3. Event Arc and event nodes

An Event Arc is a graph, not a linear chapter outline.

It contains **event nodes**. An event node is triggered only when its preconditions are satisfied by prior game/scene state.

Example event nodes for the risk-list arc:

- E0: suspicious list discovered
- E1: all overnight runs frozen
- E2: 72-hour joint explanation ordered
- E3: pilot pause/narrow/continue decision
- E4: formal audit opened
- E5: responsibility/power redesign adopted or rejected
- E6: institutional/career aftermath becomes visible

The system must distinguish:

- **pre-event convergence**: multiple scenes/games create enough state for an event node to fire;
- **event firing**: a hard-world mutation happens;
- **post-event games**: actors respond to the new world created by the event.

This avoids treating a large event as one author-invented beat. The event is earned by accumulated state.

## 4. Multiple concurrent Games

An Event Arc may contain several active games at once.

For example during the same 72 hours:

- Game A: reconstruct the technical/data cause;
- Game B: decide what the institutions can truthfully say publicly;
- Game C: determine whether the pilot continues tomorrow;
- Game D: locate how the screenshot left the internal workflow.

These games share one World but do not share all information automatically.

A result in one game may spill into another only through an explicit bridge:

- public disclosure;
- participant carries information;
- formal report;
- shared evidence object;
- authority decision;
- resource transfer;
- reputation change;
- map/jurisdiction change.

No magical synchronization is allowed.

## 5. One actor may participate in multiple Games

Actors are persistent world entities, not pieces owned by a single game.

An actor has a **participation portfolio**.

Each participation records:

- `game_id`
- local role / jurisdiction
- local stake
- information available in that game
- obligations in that game
- current stance
- attention allocation
- authority allocation
- risk exposure

The same actor may be:

- highly cooperative in one game;
- cautious or obstructive in another;
- a verifier in one scene;
- a gatekeeper in another;
- a beneficiary in one process;
- a person exposed to blame in another.

There is no global `good_person` / `bad_person` flag.

Moral valence is a reader interpretation. The runtime stores incentives, duties, knowledge, beliefs, actions and consequences.

## 6. Concurrency capacity

Game participation is governed by a **soft capacity** and a **hard cap**.

Suggested actor parameters:

- `attention_budget`
- `coordination_capacity`
- `delegation_capacity`
- `formal_power`
- `information_access`
- `stress_tolerance`
- `current_fatigue`
- `current_obligations`
- `max_parallel_games_soft`
- `max_parallel_games_hard`

Typical ordinary actors may have a soft capacity around one primary game plus limited peripheral participation.

High-power or highly connected actors may sustain 2–4 active games because they can delegate, summon information, coordinate subordinates or hold authority across jurisdictions.

Exceeding soft capacity is legal but creates costs such as:

- slower response;
- memory/coordination errors;
- shallow belief updating;
- delayed commitments;
- irritability or relationship cost;
- greater delegation;
- higher chance of contradictory promises;
- vulnerability to information leakage across games.

Exceeding hard capacity is illegal unless a hard-world emergency temporarily changes the capacity.

The runtime should model influence through capabilities and position, not through a narrative label like `boss=true`.

## 7. Cross-game spillover

Persistent world state can carry across games, but not every local fact does.

Potential cross-game state:

- fatigue;
- reputation;
- commitments/promises;
- money/resources;
- relationship damage or trust;
- formal authority;
- public information;
- known secrets if the actor personally carries them;
- institutional rules;
- deadlines;
- opportunity cost.

Game-local state may remain isolated:

- confidential evidence;
- unshared suspicions;
- role-specific instructions;
- beliefs formed from information unavailable elsewhere.

Cross-game leakage itself may be an event.

## 8. Scene convergence

A Scene ends when at least one of these occurs:

1. its local objective is resolved or transformed;
2. new evidence or a new actor materially changes the action set;
3. authority or jurisdiction changes;
4. a deadline interrupts;
5. all eligible participants act/pass and no new local move remains;
6. the scene reaches local deadlock;
7. actors physically/virtually separate.

A Scene may end without resolving the Game.

## 9. Game convergence

A Game ends when:

- objective resolved;
- objective failed;
- stable equilibrium reached;
- deadlock reached;
- absorbed into an institutional rule;
- superseded by a new dominant game;
- hard terminal event fires;
- round/scene cap or safety stop is reached.

Convergence is not victory.

## 10. Event-node convergence

An Event Node fires only when its trigger predicate is satisfied.

Predicates should be built from auditable state such as:

- game status;
- mystery status;
- deadline state;
- authority decision;
- public information threshold;
- resource threshold;
- map/jurisdiction unlock;
- commitment count/state;
- evidence requirement.

The engine should not fire event nodes merely because the Storyteller wants a dramatic beat.

## 11. Anti-filler consequence

This hierarchy helps remove filler at every scale.

- An Action must have a legal basis and possible consequence.
- A Round must change state or count toward a justified deadlock/equilibrium.
- A Scene must change the local action set, information, relationship, power, commitment or next trigger.
- A Game must converge or expose why it cannot.
- An Event Arc must leave persistent world consequences.

Dialogue for its own sake is not a Round result.
A location for atmosphere only is not a Scene.
A character cameo for ensemble coverage is not a Game participation.

## 12. Storyteller relationship

StoryBox runs the world.
Storyteller renders selected traces for readers.

Storyteller may:

- merge several rounds into one scene in prose;
- split one long scene across chapters;
- hide information the world already contains;
- reorder reader revelation when chronology remains truthful;
- choose a viewpoint that misunderstands events.

Storyteller may not:

- rewrite truth;
- invent a state delta that StoryBox did not produce;
- move an actor into a game without a valid bridge;
- make a game converge for literary convenience;
- erase cross-game costs because they complicate a character arc.

## 13. Current implementation target

The next runtime version should add:

1. `SceneState` above Round;
2. `ActorPortfolio` for concurrent game participation;
3. `EventArcState` and event-node predicates;
4. cross-game spillover rules;
5. soft/hard concurrency capacity;
6. tests for the same actor being cooperative in one game and obstructive in another without contradiction;
7. tests for a high-capacity actor participating in several games with fatigue/commitment costs;
8. tests that event nodes cannot fire before preconditions are satisfied.
