"""The witness primitive — every step in the walker emits one.

A witness is:
- A receipted observation of an act (load, save, walk, transform, ...)
- Hash-chained to parent witnesses (NO DELETION, parent-anchored)
- Content-addressed (FNV1a-64 over UTF-8 bytes by default)
- Promotable to a higher-tier finding if enough witnesses agree
"""
from __future__ import annotations

import datetime
import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# Bytes-law: FNV-1a 64. See cellforge canary 0x24a555471370b18d.
FNV1A64_OFFSET = 0xCBF29CE484222325
FNV1A64_PRIME = 0x100000001B3
MASK64 = 0xFFFFFFFFFFFFFFFF


def fnv1a_64(data: bytes) -> int:
    h = FNV1A64_OFFSET
    for byte in data:
        h ^= byte
        h = (h * FNV1A64_PRIME) & MASK64
    return h


def hash_witness(content: Dict[str, Any]) -> str:
    """FNV1a-64 hash of canonical-JSON content, as 16-hex."""
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{fnv1a_64(canonical):016x}"


class WitnessKind(str, Enum):
    """The kinds of acts the walker can witness."""
    LOAD = "load"           # substrate boundary crossed inward
    SAVE = "save"           # substrate boundary crossed outward
    WALK = "walk"           # one step inside a substrate
    STITCH = "stitch"       # cross-substrate composite
    PROMOTE = "promote"     # graduated to canonical finding
    WITHDRAW = "withdraw"   # cleanly excised
    DISPATCH = "dispatch"   # clock event (Page-Wootters)
    INFER = "infer"         # a derived observation


@dataclass
class Witness:
    """A receipted observation. Always anchored to parent witnesses."""
    kind: WitnessKind
    substrate_id: str
    payload: Dict[str, Any]  # the observation itself
    parent_hashes: List[str]  # anchoring
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    vector_clock: Dict[str, int] = field(default_factory=dict)
    content_hash: str = ""

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hash_witness({
                "kind": self.kind.value,
                "substrate_id": self.substrate_id,
                "payload": self.payload,
                "parent_hashes": self.parent_hashes,
                "vector_clock": self.vector_clock,
                "timestamp": self.timestamp,
            })

    def integrity_check(self) -> bool:
        """Verify content_hash matches the FNV1a-64 of the canonical payload."""
        expected = hash_witness({
            "kind": self.kind.value,
            "substrate_id": self.substrate_id,
            "payload": self.payload,
            "parent_hashes": self.parent_hashes,
            "vector_clock": self.vector_clock,
            "timestamp": self.timestamp,
        })
        return expected == self.content_hash


@dataclass
class WitnessChain:
    """An append-only, hash-chained sequence of witnesses.

    Same chain law as cellforge's Workbook.witness_log and moth-ledger's
    hash chain: each witness's content_hash depends on parent_hashes; tampering
    breaks the chain.
    """
    substrate_id: str = "chain"
    witnesses: List[Witness] = field(default_factory=list)
    vector_clock: Dict[str, int] = field(default_factory=dict)

    def append(self, w: Witness) -> None:
        """Anchor a new witness to the head of the chain."""
        w.parent_hashes = [w.content_hash for w in self.witnesses[-3:]]
        # Bump vector clock on the substrate_id's dimension
        self.vector_clock[w.substrate_id] = self.vector_clock.get(w.substrate_id, 0) + 1
        w.vector_clock = dict(self.vector_clock)
        # Recompute hash with the populated parent_hashes
        w.content_hash = hash_witness({
            "kind": w.kind.value,
            "substrate_id": w.substrate_id,
            "payload": w.payload,
            "parent_hashes": w.parent_hashes,
            "vector_clock": w.vector_clock,
            "timestamp": w.timestamp,
        })
        self.witnesses.append(w)

    def verify(self) -> bool:
        """Re-derive every hash from residue. Returns True if intact."""
        for i, w in enumerate(self.witnesses):
            if not w.integrity_check():
                return False
            # Check parent_anchor (each witness should reference the 3 preceding)
            expected_parents = [
                prev.content_hash
                for prev in self.witnesses[max(0, i - 3):i]
            ]
            if w.parent_hashes != expected_parents:
                return False
        return True

    def last_hash(self) -> Optional[str]:
        """The hash of the most recent witness (the chain's 'now')."""
        return self.witnesses[-1].content_hash if self.witnesses else None

    def size(self) -> int:
        return len(self.witnesses)

    def by_kind(self, kind: WitnessKind) -> List[Witness]:
        return [w for w in self.witnesses if w.kind == kind]
