#!/usr/bin/env python3
"""Self-test for per-query-cost-table (ALIGNMENT rule 97 three families).

Run:  python self_test.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cost_table as ct  # noqa: E402

results = []


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))


PRICES = {
    "model-a": {"input_per_mtok": 1.0, "output_per_mtok": 2.0, "as_of": "2026-10-11"},
    "model-b": {"input_per_mtok": 0.5, "output_per_mtok": 1.5, "as_of": "2026-10-11"},
}


def write_prices(tmp):
    p = os.path.join(tmp, "prices.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(PRICES, fh)
    return p


# ------------------------------------------------------------- functional ---
def test_functional(tmp):
    led = os.path.join(tmp, "l.jsonl")
    ct.record(led, "search", "model-a", 1_000_000, 500_000, ts=1.0)
    ct.record(led, "search", "model-a", 0, 0, ts=2.0)
    ct.record(led, "summary", "model-b", 2_000_000, 1_000_000, ts=3.0)

    recs, skipped = ct.load(led)
    record("functional: 3 records loaded, 0 skipped", len(recs) == 3 and skipped == 0)

    prices = ct.load_prices(write_prices(tmp))
    # search: 1M*1.0 + 0.5M*2.0 = 2.0 ; summary: 2M*0.5 + 1M*1.5 = 2.5
    tbl = ct.table(recs, prices)
    record("functional: cost math exact (search=2.0, summary=2.5)",
           "| search | 2 | 1000000 | 500000 | 2.0000 |" in tbl and
           "| summary | 1 | 2000000 | 1000000 | 2.5000 |" in tbl, tbl)

    warn = ct.budget_check(recs, prices, {"search": 1.0})
    record("functional: budget breach detected",
           len(warn) == 1 and warn[0].startswith("OVER BUDGET: search"))
    record("functional: within budget silent",
           ct.budget_check(recs, prices, {"search": 5.0}) == [])


# ----------------------------------------------------------- error paths ---
def test_errors(tmp):
    led = os.path.join(tmp, "err.jsonl")
    for name, fn in [
        ("negative tokens", lambda: ct.record(led, "t", "m", -1, 0)),
        ("float tokens", lambda: ct.record(led, "t", "m", 1.5, 0)),
        ("empty query_type", lambda: ct.record(led, "  ", "m", 1, 1)),
        ("empty model", lambda: ct.record(led, "t", "", 1, 1)),
        ("insane token count", lambda: ct.record(led, "t", "m", 10**9, 0)),
    ]:
        try:
            fn()
            record(f"error: {name} raises", False)
        except ct.LedgerError:
            record(f"error: {name} raises", True)

    bad_prices = os.path.join(tmp, "bad_prices.json")
    with open(bad_prices, "w", encoding="utf-8") as fh:
        json.dump({"model-x": {"input_per_mtok": 1.0}}, fh)  # missing output
    try:
        ct.load_prices(bad_prices)
        record("error: malformed price entry raises", False)
    except ct.LedgerError:
        record("error: malformed price entry raises", True)

    unknown = [{"query_type": "t", "model": "ghost-model",
                "input_tokens": 10, "output_tokens": 10}]
    tbl = ct.table(unknown, PRICES)
    record("error: unknown model shows '?' not invented price", "| ? |" in tbl)


# ------------------------------------------------------------ edge cases ---
def test_edges(tmp):
    # empty ledger
    recs, skipped = ct.load(os.path.join(tmp, "nothing.jsonl"))
    record("edge: missing ledger -> empty, no error", recs == [] and skipped == 0)
    tbl = ct.table([], PRICES)
    record("edge: empty table renders placeholder", "(no records)" in tbl)

    # corrupted lines skipped and counted
    led = os.path.join(tmp, "mixed.jsonl")
    with open(led, "w", encoding="utf-8") as fh:
        fh.write('{"query_type":"a","model":"model-a","input_tokens":1,"output_tokens":1}\n')
        fh.write("NOT JSON{{{\n")
        fh.write('{"query_type":"a","model":"model-a"}\n')  # missing fields
        fh.write("\n")  # blank line: ignored, not counted
    recs, skipped = ct.load(led)
    record("edge: 2 malformed lines skipped and counted, 1 loaded",
           len(recs) == 1 and skipped == 2)

    # 10k records performance sanity
    led10k = os.path.join(tmp, "big.jsonl")
    for i in range(10_000):
        ct.record(led10k, f"type{i % 7}", "model-a", 100, 200, ts=float(i))
    recs, _ = ct.load(led10k)
    tbl = ct.table(recs, PRICES)
    record("edge: 10k records aggregate to 7 types", tbl.count("| type") == 7)

    # zero-token record is valid
    led0 = os.path.join(tmp, "zero.jsonl")
    ct.record(led0, "cache-hit", "model-a", 0, 0)
    recs, _ = ct.load(led0)
    record("edge: zero-token record accepted",
           len(recs) == 1 and recs[0]["input_tokens"] == 0)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        test_functional(tmp)
        test_errors(tmp)
        test_edges(tmp)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
