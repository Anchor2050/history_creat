# Career-six StoryBox no-API pass 06

Date: 2026-10-11

Branch: `chatgpt/career-six-cohort`

Status: **architecture correction; noncanonical replay infrastructure**.

## Why this correction was necessary

The original StoryBox/Reverie repository does not generate agent cognition by itself. Its `PromptManager` obtains an LLM through `get_chat_model`, and the default configuration points at `gpt-4o-mini`. The repository also supports an Ollama model and a local HuggingFace model, but those still require a model runtime and the original `llm.py` imports an embedding model at module load time.

The current `history_creat` workflow does not assume an OpenAI API key, an Ollama server, or a GPU-hosted HuggingFace model. Therefore the previous v7 runtime may remain as an optional compatibility path, but it cannot be the branch's default execution path.

## New default

`storybox_noapi_runtime_v8.py` is the default micro-interaction runtime.

It deliberately imports no Reverie prompt manager, LLM client, embedding model, OpenAI client, Ollama client, or HuggingFace model. It preserves the useful StoryBox protocol:

`social window -> visible state -> retrieve prior memory -> relationship-bounded interaction -> bilateral memory -> event writeback -> next window`.

The runtime has two cognition backends.

### 1. Deterministic no-API backend

A seeded pure-Python policy chooses semantic social acts such as:

- check in;
- share experience;
- ask advice;
- offer bounded information;
- offer help;
- decline;
- set a boundary;
- ordinary small talk.

This backend is intentionally not presented as literary dialogue. Its purpose is to make the social mechanics executable in ordinary Python and to support regression tests, multi-seed audits, and unattended structural simulation.

### 2. ChatGPT product backend, still with no repository API call

The same runtime can produce a structured cognition request containing only what each actor is allowed to know:

- identity and current state;
- hard-world constraints;
- relationships that have actually been earned;
- retrieved memories;
- current social window;
- allowed social acts.

An interactive ChatGPT session or the existing scheduled ChatGPT task can read that request, generate a structured replay result, and commit/apply it through GitHub. The repository itself never calls the OpenAI API in this workflow. ChatGPT is already the execution environment in which the research is being advanced.

This keeps generative character nuance available without requiring the user to configure an API key inside the repository.

## What remains optional

`storybox_micro_runtime_v7.py` and the direct Reverie bridge remain useful if a future environment provides one of:

- an OpenAI-compatible API;
- a local Ollama server;
- a supported local HuggingFace model/runtime.

They are no longer the default path and no current result may assume that such a backend exists.

## Information discipline

The no-API runtime enforces several rules before applying a replay:

1. both speaker and listener must be participants in the current social window;
2. a private interaction requires an existing relationship or an introduction earned in that event;
3. the channel must match the scheduled event;
4. one conversation does not automatically increase trust or closeness;
5. an offer of help or introduction creates only a hard-world candidate; resources are not created by dialogue;
6. remote interaction cannot move a physical location;
7. silence, refusal, weak conversation and mundane outcomes remain valid.

## Decade driver

`storybox_noapi_driver_v8.py` is now the default bounded decade driver.

It selects a sparse subset of 2026-2035 micro-windows rather than replaying every candidate event, executes them in chronological order, and carries each actor's memory into later windows.

A fully local run therefore needs only Python:

```python
from narrative.longform.storybox_noapi_driver_v8 import run_noapi_decade
result = run_noapi_decade(seed=7)
```

No external API is required for that mode.

For higher-quality character cognition, ChatGPT can instead answer `prepare_next_chatgpt_replay(...)` requests through the existing conversation/automation workflow; `apply_chatgpt_replay(...)` validates and writes those results into the same state transition system.

## Interpretation

This distinction matters:

- StoryBox provides a useful **interaction architecture**;
- an LLM provides one possible **cognition generator**;
- the two should not be conflated.

The branch now uses the architecture even when no external model endpoint exists.

## Next work

The most valuable next step is to make scheduled ChatGPT runs consume one or two cognition requests per cycle and write back structured replay results, while retaining the deterministic backend as the executable control group. Those two streams can then be compared:

- which mechanisms survive both;
- which interactions require language nuance;
- where the deterministic policy is too mechanical;
- where generative dialogue attempts to invent unavailable information or resources.

No single generated dialogue or deterministic interaction becomes canon merely because it was replayed.
