"""Compatibility wrapper for the corrected controlled topology pilot.

The original pilot was retired after audit because its cash process and
competition logic could manufacture apparently successful chains.
"""
from .topology_pilot_v2 import (
    run_controlled_world,
    run_four_world_controlled_pilot,
)


def run_topology_pilot(seed, weeks=160):
    row = run_controlled_world(seed, weeks)
    return {
        **row,
        "status": "pilot_noncanonical",
    }


def run_four_world_pilot(seeds=(101, 202, 303, 404), weeks=160):
    result = run_four_world_controlled_pilot(seeds, weeks)
    runs = result["worlds"]
    return {
        **result,
        "total_closed_chains": sum(r["chain_count"] for r in runs),
        "worlds_with_at_least_three_chains": sum(
            r["chain_count"] >= 3 for r in runs
        ),
        "status": "pilot_complete" if result["acceptance"] else "pilot_failed",
    }
