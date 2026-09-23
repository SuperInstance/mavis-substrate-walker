"""Lexical-substrate as a walkable substrate.

A lexical-substrate variance ledger is monotone. Each entry has a stride-4 u32
ctx/tgt structure. We walk it entry by entry, with monotone checks.

The walker's job here is to verify monotone-ness (a key claim of lexical) and
promote to a Finding when all entries pass.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .substrate import Substrate, SubstrateState, Step, Finding, register_substrate


@register_substrate("lexical")
class LexicalSubstrate(Substrate):
    """A lexical-substrate variance ledger, walked entry by entry."""

    substrate_kind: str = "lexical"

    def __init__(self, variance_ledger: Sequence[float], substrate_id: Optional[str] = None):
        self.ledger = list(variance_ledger)
        self.substrate_id = substrate_id or f"lex_{id(variance_ledger)}"
        self._cursor: int = 0

    def load(self) -> SubstrateState:
        return SubstrateState(
            substrate_id=self.substrate_id,
            substrate_kind=self.substrate_kind,
            data={"n_entries": len(self.ledger)},
            vector_clock={"master": len(self.ledger)},
            metadata={"law": "monotone_variance"},
        )

    def save(self, state: SubstrateState) -> None:
        pass

    def walk(self) -> List[Step]:
        if self._cursor >= len(self.ledger):
            return []
        idx = self._cursor
        value = self.ledger[idx]
        # Check monotone-ness
        is_monotone = all(
            self.ledger[i] <= self.ledger[i + 1]
            for i in range(len(self.ledger) - 1)
        )
        self._cursor += 1
        return [Step(
            op_id=f"lex_entry_{idx}",
            op_kind="walk",
            inputs={"index": idx, "value": value},
            outputs={"is_monotone": is_monotone},
            cost_ms=0.01,
            metadata={"variance": value},
        )]

    def promote(self, steps: List[Step]) -> Optional[Finding]:
        # Promote only when we've walked everything AND it's monotone.
        if len(steps) == len(self.ledger):
            monotone = all(
                s.outputs.get("is_monotone", False)
                for s in steps
            )
            return Finding(
                finding_id=f"lex_promote_{self.substrate_id}",
                substrate_id=self.substrate_id,
                polarity="positive" if monotone else "negative",
                description=(
                    f"Walked {len(self.ledger)} lexical entries; "
                    f"monotone={'YES' if monotone else 'NO'}; "
                    f"polarity reflects the variance ledger's monotonicity."
                ),
                supporting_witnesses=[s.op_id for s in steps],
            )
        return None
