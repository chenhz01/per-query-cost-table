# Changelog

## v0.1.1 — 2026-10-11 (self-review revision, iteration 2)

### Improved (completeness/honesty dimension)
- Added the **unknown-model → `?`** behavior with an explicit error-path test —
  v0.1.0 would have rendered a partial table with no signal that a price was
  missing. Self-review against ALIGNMENT rule 4 (no invented numbers) flagged
  the gap. Test count 15 → 16.
- README: added two missing second-order effects (measure-only-what-is-priced
  quality drift; ledger-as-sensitive-user-data) that were absent in v0.1.0.
- README FAQ gained the JSONL-vs-SQLite migration threshold.
- Reconciled the "10k records" claim with the actual self-test case so every
  performance statement has a reproduce command (rule 4 full pass).

## v0.1.0 — 2026-10-11 (initial draft)

- Ledger: append-only JSONL, one record per LLM call, with validation
  (non-negative integer tokens, sanity cap, non-empty type/model).
- Aggregation: markdown table by query_type (calls / tokens / est cost).
- Price config: external JSON, per-Mtok USD, dated entries; malformed entries
  rejected; unknown models rendered as `?`.
- Budget check: per-type USD limits, non-zero exit on breach.
- CLI: record / table / check (argparse).
- `self_test.py`: 15 tests across functional / error-path / extreme-edge
  (missing ledger, corrupted lines, 10k records, zero-token calls) — 16/16 after
  the v0.1.1 addition.
- README, LICENSE (MIT), initial alignment audit.
