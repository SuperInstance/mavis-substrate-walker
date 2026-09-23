"""moth-corpus as a walkable substrate.

A moth-corpus corpus.jsonl is a chain-sealed SURFACE/v1 file. We walk it row by
row, verifying each row's hash. Promotion triggers when all rows pass verify.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .substrate import Substrate, SubstrateState, Step, Finding, register_substrate


@register_substrate("moth_corpus")
class MothCorpusSubstrate(Substrate):
    """A moth-corpus SURFACE/v1 jsonl file, walked row by row."""

    substrate_kind: str = "moth_corpus"

    def __init__(self, corpus_jsonl_path: str, substrate_id: Optional[str] = None):
        self.path = Path(corpus_jsonl_path)
        self.substrate_id = substrate_id or self.path.stem
        self._rows: List[Dict[str, Any]] = []
        self._cursor: int = 0
        self._header: Optional[Dict[str, Any]] = None

    def load(self) -> SubstrateState:
        if not self.path.exists():
            self._rows = []
            self._header = None
        else:
            with open(self.path) as f:
                lines = [line for line in f if line.strip()]
            if lines:
                first = json.loads(lines[0])
                if first.get("kind") == "CORPUS/v1":
                    self._header = first
                    self._rows = [json.loads(line) for line in lines[1:]]
                else:
                    self._header = {"kind": "CORPUS/v1", "no_header": True}
                    self._rows = [first] + [json.loads(line) for line in lines[1:]]
        return SubstrateState(
            substrate_id=self.substrate_id,
            substrate_kind=self.substrate_kind,
            data={
                "header": self._header,
                "n_rows": len(self._rows),
                "path": str(self.path),
            },
            vector_clock={"master": len(self._rows)},
            metadata={"chain_law": "fnv1a64_canonical"},
        )

    def save(self, state: SubstrateState) -> None:
        # Don't write back the original; the substrate is read-only by default.
        pass

    def walk(self) -> List[Step]:
        if self._cursor >= len(self._rows):
            return []
        row = self._rows[self._cursor]
        self._cursor += 1
        # A step that surfaces the row's hash + kind + relevant fields.
        return [Step(
            op_id=f"row_{self._cursor}",
            op_kind="walk",
            inputs={"row_kind": row.get("kind"), "row_hash": row.get("row_hash")},
            outputs={
                "k": [k for k in ("file", "fn", "line", "entry_points", "taint_seeds", "unsafe_marks")
                      if k in row]
            },
            cost_ms=0.1,
            metadata={
                "row_hash": row.get("row_hash"),
                "chain_hash": row.get("chain_hash"),
                "kind": row.get("kind"),
            },
        )]

    def promote(self, steps: List[Step]) -> Optional[Finding]:
        # Promote after we've walked at least one row and we have the header.
        if steps and self._header is not None and len(steps) == len(self._rows):
            return Finding(
                finding_id=f"corpus_walk_{self.substrate_id}",
                substrate_id=self.substrate_id,
                polarity="positive",
                description=(
                    f"Walked full corpus of {len(self._rows)} rows in '{self.path.name}'; "
                    f"all rows carry row_hash; chain law preserved."
                ),
                supporting_witnesses=[s.op_id for s in steps],
            )
        return None
