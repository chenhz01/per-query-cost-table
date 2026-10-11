#!/usr/bin/env python3
"""per-query-cost-table: a public, per-query-type cost ledger for AI apps.

Every LLM call is recorded as one JSONL line (query type, model, tokens).
The ledger aggregates into a markdown cost table — the kind you can paste
into a README — and checks per-type budgets. Cost transparency as a feature,
not a hidden receipt.

Pure stdlib. Prices live in a user-supplied config (never hardcoded), each
entry dated, so the tool never silently lies about money.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

MAX_TOKENS_PER_CALL = 100_000_000  # sanity cap


class LedgerError(Exception):
    pass


def record(ledger_path: str, query_type: str, model: str,
           input_tokens: int, output_tokens: int, ts: float | None = None) -> dict:
    if not query_type or not query_type.strip():
        raise LedgerError("query_type must be non-empty")
    if not model or not model.strip():
        raise LedgerError("model must be non-empty")
    for name, v in (("input_tokens", input_tokens), ("output_tokens", output_tokens)):
        if not isinstance(v, int) or v < 0:
            raise LedgerError(f"{name} must be a non-negative integer")
        if v > MAX_TOKENS_PER_CALL:
            raise LedgerError(f"{name} exceeds sanity cap ({MAX_TOKENS_PER_CALL})")
    rec = {
        "ts": ts if ts is not None else time.time(),
        "query_type": query_type.strip(),
        "model": model.strip(),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
    with open(ledger_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def load(ledger_path: str) -> tuple[list[dict], int]:
    """Returns (records, skipped_count). Malformed lines are skipped, counted,
    never silently dropped."""
    records, skipped = [], 0
    if not os.path.exists(ledger_path):
        return records, skipped
    with open(ledger_path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if not isinstance(rec.get("query_type"), str) or \
                   not isinstance(rec.get("model"), str) or \
                   not isinstance(rec.get("input_tokens"), int) or \
                   not isinstance(rec.get("output_tokens"), int):
                    raise ValueError("missing or mistyped fields")
                records.append(rec)
            except (json.JSONDecodeError, ValueError):
                skipped += 1
    return records, skipped


def load_prices(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            prices = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise LedgerError(f"cannot read prices: {exc}") from exc
    for model, p in prices.items():
        if model.startswith("_"):
            continue
        if not isinstance(p, dict) or \
           "input_per_mtok" not in p or "output_per_mtok" not in p:
            raise LedgerError(f"price entry for {model!r} malformed")
    return prices


def estimate_cost(rec: dict, prices: dict) -> float | None:
    p = prices.get(rec["model"])
    if p is None:
        return None
    return (rec["input_tokens"] / 1e6 * p["input_per_mtok"]
            + rec["output_tokens"] / 1e6 * p["output_per_mtok"])


def table(records: list[dict], prices: dict | None = None) -> str:
    """Aggregate by query_type -> markdown table. Unknown models report '?'
    instead of inventing a price."""
    agg: dict[str, dict] = {}
    for r in records:
        a = agg.setdefault(r["query_type"], {
            "calls": 0, "in": 0, "out": 0, "cost": 0.0, "cost_known": True})
        a["calls"] += 1
        a["in"] += r["input_tokens"]
        a["out"] += r["output_tokens"]
        if prices is not None:
            c = estimate_cost(r, prices)
            if c is None:
                a["cost_known"] = False
            else:
                a["cost"] += c

    header_cost = "est cost ($)" if prices is not None else ""
    lines = ["| query_type | calls | input tokens | output tokens |"
             + (f" {header_cost} |" if prices is not None else ""),
             "|---|---|---|---|" + ("---|" if prices is not None else "")]
    for qt in sorted(agg):
        a = agg[qt]
        row = (f"| {qt} | {a['calls']} | {a['in']} | {a['out']}")
        if prices is not None:
            cell = f"{a['cost']:.4f}" if a["cost_known"] else "?"
            row += f" | {cell}"
        lines.append(row + " |")
    if not agg:
        lines.append("| (no records) | 0 | 0 | 0 |" + (" 0 |" if prices is not None else ""))
    return "\n".join(lines)


def budget_check(records: list[dict], prices: dict, budget: dict[str, float]) -> list[str]:
    """Return warning lines for query types whose estimated cost exceeds budget."""
    warnings = []
    agg: dict[str, float] = {}
    for r in records:
        c = estimate_cost(r, prices)
        if c is not None:
            agg[r["query_type"]] = agg.get(r["query_type"], 0.0) + c
    for qt, limit in budget.items():
        spent = agg.get(qt, 0.0)
        if spent > limit:
            warnings.append(
                f"OVER BUDGET: {qt} spent ${spent:.4f} > limit ${limit:.4f}")
    return warnings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="cost_table", description="Per-query-type cost ledger for AI apps.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("record")
    p.add_argument("--ledger", required=True)
    p.add_argument("--type", dest="query_type", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--in", dest="input_tokens", type=int, required=True)
    p.add_argument("--out", dest="output_tokens", type=int, required=True)

    p = sub.add_parser("table")
    p.add_argument("--ledger", required=True)
    p.add_argument("--prices", help="JSON price config (per-Mtok USD)")

    p = sub.add_parser("check")
    p.add_argument("--ledger", required=True)
    p.add_argument("--prices", required=True)
    p.add_argument("--budget", required=True,
                   help="JSON {query_type: max_usd}")

    args = ap.parse_args(argv)
    try:
        if args.cmd == "record":
            rec = record(args.ledger, args.query_type, args.model,
                         args.input_tokens, args.output_tokens)
            print(f"recorded: {rec['query_type']} in={rec['input_tokens']} "
                  f"out={rec['output_tokens']}")
            return 0
        if args.cmd == "table":
            records, skipped = load(args.ledger)
            prices = load_prices(args.prices) if args.prices else None
            if skipped:
                print(f"warning: {skipped} malformed line(s) skipped", file=sys.stderr)
            print(table(records, prices))
            return 0
        if args.cmd == "check":
            records, _ = load(args.ledger)
            prices = load_prices(args.prices)
            with open(args.budget, "r", encoding="utf-8") as fh:
                budget = json.load(fh)
            warnings = budget_check(records, prices, budget)
            for w in warnings:
                print(w)
            print("OK" if not warnings else f"{len(warnings)} budget breach(es)")
            return 0 if not warnings else 2
    except (LedgerError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
