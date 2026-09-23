"""Unit tests for the substrate walker."""
from __future__ import annotations

import sys
import json
from pathlib import Path

# Allow importing the package directly from source.
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "src"))

from mavis_substrate_walker import (
    SubstrateWalker,
    Witness,
    WitnessChain,
    WitnessKind,
    hash_witness,
    fnv1a_64,
    walk_dict,
    walk_lexical,
)
from mavis_substrate_walker.substrate import (
    Substrate,
    SubstrateState,
    Step,
    Finding,
)
from mavis_substrate_walker.walker import DictSubstrate


# ----- Witness tests -----

def test_fnv1a_64_canary():
    """Canary: empty input → 0xCBF29CE484222325; preserved across the fleet."""
    h = fnv1a_64(b"")
    assert h == 0xCBF29CE484222325, f"expected 0xCBF29CE484222325, got {h:#x}"


def test_witness_kind_enum():
    """All witness kinds have string values."""
    assert WitnessKind.LOAD.value == "load"
    assert WitnessKind.WALK.value == "walk"
    assert WitnessKind.STITCH.value == "stitch"
    assert WitnessKind.PROMOTE.value == "promote"
    assert WitnessKind.DISPATCH.value == "dispatch"


def test_hash_witness_deterministic():
    """Same content -> same hash."""
    a = hash_witness({"kind": "walk", "step": 5})
    b = hash_witness({"kind": "walk", "step": 5})
    c = hash_witness({"kind": "walk", "step": 6})
    assert a == b
    assert a != c
    assert len(a) == 16  # 16-hex FNV1a-64


def test_witness_integrity_check():
    """Tampering with content breaks integrity_check."""
    w = Witness(
        kind=WitnessKind.WALK,
        substrate_id="test",
        payload={"step": 0},
        parent_hashes=[],
    )
    assert w.integrity_check()
    w.payload = {"step": 1}  # tamper
    assert not w.integrity_check()


def test_chain_appends_and_anchors():
    """Each witness in the chain references the 3 preceding via parent_hashes."""
    chain = WitnessChain(substrate_id="test_chain")
    for i in range(5):
        chain.append(Witness(
            kind=WitnessKind.WALK,
            substrate_id="test_chain",
            payload={"step": i},
            parent_hashes=[],
        ))
    assert chain.size() == 5
    assert chain.verify()
    # Check parent anchoring
    for i in range(len(chain.witnesses)):
        expected_parents = [
            chain.witnesses[j].content_hash for j in range(max(0, i - 3), i)
        ]
        assert chain.witnesses[i].parent_hashes == expected_parents


def test_chain_verify_detects_tamper():
    """Modifying a witness content should break verify()."""
    chain = WitnessChain(substrate_id="test_chain")
    for i in range(3):
        chain.append(Witness(
            kind=WitnessKind.WALK,
            substrate_id="test_chain",
            payload={"step": i},
            parent_hashes=[],
        ))
    assert chain.verify()
    # Tamper: change a payload
    chain.witnesses[1].payload = {"step": 999}
    # The integrity_check should now fail (hash was computed on original)
    assert not chain.witnesses[1].integrity_check()
    # Even without re-running integrity_check, the chain.verify() iterates and calls each
    assert not chain.verify()


def test_chain_vector_clock_advances():
    """The chain's vector_clock[substrate_id] should monotonically increase."""
    chain = WitnessChain(substrate_id="test_chain")
    for _ in range(5):
        chain.append(Witness(
            kind=WitnessKind.WALK,
            substrate_id="test_chain",
            payload={"step": 0},
            parent_hashes=[],
        ))
    assert chain.vector_clock["test_chain"] == 5
    # Each witness carries the clock state at its append-time
    for i, w in enumerate(chain.witnesses):
        assert w.vector_clock["test_chain"] == i + 1


# ----- Walker tests -----

def test_walker_walks_dict():
    """A walker over a dict substrate emits per-key witnesses."""
    data = {"a": 1, "b": 2, "c": 3}
    result = walk_dict(data)
    assert result.stats.n_steps == 3
    assert result.stats.n_witnesses >= 3  # LOAD + 3 WALK + SAVE
    assert result.chain.verify()


def test_walker_promotes_finding():
    """When a substrate is fully walked, the walker may emit a Finding."""
    # A dict substrate with >= 3 entries (DictSubstrate promotes when len(steps) >= 3)
    data = {"x": "alpha", "y": "beta", "z": "gamma", "w": "delta"}
    result = walk_dict(data)
    assert result.stats.n_findings >= 1
    f = result.findings[0]
    assert f.polarity == "positive"


def test_walker_no_finding_for_tiny_dict():
    """A dict with <3 entries doesn't trigger promote."""
    result = walk_dict({"only": 1})
    assert result.stats.n_findings == 0


def test_walker_witness_kinds_proper():
    """A walk emits LOAD, WALK, possibly PROMOTE, SAVE — in that order."""
    result = walk_dict({"a": 1, "b": 2})
    kinds = [w.kind for w in result.chain.witnesses]
    # First must be LOAD, last must be SAVE
    assert kinds[0] == WitnessKind.LOAD
    assert kinds[-1] == WitnessKind.SAVE
    # Middle kinds are WALK or PROMOTE
    for k in kinds[1:-1]:
        assert k in (WitnessKind.WALK, WitnessKind.PROMOTE, WitnessKind.DISPATCH)


def test_lexical_substrate_monotone_promotes_positive():
    """Monotone ledger → positive polarity finding."""
    result = walk_lexical([1.0, 2.0, 3.0, 5.0, 8.0])
    assert result.stats.n_findings >= 1
    f = result.findings[0]
    assert f.polarity == "positive"


def test_lexical_substrate_non_monotone_promotes_negative():
    """Non-monotone ledger → negative polarity finding (abstention)."""
    result = walk_lexical([5.0, 3.0, 4.0, 2.0])
    assert result.stats.n_findings >= 1
    f = result.findings[0]
    assert f.polarity == "negative"


def test_multiple_walks_independent_chains():
    """Each walk creates its own chain."""
    walker = SubstrateWalker()
    sub_a = DictSubstrate({"k": "a"})
    sub_b = DictSubstrate({"j": "b"})
    walker.walk(sub_a)
    walker.walk(sub_b)
    # Two chains in the walker
    assert len(walker.chains) == 2
    assert walker.chains[sub_a.substrate_id] != walker.chains[sub_b.substrate_id]


# ----- CLI smoke test -----

def test_cli_walk_dict_imports():
    """Just verify the CLI module imports without error."""
    from mavis_substrate_walker.__main__ import (
        cmd_walk_dict,
        cmd_walk_lexical,
        main,
    )
    assert callable(cmd_walk_dict)
    assert callable(cmd_walk_lexical)
    assert callable(main)


if __name__ == "__main__":
    # Allow running without pytest.
    import traceback
    tests = [
        test_fnv1a_64_canary,
        test_witness_kind_enum,
        test_hash_witness_deterministic,
        test_witness_integrity_check,
        test_chain_appends_and_anchors,
        test_chain_verify_detects_tamper,
        test_chain_vector_clock_advances,
        test_walker_walks_dict,
        test_walker_promotes_finding,
        test_walker_no_finding_for_tiny_dict,
        test_walker_witness_kinds_proper,
        test_lexical_substrate_monotone_promotes_positive,
        test_lexical_substrate_non_monotone_promotes_negative,
        test_multiple_walks_independent_chains,
        test_cli_walk_dict_imports,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {t.__name__}: {type(e).__name__}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed}/{passed+failed} tests passed ({failed} failed)")
    sys.exit(0 if failed == 0 else 1)
