"""The walker — runs across substrates, emitting witnesses for each step.

Doctrine:
- A walk is a sequence of STITCH / WITNESS / PROMOTE primitives.
- Each step is witnessed (no silent operations).
- The walker's clock is the vector_clock advancement on each substrate.
- Promotion takes chains of witnesses to canonical findings.

The walker is **performative, not representational**. There is no model of
"a walked substrate". There is only the act of walking — captured in witnesses.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .witness import Witness, WitnessChain, WitnessKind
from .substrate import Substrate, SubstrateState, Step, Finding


@dataclass
class WalkStats:
    """Telemetry for a single walk."""
    substrate_id: str
    substrate_kind: str
    n_steps: int = 0
    n_witnesses: int = 0
    n_findings: int = 0
    started_at: str = ""
    duration_ms: float = 0.0


class SubstrateWalker:
    """Run a walk on a substrate, witnessing each step.

    Usage:
        walker = SubstrateWalker()
        chain = walker.walk(my_substrate)
        for finding in chain.findings:
            print(finding.description)

    The walker:
    1. Emits WITNESS/LOAD (capture substrate state)
    2. Iterates `walk()` steps; emits WITNESS/WALK for each
    3. Optionally calls `promote()` to graduate witnesses to a Finding
    4. Emits WITNESS/SAVE (save the new state back)

    All witnesses are anchored in the chain. Verifiable via `chain.verify()`.
    """

    def __init__(self, clock_id: str = "master"):
        self.clock_id = clock_id
        self.chains: Dict[str, WitnessChain] = {}
        self.stats: List[WalkStats] = []

    def make_chain(self, substrate_id: str) -> WitnessChain:
        """Allocate a new chain for a substrate."""
        chain = WitnessChain(substrate_id=substrate_id)
        self.chains[substrate_id] = chain
        return chain

    def walk(self, substrate: Substrate, max_steps: int = 100) -> "WalkResult":
        """Walk the substrate. Returns a result with the chain + findings."""
        from time import time
        stats = WalkStats(
            substrate_id=substrate.substrate_id,
            substrate_kind=substrate.substrate_kind,
            started_at=datetime.datetime.utcnow().isoformat() + "Z",
        )
        chain = self.make_chain(substrate.substrate_id)
        t0 = time()

        # STITCH step 1: LOAD
        try:
            state = substrate.load()
        except Exception as e:
            chain.append(Witness(
                kind=WitnessKind.LOAD,
                substrate_id=substrate.substrate_id,
                payload={"action": "load", "error": str(e)},
                parent_hashes=[],
            ))
            return WalkResult(chain=chain, findings=[], stats=self._finish(stats, chain, time() - t0))

        chain.append(Witness(
            kind=WitnessKind.LOAD,
            substrate_id=substrate.substrate_id,
            payload={"action": "load", "state_kind": state.substrate_kind, "data_size": len(str(state.data))},
            parent_hashes=[],
        ))
        stats.n_witnesses += 1

        # WALK steps
        steps: List[Step] = []
        try:
            for i in range(max_steps):
                step_results = substrate.walk()
                if not step_results:
                    break
                for step in step_results:
                    chain.append(Witness(
                        kind=WitnessKind.WALK if step.op_kind != "dispatch" else WitnessKind.DISPATCH,
                        substrate_id=substrate.substrate_id,
                        payload={
                            "step": i,
                            "op_id": step.op_id,
                            "op_kind": step.op_kind,
                            "n_inputs": len(step.inputs),
                            "n_outputs": len(step.outputs),
                            "cost_ms": step.cost_ms,
                        },
                        parent_hashes=[],
                    ))
                    stats.n_witnesses += 1
                    stats.n_steps += 1
                    steps.append(step)
        except Exception as e:
            chain.append(Witness(
                kind=WitnessKind.WALK,
                substrate_id=substrate.substrate_id,
                payload={"action": "walk", "error": str(e)},
                parent_hashes=[],
            ))
            return WalkResult(chain=chain, findings=[], stats=self._finish(stats, chain, time() - t0))

        # PROMOTE (optional, depends on substrate)
        finding: Optional[Finding] = None
        try:
            finding = substrate.promote([s for s in steps])
        except Exception as e:
            # Substrate may not support promote; that's OK.
            pass

        findings: List[Finding] = []
        if finding:
            chain.append(Witness(
                kind=WitnessKind.PROMOTE,
                substrate_id=substrate.substrate_id,
                payload={
                    "finding_id": finding.finding_id,
                    "polarity": finding.polarity,
                    "n_supporting": len(finding.supporting_witnesses),
                },
                parent_hashes=[],
            ))
            stats.n_witnesses += 1
            stats.n_findings += 1
            findings.append(finding)

        # STITCH step 2: SAVE
        try:
            substrate.save(state)
            chain.append(Witness(
                kind=WitnessKind.SAVE,
                substrate_id=substrate.substrate_id,
                payload={"action": "save", "state_kind": state.substrate_kind},
                parent_hashes=[],
            ))
            stats.n_witnesses += 1
        except Exception as e:
            chain.append(Witness(
                kind=WitnessKind.SAVE,
                substrate_id=substrate.substrate_id,
                payload={"action": "save", "error": str(e)},
                parent_hashes=[],
            ))

        return WalkResult(chain=chain, findings=findings, stats=self._finish(stats, chain, time() - t0))

    def _finish(self, stats: WalkStats, chain: WitnessChain, duration: float) -> WalkStats:
        stats.duration_ms = duration * 1000
        self.stats.append(stats)
        return stats


@dataclass
class WalkResult:
    chain: WitnessChain
    findings: List[Finding]
    stats: WalkStats


# ----- Concrete substrates -----


class DictSubstrate(Substrate):
    """The simplest walkable substrate — a Python dict.

    Demonstrates the protocol. Each walk step yields one key + value pair.
    Walk is finite — once every key has been yielded once, returns [].
    """

    substrate_id: str = "dict_substrate"
    substrate_kind: str = "dict"
    _counter: int = 0

    def __init__(self, data: Dict[str, Any], substrate_id: Optional[str] = None):
        if substrate_id is None:
            DictSubstrate._counter += 1
            substrate_id = f"dict_{DictSubstrate._counter}"
        self.substrate_id = substrate_id
        self.substrate_kind = "dict"
        self._keys = list(data.keys())
        self._data = dict(data)
        self._cursor = 0

    def load(self) -> SubstrateState:
        return SubstrateState(
            substrate_id=self.substrate_id,
            substrate_kind=self.substrate_kind,
            data=dict(self._data),
            vector_clock={"master": 0},
        )

    def save(self, state: SubstrateState) -> None:
        self._data = dict(state.data)
        self._keys = list(self._data.keys())
        self._cursor = 0

    def walk(self) -> List[Step]:
        if self._cursor >= len(self._keys):
            return []
        key = self._keys[self._cursor]
        value = self._data[key]
        self._cursor += 1
        outputs = {f"value_of_{key}": value}
        return [Step(
            op_id=f"read_{key}",
            op_kind="read",
            inputs={"key": key},
            outputs=outputs,
            cost_ms=0.001,
        )]

    def promote(self, steps: List[Step]) -> Optional[Finding]:
        if len(steps) >= 3:
            return Finding(
                finding_id=f"finding_{self.substrate_id}_{len(steps)}",
                substrate_id=self.substrate_id,
                polarity="positive",
                description=f"Walked {len(steps)} keys with at least 3 reading the substrate's content",
                supporting_witnesses=[],
            )
        return None


def walk_dict(data: Dict[str, Any]) -> WalkResult:
    """Convenience: walk a dict substrate."""
    walker = SubstrateWalker()
    return walker.walk(DictSubstrate(data))


def walk_cellforge(workbook) -> WalkResult:
    """Walk a cellforge Workbook as a substrate.

    This is the STITCH across cellforge. Each step in the walk yields one
    cell + its witness log. Each witness event in the Workbook.witness_log
    becomes a WITNESS/WALK.
    """
    from .substrate_cellforge import CellforgeSubstrate
    walker = SubstrateWalker()
    return walker.walk(CellforgeSubstrate(workbook))


def walk_moth_corpus(corpus_jsonl_path: str) -> WalkResult:
    """Walk a moth-corpus SURFACE/v1 jsonl as a substrate.

    Each step yields one row + its hash chain position.
    """
    from .substrate_moth_corpus import MothCorpusSubstrate
    walker = SubstrateWalker()
    return walker.walk(MothCorpusSubstrate(corpus_jsonl_path))


def walk_lexical(variance_ledger) -> WalkResult:
    """Walk a lexical-substrate variance ledger.

    Each step yields one entry + its Monotone property.
    """
    from .substrate_lexical import LexicalSubstrate
    walker = SubstrateWalker()
    return walker.walk(LexicalSubstrate(variance_ledger))
