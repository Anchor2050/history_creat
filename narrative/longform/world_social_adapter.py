"""Transactional adapter between World hard authority and social topology."""
from copy import deepcopy

from .ledger import Ledger, LedgerError
from .consequence_topology import ConsequenceTopology, TopologyError


class WorldSocialAdapterError(ValueError):
    pass


class WorldSocialAdapter:
    """Compose World and ConsequenceTopology without weakening either authority."""

    def __init__(self, world, topology=None):
        self.world = world
        self.topology = topology or ConsequenceTopology()

    def snapshot(self):
        return {
            "world": self.world.snapshot(),
            "topology": self.topology.snapshot(),
        }

    def _atomic(self, fn):
        before_world = self.world.snapshot()
        before_topology = self.topology.snapshot()
        try:
            result = fn()
            self.world._validate()
            self.topology._validate()
            return result
        except Exception:
            self.world.state = before_world
            self.topology = ConsequenceTopology(before_topology)
            raise

    def transfer(self, operation_id, source, target, amount, reason, date, cause_ids=None):
        """Commit a social cash consequence through the canonical Ledger."""
        def apply():
            ledger = Ledger.restore(self.world.state["ledger"])
            if ledger.state["now"][:10] < date:
                ledger.advance(date)
            row = ledger.transfer(operation_id, source, target, amount, reason)
            self.world.state["ledger"] = ledger.snapshot()
            self.world.state["now"] = ledger.state["now"][:10]
            node = self.topology._node(
                "micro_cash_transfer", date, target=target,
                payload={
                    "operation_id": operation_id,
                    "source": source,
                    "amount": amount,
                    "reason": reason,
                },
                causes=cause_ids,
            )
            self.world._record(
                "social_cash_consequence",
                operation=operation_id,
                topology_node=node["id"],
                source=source,
                target=target,
                amount=amount,
            )
            return {"ledger": deepcopy(row), "cause": node}
        try:
            return self._atomic(apply)
        except LedgerError as exc:
            raise WorldSocialAdapterError(str(exc)) from None

    def reserve_time(self, operation_id, actor, start, end, reason, cause_ids=None):
        """Commit social obligations to the canonical no-overlap time ledger."""
        def apply():
            ledger = Ledger.restore(self.world.state["ledger"])
            slot = {"actor": actor, "start": start, "end": end}
            rows = ledger.reserve(operation_id, [slot], reason)
            self.world.state["ledger"] = ledger.snapshot()
            node = self.topology._node(
                "micro_time_reserved", start[:10], actor=actor,
                payload={"operation_id": operation_id, "start": start, "end": end, "reason": reason},
                causes=cause_ids,
            )
            self.world._record(
                "social_time_consequence",
                operation=operation_id,
                topology_node=node["id"],
                actor=actor,
            )
            return {"ledger": deepcopy(rows), "cause": node}
        try:
            return self._atomic(apply)
        except LedgerError as exc:
            raise WorldSocialAdapterError(str(exc)) from None

    def allocate_resource(self, operation_id, resource_id, actor_id, amount, date,
                          authority=None, required_permission=None, cause_ids=None):
        """Allocate topology capacity with optional World permission enforcement."""
        def apply():
            if required_permission:
                if not authority or not self.world.has_permission(authority, required_permission):
                    raise WorldSocialAdapterError("Authority lacks required permission")
            node = self.topology.allocate(
                resource_id, actor_id, amount, date, cause_ids
            )
            self.world._record(
                "shared_resource_consequence",
                operation=operation_id,
                topology_node=node["id"],
                resource=resource_id,
                actor=actor_id,
                amount=amount,
                authority=authority,
            )
            return node
        return self._atomic(apply)

    def release_resource(self, operation_id, resource_id, actor_id, amount, date,
                         cause_ids=None):
        def apply():
            node = self.topology.release(
                resource_id, actor_id, amount, date, cause_ids
            )
            self.world._record(
                "shared_resource_released",
                operation=operation_id,
                topology_node=node["id"],
                resource=resource_id,
                actor=actor_id,
                amount=amount,
            )
            return node
        return self._atomic(apply)
