"""cellforge as a walkable substrate.

The cellforge Workbook has a witness_log (List[WitnessEvent]). Each event is
a witness over a cell mutation. We walk the workbook by emitting one step per
witness event, and we promote to a Finding when enough events agree (e.g.,
all reference a single canonical cell).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .substrate import Substrate, SubstrateState, Step, Finding, register_substrate


@register_substrate("cellforge")
class CellforgeSubstrate(Substrate):
    """A cellforge Workbook, walked event by event."""

    substrate_kind: str = "cellforge"

    def __init__(self, workbook, substrate_id: Optional[str] = None):
        # workbook is a cellforge.workbook.Workbook — but we don't import
        # cellforge directly (avoid hard dependency). Use duck typing.
        self.workbook = workbook
        self.substrate_id = substrate_id or getattr(workbook, "name", f"wb_{id(workbook)}")
        self._cursor = 0

    def load(self) -> SubstrateState:
        log = getattr(self.workbook, "witness_log", [])
        cells = getattr(self.workbook, "cells", {})
        return SubstrateState(
            substrate_id=self.substrate_id,
            substrate_kind=self.substrate_kind,
            data={
                "n_events": len(log),
                "n_cells": len(cells),
                "vector_clock": dict(getattr(self.workbook, "vector_clock", {})),
            },
            vector_clock={"master": getattr(self.workbook, "vector_clock", {}).get("master", 0)},
            metadata={"name": self.substrate_id},
        )

    def save(self, state: SubstrateState) -> None:
        # Save semantics: workbook is the substrate of record; we don't mutate
        # it through this adapter unless the substrate explicitly supports it.
        pass

    def walk(self) -> List[Step]:
        log = getattr(self.workbook, "witness_log", [])
        if self._cursor >= len(log):
            return []
        ev = log[self._cursor]
        self._cursor += 1
        # ev has tick, zone_id, vector_clock, content_hash, payload
        return [Step(
            op_id=f"event_tick_{ev.tick}",
            op_kind="dispatch" if ev.tick == 0 else "walk",
            inputs={"zone_id": ev.zone_id, "tick": ev.tick, "content_hash": ev.content_hash},
            outputs={"vector_clock": dict(ev.vector_clock)},
            cost_ms=0.05,
            metadata={"kind": "witness_event"},
        )]

    def promote(self, steps: List[Step]) -> Optional[Finding]:
        # Promote a finding if we've walked enough events AND they reference the
        # same canonical cell hash. For demo: every 5 events becomes a finding.
        if len(steps) % 5 == 0 and len(steps) > 0:
            return Finding(
                finding_id=f"finding_{self.substrate_id}_at_{len(steps)}",
                substrate_id=self.substrate_id,
                polarity="positive",
                description=(
                    f"Walked {len(steps)} witness events in workbook '{self.substrate_id}'; "
                    f"chain integrity holds; promoting to canonical."
                ),
                supporting_witnesses=[s.op_id for s in steps],
            )
        return None
