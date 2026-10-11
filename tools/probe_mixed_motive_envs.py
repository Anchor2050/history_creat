"""Probe which TextArena mixed-motive envs actually run in 0.7.4.

SecretMafia taught us not to trust an env's apparent contract: check reset, a
few steps, action parsing and what is observable before building anything on it.
"""
import importlib
import traceback

CANDIDATES = [
    ("PublicGoodsGame", "PublicGoodsGameEnv", {"num_rounds": 3, "communication_turns": 1}),
    ("BlindAuction", "BlindAuctionEnv", {"num_items": 3, "conversation_rounds": 1}),
    ("LetterAuction", "LetterAuctionEnv", {}),
    ("MarketEntryGame", "MarketEntryGameEnv", {"num_rounds": 3, "communication_turns": 1}),
    ("IteratedStagHunt", "IteratedStagHuntEnv", {"num_rounds": 3, "conversation_rounds": 1}),
    ("IteratedPrisonersDilemma", "IteratedPrisonersDilemmaEnv", {"num_rounds": 3, "communication_turns": 1}),
]

for module_name, class_name, kwargs in CANDIDATES:
    print(f"=== {module_name} ===")
    try:
        module = importlib.import_module(
            f"textarena.envs.{module_name}.env"
        )
        env_class = getattr(module, class_name)
    except Exception as exc:  # noqa: BLE001
        print(f"  IMPORT FAIL: {type(exc).__name__}: {exc}")
        continue
    try:
        env = env_class(**kwargs)
    except Exception as exc:  # noqa: BLE001
        print(f"  CONSTRUCT FAIL: {type(exc).__name__}: {exc}")
        continue
    try:
        env.reset(num_players=4, seed=1)
    except Exception as exc:  # noqa: BLE001
        print(f"  RESET FAIL: {type(exc).__name__}: {exc}")
        continue
    state = env.state
    gs = state.game_state
    print(f"  reset OK; phase={gs.get('phase')!r} keys={sorted(gs)[:8]}")
    # Try a few blind steps with a generic action to see what the env accepts.
    steps = 0
    errors = []
    while not state.done and steps < 8:
        try:
            pid = int(state.current_player_id)
            # try the env's advertised formats in turn
            for action in (f"[{gs.get('endowment', 1)}]", "[E]", "{hello}", "hello"):
                try:
                    env.step(action)
                    break
                except Exception:
                    continue
            steps += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{type(exc).__name__}: {exc}")
            break
    print(f"  steps attempted={steps} done={state.done} errors={errors[:2]}")
print("done")
