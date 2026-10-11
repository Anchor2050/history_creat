"""Throwaway probe: dump the real TextArena SecretMafia observation stream.

Not part of the deliverable; used to ground the live-runner design in observed
behaviour instead of assumptions.
"""
import random
import sys

from textarena.envs.SecretMafia.env import SecretMafiaEnv

NUM_PLAYERS = 6
SEED = 11

env = SecretMafiaEnv(mafia_ratio=0.25, discussion_rounds=3)
env.reset(num_players=NUM_PLAYERS, seed=SEED)
state = env.state

print("roles (backstage, printed only for probe understanding):", env.player_roles)
print("--- initial private inboxes ---")
for pid in range(NUM_PLAYERS):
    for row in state.observations[pid]:
        print(f"  inbox[{pid}] from={row[0]} type={row[2].name} msg={row[1]!r}")
    state.observations[pid] = []

seen = {pid: 0 for pid in range(NUM_PLAYERS)}
rng = random.Random(SEED)
steps = 0
while not state.done and steps < 400:
    pid = state.current_player_id
    phase = state.game_state["phase"]
    phase_name = phase.value if hasattr(phase, "value") else str(phase)
    alive = list(state.game_state["alive_players"])
    # naive random legal action
    if phase_name == "Night-Mafia":
        mafia = [p for p in alive if env.player_roles[p] == "Mafia"]
        opts = [p for p in alive if p not in mafia]
    elif phase_name in ("Night-Doctor", "Night-Detective", "Day-Voting"):
        opts = [p for p in alive if p != pid]
    else:
        opts = []
    if opts:
        action = f"[Player {rng.choice(opts)}]"
    else:
        action = "I have nothing to add."
    try:
        env.step(action)
    except Exception as exc:  # noqa: BLE001
        print("STEP ERROR", phase_name, pid, action, type(exc).__name__, exc)
        break
    steps += 1
    for other in range(NUM_PLAYERS):
        inbox = state.observations[other]
        new = inbox[seen[other]:]
        seen[other] = len(inbox)
        for row in new:
            print(f"  step{steps} ({phase_name} actor={pid}) -> inbox[{other}] "
                  f"from={row[0]} type={row[2].name} msg={row[1]!r}")

print("done:", state.done, "steps:", steps)
print("rewards:", state.rewards)
print("game_info:", {p: state.game_info[p] for p in range(NUM_PLAYERS)})
print("alive:", state.game_state["alive_players"])
print("logs sample:", state.logs[:8])
