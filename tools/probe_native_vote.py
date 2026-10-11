"""Probe: does a day vote submitted as '[N]' survive the observation pipeline?

textarena 0.7.4 State.add_observation strips every role tag such as '[Player 3]'
from PLAYER_ACTION messages. SecretMafia's VoteHandler accepts both '[Player N]'
and '[N]'. This probe checks whether the native '[N]' form survives.

Only environment-level reads used here are phase/alive/observations; player_roles
is read once at the end to report which seats were Mafia, for the probe's own
interpretation, never to choose an action.
"""
from textarena.envs.SecretMafia.env import SecretMafiaEnv

NUM_PLAYERS = 6
SEED = 21


def play(action_format: str):
    env = SecretMafiaEnv(mafia_ratio=0.25, discussion_rounds=1)
    env.reset(num_players=NUM_PLAYERS, seed=SEED)
    state = env.state
    seen = {pid: 0 for pid in range(NUM_PLAYERS)}
    received: list[tuple[str, int, int, str, str]] = []
    day_votes: dict[int, int] = {}
    steps = 0

    def render(target: int) -> str:
        return f"[{target}]" if action_format == "native" else f"[Player {target}]"

    while not state.done and steps < 400:
        pid = int(state.current_player_id)
        raw_phase = state.game_state["phase"]
        phase = raw_phase.value if hasattr(raw_phase, "value") else str(raw_phase)
        alive = [int(p) for p in state.game_state["alive_players"]]
        if phase == "Night-Mafia":
            # Mafia targets are read from the seat's own phase prompt instead of
            # backstage roles: the prompt lists the valid targets.
            inbox = state.observations[pid]
            prompt = " ".join(m for f, m, t in inbox if t.name == "GAME_MESSAGE")
            blocked = set()
            for who in range(NUM_PLAYERS):
                pass
            opts = [p for p in alive if p != pid]
            # crude: at night the Mafia prompt lists valid targets
            opts = [
                p
                for p in alive
                if f"[{p}]" in prompt
            ] or opts
        elif phase in ("Night-Doctor", "Night-Detective", "Day-Voting"):
            opts = [p for p in alive if p != pid]
        else:
            opts = []
        if opts:
            target = opts[0]
            action = render(target)
        else:
            target = None
            action = "nothing material to add."
        if phase == "Day-Voting" and target is not None:
            day_votes[pid] = target
        env.step(action)
        steps += 1
        for other in range(NUM_PLAYERS):
            inbox = state.observations[other]
            new = inbox[seen[other]:]
            seen[other] = len(inbox)
            for row in new:
                received.append((phase, other, row[0], row[1], row[2].name))

    return env, day_votes, received


for fmt in ("native", "player_tag"):
    env, day_votes, received = play(fmt)
    player_actions = [r for r in received if r[4] == "PLAYER_ACTION"]
    parseable = [r for r in player_actions if r[3].strip().startswith("[") and "]" in r[3]]
    empty = [r for r in player_actions if r[3] == ""]
    print(f"--- {fmt} ---")
    print(f"  day votes submitted      : {len(day_votes)}")
    print(f"  PLAYER_ACTION observations: {len(player_actions)}")
    print(f"  empty-string ones         : {len(empty)}")
    print(f"  carrying a bracket target : {len(parseable)}")
    for row in parseable[:6]:
        print(f"    phase={row[0]} to=player{row[1]} from=player{row[2]} msg={row[3]!r}")
    print(f"  done={env.state.done} rewards={env.state.rewards}")
