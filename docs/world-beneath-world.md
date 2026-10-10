# World beneath the world

## Why this branch exists

The current long-form prototype can produce coherent micro-level consequences from
money, time, permission, consent, knowledge and relationship constraints. Its
world is still too small for long-horizon literary work: most pressure comes from
deadlines and interpersonal choices.

This branch adds a slow-moving world above the character layer.

The design target is not an empirical forecast of Beijing. It is a fictional,
auditable social world whose institutions and material conditions can change
without waiting for a protagonist to act.

## Layered architecture

```
History / technology / demography
            |
            v
Macro signals and shocks
            |
            v
Institutions / organizations / families / neighborhoods
            |
            v
Actor-specific exposure and knowledge
            |
            v
Characters -> bounded choices -> hard-rule World
            |
            v
Consequences -> memory -> narrative
```

The key rule is one-way authority:

- MacroWorld may change public conditions.
- A bridge may expose selected public changes to characters.
- Characters choose their own response.
- The existing World remains authority for money, time, permission, consent,
  artifact workflow and immutable micro history.
- The writer may select and compress events but cannot change either world.

## First implementation slice

`narrative.longform.macro_world` contains a deterministic slow clock and five
fictional reference indices:

- academic job availability,
- AI research capability,
- urban housing cost,
- university discretionary budget,
- research-outsourcing demand.

Each signal has a starting value, monthly trend and hard bounds. Scenario authors
can add dated changes with explicit provenance. Advancing the macro clock requires
no character action.

`pressures_for(exposure)` then maps public signals to an actor-specific pressure
vector. It intentionally does not return a decision, emotion or plot beat.

This gives us the missing mechanism for sentences of the form:

> the world changed while the characters were busy living.

## What this is not

The numbers are not claims about real China, Beijing, academia, AI progress or
housing. They are fictional scenario parameters.

The first slice is deliberately small. A giant ABM, calibrated economy or
thousands of LLM agents would make the system harder to understand before we know
which macro variables actually produce durable narrative structure.

## Next bridge

The next change should attach exposure profiles to Beijing actors and freeze a
monthly public view. When a threshold-crossing macro event becomes relevant, it
should enter a character's available knowledge as a public fact or institution
notice. That fact can affect plans, applications, budgets or relationships, but
only through the same validated action path used by the micro world.

After the bridge works, run the existing cast from 2026 into the early 2030s
without writing chapters every month. Extract chapters only around irreversible
choices, reversals, reunions, institutional changes and delayed consequences.
