"""Substrate protocol — any system that can be walked has these methods.

A substrate is a cell that the walker addresses. Loading it means: emit a
WITNESS/LOAD, capture a snapshot of its state, set up the vector clock. Saving
means: emit a WITNESS/SAVE, write back the snapshot (or a derived state).
Walking means: stepping through the substrate's internal operations one step
at a time, emitting WITNESS/WALK for each.

The substrate is its OWN substrate. The walker doesn't carry a model; it carries
a stitch protocol. Each substrate's logic is in the substrate itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SubstrateState:
    """A snapshot of substrate state — JSON-serializable for portability.

    Substrates that aren't JSON-native (GPU buffers, quantum states) are
    expected to serialize their state to a portable form. Moth-quantum, for
    example, would serialize as a list of complex amplitudes + gate history.
    """
    substrate_id: str
    substrate_kind: str  # 'cellforge', 'moth_corpus', 'lexical', 'moth_quantum', etc.
    data: Any  # the substrate-specific payload
    vector_clock: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Substrate:
    """The protocol every walkable substrate implements.

    Methods:
        load(): SubstrateState — read current state, return a portable snapshot.
        save(state): None — apply a snapshot back to the substrate (or stage).
        walk() -> List[Step]: walk one step (or many), returning ops to witness.
        promote(witnesses) -> Optional[Finding]: graduate to canonical.

    These methods are NOT called directly by the walker; the walker emits a
    witness for each invocation. The substrate MUST be idempotent or the walker
    can't safely retry.
    """

    substrate_id: str
    substrate_kind: str

    def load(self) -> SubstrateState:
        ...

    def save(self, state: SubstrateState) -> None:
        ...

    def walk(self) -> List["Step"]:
        ...

    def promote(self, witnesses: List["Step"]) -> Optional["Finding"]:
        ...


@dataclass
class Step:
    """A single observable step the walker can witness."""
    op_id: str
    op_kind: str  # 'read', 'write', 'transform', 'dispatch'
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    cost_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Finding:
    """A canonical finding — what promoters output."""
    finding_id: str
    substrate_id: str
    polarity: str  # 'positive' (restraint) | 'negative' (abstention)
    description: str
    supporting_witnesses: List[str]  # content_hashes
    content_hash: str = ""

    def __post_init__(self):
        if not self.content_hash:
            import hashlib, json
            canonical = json.dumps({
                "finding_id": self.finding_id,
                "substrate_id": self.substrate_id,
                "polarity": self.polarity,
                "description": self.description,
                "supporting_witnesses": self.supporting_witnesses,
            }, sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.content_hash = hashlib.sha256(canonical).hexdigest()[:16]


# Registry of substrate kinds (for the walker to look up at run time).
_REGISTRY: Dict[str, type] = {}


def register_substrate(kind: str):
    """Decorator — register a Substrate subclass under a kind name."""
    def wrap(cls: type) -> type:
        _REGISTRY[kind] = cls
        return cls
    return wrap


def get_substrate(kind: str) -> Optional[type]:
    return _REGISTRY.get(kind)
