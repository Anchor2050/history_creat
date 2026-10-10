# Narrative Core Implementation Plan

Goal: A lightweight DeepSeek-only simulation with replaceable judgment, constrained actions, private observations and traceable consequences. Preserve original StoryBox as baseline.
Architecture: Add narrative/ alongside reverie/. Reuse the perceive-plan-execute-story pattern, but commit facts only through deterministic rules. Standard-library Python 3.11+; no GPU or embedding dependency.

1. tests/test_core.py: define failed-action atomicity, ownership conservation, private information, causality and snapshot recovery tests; run and observe failures.
2. narrative/core.py: actor views, action schema, transactional resolver, immutable event copies, JSON checkpoint and versioned scenario validation. Support move, transfer, tell, promise, wait. Shared scenes are explicit; promises persist and can expire.
3. tests/test_providers.py then narrative/providers.py: bounded DeepSeek JSON calls, configurable model, shared call limit, normalized judgment schema, injectable optional judge and recorded fallback. Jev is deferred; no credentials required.
4. narrative/run.py and scenarios/demo.json: offline scripted smoke test plus live DeepSeek proposing and judging actions; checkpoint every committed action; export event history and optional grounded prose. Reject invalid actions without state mutation; operational failures stop with checkpoint retained.
5. README and docs: commands, local credential setup, exact limitations, no claims of literary quality or live API verification without credentials.
6. Verify unittest suite and offline CLI, inspect diff. No publishing or paid live run without configured credentials.

Acceptance: resources cannot be duplicated; actor views exclude unknown facts/private traits; fact transmission requires knowledge and proximity; events cite causes and state changes; decisions are optional providers, never override hard rules; restart preserves state/history. Existing reverie files unchanged.
