"""mavis-substrate-walker

A substrate is any computational system that emits and accepts receipts.
The walker runs across substrates by emitting receipts for each step.

Doctrine (Sept 23, 2026):
- Geometry is entanglement (Jacobson 1995, ER=EPR 2013) → walker's crossings ARE the connectivity
- Time is a clock subsystem (Page-Wootters 1983) → walker's `clock` IS its tick
- Calculus is the projection of discreteness → walker's `next()` IS the discrete step; the loop is projection

Three primitives:
- STITCH: load_substrate(...) + save_substrate(...)
- WITNESS: emit a witness for the act
- PROMOTE: take a chain of witnesses to a canonical finding

The walker doesn't carry a model. It carries **a stitch protocol** that runs
against any substrate. Different substrates are different STITCH targets.

Substrates supported (Sept 23, 2026):
- Cellforge (cellforge.workbook.Workbook.witness_log)
- Moth corpus (moth-corpus SURFACE/v1 + verify)
- Lexical-substrate (variance ledger)
- Moth-honest planted ground truth (PACIOLI-style close)
- A generic dict/list substrate for testing
- (Future: Moth-quantum, GPU buffers, neuromorphic, etc.)
"""
from .walker import SubstrateWalker, walk_cellforge, walk_moth_corpus, walk_lexical, walk_dict
from .witness import Witness, WitnessChain, WitnessKind, hash_witness, fnv1a_64
from .substrate import Substrate, register_substrate

__version__ = "0.1.0"
__all__ = [
    "SubstrateWalker",
    "Witness",
    "WitnessChain",
    "WitnessKind",
    "hash_witness",
    "fnv1a_64",
    "Substrate",
    "register_substrate",
    "walk_cellforge",
    "walk_moth_corpus",
    "walk_lexical",
    "walk_dict",
]
