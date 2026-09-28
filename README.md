# mavis-substrate-walker

**Substrate-agnostic walker for the Quilt.** STITCH / WITNESS / PROMOTE primitives; walks cellforge, moth-corpus, lexical-substrate, dict substrates.

## Quickstart (30 seconds)

```bash
git clone https://github.com/SuperInstance/mavis-substrate-walker.git
cd mavis-substrate-walker
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Try it — expected: 6 witnesses, 1 finding, "chain OK: True"
python -m mavis_substrate_walker walk-dict '{"a":1,"b":2,"c":3}'

# Full suite — expected: "15/15 tests passed (0 failed)"
python run_tests.py
```

No dependencies beyond the standard library. If both expected outputs match, the walker is working.

## Doctrine

A substrate is any computational system that emits and accepts receipts. The walker runs across substrates by emitting a receipted witness for each step.

Three primitives survive every layer of the Quilt:

1. **STITCH** — load a substrate; save it back; emit a witness for the act
2. **WITNESS** — record an observation; emit a receipt; chain to its parents
3. **PROMOTE** — graduate receipts from one tier to another

This tracks three physical primitives in the deep-research foundations.
The walker treats any system that can emit and accept receipts as a
substrate — a Python dict qualifies; a quantum device qualifies.

| physical primitive | inter-logistical primitive |
|--------------------|----------------------------|
| Geometry (entanglement → wormhole) | STITCH |
| Time (Page-Wootters clock subsystem) | WITNESS |
| Calculus-projection (Jacobson, Padmanabhan) | PROMOTE |

## One walk, decoded

`python -m mavis_substrate_walker walk-dict '{"a":1,"b":2,"c":3}'`
produces six witnesses — every one hash-chained to its parents:

```
[0] load     loaded dict substrate, 24 bytes
[1] walk     step 0: read_a (read) — 1 in, 1 out
[2] walk     step 1: read_b (read) — 1 in, 1 out
[3] walk     step 2: read_c (read) — 1 in, 1 out
[4] promote  finding finding_dict_1_3 [positive]
[5] save     saved dict substrate back
chain.verify(): True
```

Line by line: **[0] STITCH-LOAD** crosses into the substrate and captures
its state; **[1]–[3] WITNESS** record each step the substrate yields (one
key-read each); **[4] PROMOTE** graduates the witness chain to a `Finding`
because ≥3 steps agreed; **[5] STITCH-SAVE** crosses back out, state
persisted. Six witnesses, one chain, zero un-receipted operations.

## Substrates

- `cellforge` (cellforge.workbook.Workbook.witness_log)
- `moth_corpus` (moth-corpus SURFACE/v1 corpus.jsonl)
- `lexical` (lexical-substrate variance ledger)
- `dict` (a Python dict, for testing)
- (Future: Moth quantum, GPU buffers, neuromorphic substrates)

## Usage

```python
from mavis_substrate_walker import walk_dict, walk_lexical, walk_moth_corpus

# Walk a dict
result = walk_dict({"a": 1, "b": 2, "c": 3})
print(result.stats.n_steps, result.stats.n_findings)
print(result.chain.verify())

# Walk a lexical-substrate monotone ledger
result = walk_lexical([1.0, 2.0, 3.0, 5.0])
for finding in result.findings:
    print(f"[{finding.polarity}] {finding.description}")

# Walk a moth-corpus file
result = walk_moth_corpus("path/to/corpus.jsonl")
print(result.chain.verify())

# Walk a cellforge Workbook (any object with a witness_log)
import cellforge
wb = cellforge.Workbook(name="my-wb")
for i in range(5):
    wb.record_witness(zone_id="A", payload={"step": i})
from mavis_substrate_walker import walk_cellforge
result = walk_cellforge(wb)
```

## CLI

```bash
python -m mavis_substrate_walker walk-dict '{"a":1,"b":2,"c":3}'
python -m mavis_substrate_walker walk-lexical 1.0,2.0,3.0,5.0
python -m mavis_substrate_walker walk-corpus examples/corpus.jsonl   # bundled sample corpus
```

## Tests

```bash
python run_tests.py
```

15 tests covering: FNV1a-64 canary (matches cellforge canary `0x24a555471370b18d`), witness integrity, chain anchoring, vector clock advancement, walker ordering, finding promotion, polarity classification.

## Cross-project bridges

- **cellforge** canary `0x24a555471370b18d` preserved (this is the fleet polyformalism canary)
- **moth-corpus** uses `SURFACE/v1` chain law
- **moth-honest** polarity (`positive`/`negative`) preserved as `Finding.polarity`
- **lexical-substrate** `variance ledger (monotone)` check is built into `LexicalSubstrate.promote()`
- **mavis-fleet** can call `walk_*()` to chain cross-substrate operations

## The walker is performative, not representational

There is no model of "a walked substrate". There is only the act of walking — captured in witnesses. The walker carries **a stitch protocol** that runs against any substrate; not a model. Different substrates are different STITCH targets. Cross-substrate work is **STITCH + WITNESS + PROMOTE**. That's it.

## Versions

- v0.1.0 — initial: dict, lexical, moth-corpus, cellforge substrates; FNV1a-64 canary preserved; 15 tests.
