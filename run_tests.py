"""Simple test runner for mavis-substrate-walker."""
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import test_walker as t


def main():
    tests = [
        ("fnv1a_64_canary", t.test_fnv1a_64_canary),
        ("witness_kind_enum", t.test_witness_kind_enum),
        ("hash_witness_deterministic", t.test_hash_witness_deterministic),
        ("witness_integrity_check", t.test_witness_integrity_check),
        ("chain_appends_and_anchors", t.test_chain_appends_and_anchors),
        ("chain_verify_detects_tamper", t.test_chain_verify_detects_tamper),
        ("chain_vector_clock_advances", t.test_chain_vector_clock_advances),
        ("walker_walks_dict", t.test_walker_walks_dict),
        ("walker_promotes_finding", t.test_walker_promotes_finding),
        ("walker_no_finding_for_tiny_dict", t.test_walker_no_finding_for_tiny_dict),
        ("walker_witness_kinds_proper", t.test_walker_witness_kinds_proper),
        ("lexical_substrate_monotone_promotes_positive", t.test_lexical_substrate_monotone_promotes_positive),
        ("lexical_substrate_non_monotone_promotes_negative", t.test_lexical_substrate_non_monotone_promotes_negative),
        ("multiple_walks_independent_chains", t.test_multiple_walks_independent_chains),
        ("cli_walk_dict_imports", t.test_cli_walk_dict_imports),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {name}: {type(e).__name__}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed}/{len(tests)} tests passed ({failed} failed)")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
