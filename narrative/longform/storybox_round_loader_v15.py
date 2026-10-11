"""Load JSON StoryBox game seeds into the v15 round engine."""
from __future__ import annotations

import json
from pathlib import Path

from narrative.longform.storybox_round_engine_v15 import (
    ConvergencePolicy,
    GameState,
    validate_game_state,
)


def game_from_seed(seed: dict) -> GameState:
    policy = ConvergencePolicy(**seed.get("convergence_policy", {}))
    game = GameState(
        game_id=seed["game_id"],
        objective=seed["objective"],
        hard_world=seed.get("hard_world", {}),
        map_state=seed.get("map_state", {}),
        actor_state=seed.get("actor_state", {}),
        truth=seed.get("truth", {}),
        public_information=seed.get("public_information", {}),
        private_information=seed.get("private_information", {}),
        beliefs=seed.get("beliefs", {}),
        relationships=seed.get("relationships", {}),
        power=seed.get("power", {}),
        resources=seed.get("resources", {}),
        mysteries=seed.get("mysteries", {}),
        deadlines=seed.get("deadlines", {}),
        commitments=seed.get("commitments", {}),
        reputation=seed.get("reputation", {}),
        payoff_debt=seed.get("payoff_debt", {}),
        convergence_policy=policy,
    )
    validate_game_state(game)
    return game


def load_game_seed(path) -> GameState:
    seed = json.loads(Path(path).read_text(encoding="utf-8"))
    return game_from_seed(seed)
