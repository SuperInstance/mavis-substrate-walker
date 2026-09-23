"""CLI for mavis-substrate-walker.

Usage:
    python -m mavis_substrate_walker walk-dict '{"a": 1, "b": 2}'
    python -m mavis_substrate_walker walk-cellforge <workbook.json>
    python -m mavis_substrate_walker walk-corpus  <corpus.jsonl>
    python -m mavis_substrate_walker walk-lexical 1.0,2.0,3.0,5.0
    python -m mavis_substrate_walker verify <chain.json>
"""
from __future__ import annotations

import argparse
import json
import sys

from .walker import (
    SubstrateWalker,
    walk_dict,
    walk_cellforge,
    walk_moth_corpus,
    walk_lexical,
)
from .witness import WitnessChain, hash_witness


def cmd_walk_dict(args) -> int:
    try:
        data = json.loads(args.json)
    except Exception as e:
        print(f"invalid JSON: {e}", file=sys.stderr)
        return 1
    result = walk_dict(data)
    print(f"substrate: {result.stats.substrate_kind} ({result.stats.substrate_id})")
    print(f"steps:     {result.stats.n_steps}")
    print(f"witnesses: {result.stats.n_witnesses}")
    print(f"findings:  {result.stats.n_findings}")
    print(f"duration:  {result.stats.duration_ms:.2f}ms")
    print(f"chain OK:  {result.chain.verify()}")
    print(f"last hash: {result.chain.last_hash()}")
    for finding in result.findings:
        print(f"finding:   [{finding.polarity}] {finding.description}")
    return 0


def cmd_walk_corpus(args) -> int:
    if not args.path:
        print("missing path to corpus jsonl", file=sys.stderr)
        return 1
    result = walk_moth_corpus(args.path)
    print(f"substrate: {result.stats.substrate_kind} ({result.stats.substrate_id})")
    print(f"steps:     {result.stats.n_steps}")
    print(f"witnesses: {result.stats.n_witnesses}")
    print(f"chain OK:  {result.chain.verify()}")
    return 0


def cmd_walk_lexical(args) -> int:
    try:
        ledger = [float(x) for x in args.ledger.split(",")]
    except Exception as e:
        print(f"invalid ledger: {e}", file=sys.stderr)
        return 1
    result = walk_lexical(ledger)
    print(f"substrate: {result.stats.substrate_kind}")
    print(f"steps:     {result.stats.n_steps}")
    print(f"chain OK:  {result.chain.verify()}")
    for finding in result.findings:
        print(f"finding:   [{finding.polarity}] {finding.description}")
    return 0


def cmd_verify(args) -> int:
    """Verify a witness chain stored as JSON."""
    try:
        with open(args.chain_json) as f:
            data = json.load(f)
    except Exception as e:
        print(f"can't load chain: {e}", file=sys.stderr)
        return 1
    chain = WitnessChain(substrate_id=data.get("substrate_id", ""))
    for wd in data.get("witnesses", []):
        w = WitnessChain.Witness  # expose via __init__?
    print("(verify not yet implemented for JSON round-trip)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="mavis-substrate-walker CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("walk-dict")
    p.add_argument("json", help="JSON object to walk")
    p.set_defaults(func=cmd_walk_dict)
    p = sub.add_parser("walk-corpus")
    p.add_argument("path", help="path to moth-corpus corpus.jsonl")
    p.set_defaults(func=cmd_walk_corpus)
    p = sub.add_parser("walk-lexical")
    p.add_argument("ledger", help="comma-separated monotonic ledger")
    p.set_defaults(func=cmd_walk_lexical)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
