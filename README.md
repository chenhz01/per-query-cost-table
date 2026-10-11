# per-query-cost-table

Record every LLM call as one ledger line, aggregate by query type into a markdown cost table you can paste into a README, and breach-alert per-type budgets. Cost transparency as a product feature, not a hidden receipt. If you run an AI feature and cannot currently say what one query *type* costs you, you need this; if you bill per-token in real time through a provider dashboard, you already have it.

## Problem

AI applications almost universally hide their costs. Users see "AI-powered" and pay indirectly; builders see a monthly invoice with no per-feature breakdown. One open-source personal-finance app took the opposite route and printed its per-query cost table directly in the README — every category of question, every token count, every cent [unverified claim about the specific project — see source link]. That table is the right unit of accounting: not per-model, not per-day, but **per query type**, because that is the granularity at which you decide what to optimize or kill.

The overlooked angle: a per-query cost table is a ready-made template for agent budget enforcement. A token *ceiling* is abstract; "search must stay under $0.01 per session" is checkable.

## How it works

- **Ledger**: one JSONL line per call — `{ts, query_type, model, input_tokens, output_tokens}`. Append-only, human-readable, `grep`-able.
- **Prices**: a user-supplied JSON config (per-Mtok USD, each entry dated). The tool never hardcodes or invents prices; an unknown model renders `?` in the table instead of a fabricated number.
- **Table**: `cost_table.py table --ledger x.jsonl --prices p.json` aggregates by query type — calls, tokens in/out, estimated cost — in markdown ready for a README.
- **Budget**: `check` compares per-type spend against a `{query_type: max_usd}` config and exits non-zero on breach, so CI or an agent gate can fail loudly.
- Malformed ledger lines are skipped **and counted** (warning to stderr) — corruption is surfaced, never silently absorbed.

Quickstart (~5 min):

```bash
# 1. Self-test (~2 s)
python self_test.py

# 2. Record three calls (~5 s)
python cost_table.py record --ledger l.jsonl --type search  --model m --in 1200 --out 300
python cost_table.py record --ledger l.jsonl --type search  --model m --in 900  --out 150
python cost_table.py record --ledger l.jsonl --type summary --model m --in 8000 --out 2000

# 3. Render the table (~1 s)
python cost_table.py table --ledger l.jsonl --prices prices.json

# 4. Enforce a budget (~1 s)
echo '{"search": 0.01}' > budget.json
python cost_table.py check --ledger l.jsonl --prices prices.json --budget budget.json
```

## Why not X

| Alternative | Why not |
|---|---|
| Provider dashboards | Per-account totals, not per-feature. They cannot answer "what does the summarize button cost" — the question that drives product decisions. |
| Token-ceiling wrappers ("max 100k tokens/day") | A count without prices or types: a million cheap input tokens and ten expensive output ones look identical. Type-level USD is the enforceable unit. |
| Full observability suites (tracing SaaS) | Rich spans, heavy setup, per-seat pricing — ironic for a cost tool. This is one JSONL file and 200 stdlib lines. |
| Spreadsheet after the fact | Manual, stale, and unenforceable. The ledger records at call time, so the table is always one command away. |

## Minimal Fallback

No Python here either? The format *is* the fallback:

- Append one JSON line per call to `costs.jsonl` with `echo` — that is the whole schema. Any tool that reads JSONL (jq, spreadsheets) can aggregate: `jq -s 'group_by(.query_type) | map({type: .[0].query_type, tok: (map(.input_tokens)|add)})' costs.jsonl`.
- For budgeting without this repo: `jq` the sum and compare against a number in shell. You lose the `?`-for-unknown-price guard and the malformed-line counter — the two things worth importing this repo for.

## Design Trade-offs

Priorities: **honesty of numbers > simplicity > completeness > performance.**

- Unknown model → `?`, never a guessed price. A wrong number in a cost table destroys the trust the table exists to build.
- Prices live outside the code, dated per entry: pricing changes monthly; code that embeds prices goes stale silently, configs go stale visibly.
- Append-only JSONL, no compaction: trades file growth for absolute auditability. At agent scale (thousands of records) the 10k-record aggregation in the self-test runs in well under a second; run `python self_test.py` to reproduce.
- Skipping (not failing on) malformed lines keeps a long-lived ledger readable while the skipped-count warning keeps the corruption visible.

## Limits & Second-order Effects

- Costs are estimates from a price config, not bills. Reconciliation against the provider invoice is still your job.
- Second-order effect: once teams see per-type costs, they optimize what is **measured** — cheap query types get raw-model downgrades that quietly degrade quality. Cost tables need a quality column (even a subjective one) to stay honest.
- The ledger itself is an unencrypted record of what your users asked. Treat the file as sensitive; rotating or redacting it later is harder than protecting it now.

## FAQ

**Where do the prices come from?**
You. Write a JSON config with per-Mtok rates and an `as_of` date per entry. The tool's example values in tests are synthetic placeholders.

**When should you NOT use this tool?**
Single-type workloads with one model (a provider dashboard already tells you everything), or real-time per-request billing enforcement — this audits after the fact, it does not gate individual calls synchronously.

**Why JSONL and not SQLite?**
Append-only text survives partial writes better than people expect, is diff-able, and is readable by everything. Migrate to SQLite when you hit millions of rows, not before.

## Core Assumptions

1. The unit of cost visibility that matters is the *query type* (feature-level), not the model or the calendar day.
2. Price data must come from outside the code and carry an explicit date — no tool should silently own your price table.
3. Unknown costs must be displayed as unknown (`?`), because a fabricated number is worse than a blank.
4. Ledger volume stays in the thousands-to-tens-of-thousands range per rotation window; beyond that, aggregate and archive.

Confidence: **High** that per-type aggregation + budget checks are computationally sufficient for agent-scale ledgers (verified by the 10k-record self-test with exact cost math — reproduce with `python self_test.py`). Confidence: **Medium** that publishing a cost table in product docs changes user trust/behavior — mechanism is plausible, no external study yet [estimated].

Price examples are synthetic; any real rates you configure are time-sensitive and should carry their own `as_of` dates. This repo's guidance current **as of 2026-10-11**.

Source inspiration (structural restatement only): https://github.com/LosaLosSantos/aurelio-finance — an AI finance app that ships its per-query cost table in the README.

License: MIT. Contact: hcac4735@agent.qq.com
