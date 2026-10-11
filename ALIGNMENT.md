# Alignment Audit (Rules 85-100 / 16 items)

Repo: per-query-cost-table — audited 2026-10-11 (post v0.1.1 revision)

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Safety/Ethics section | PASS | README "Limits & Second-order Effects": estimates≠bills, quality-drift from cost-optimization, ledger-as-sensitive-data |
| 2 | Privacy/redaction | PASS | grep scan → 0 secret patterns; contact only hcac4735@agent.qq.com; price examples explicitly synthetic; README flags ledger as user-data-sensitive |
| 3 | Copyright boundary | PASS | Source repo credited by link + structural restatement; specific-claim tagged [unverified]; no >50-word copied text; LICENSE (MIT) present |
| 4 | Fact-check labeling of numbers | PASS | 10k-record claim cites self-test + reproduce command; dashboard/provider claims tagged [unverified] or framed as mechanism; adoption-behavior claim tagged [estimated] |
| 5 | Confidence grading (≥2 explicit) | PASS | README bottom: High (aggregation/budget sufficiency, test-backed) + Medium (published-table trust effect, [estimated]) |
| 6 | Minimal Fallback (PLAN B) | PASS | "Minimal Fallback": echo-append + jq aggregation one-liner, zero Python |
| 7 | Quickstart timing | PASS | "~5 min" with per-step timings (2 s / 5 s / 1 s / 1 s); staged self-test → record → table → check |
| 8 | Design trade-off priority | PASS | "Design Trade-offs": honesty of numbers > simplicity > completeness > performance |
| 9 | CHANGELOG ≥2 iterations | PASS | v0.1.0 + v0.1.1 with named improvements (unknown-model `?` gap closed) |
| 10 | Exemption instruction (session rule) | N/A | Session-level governance; static repo not applicable |
| 11 | Time-sensitive data dated | PASS | Price entries require `as_of` per design; README guidance dated "as of 2026-10-11" |
| 12 | Explicit core assumptions (≥3) | PASS | "[Core Assumptions]": 4 items (query-type granularity, external prices, unknown≠invented, ledger scale window) |
| 13 | Three-family self-test, all PASS | PASS | `python self_test.py` → 16/16 (functional 4, error paths 7, extreme edges 5: missing ledger, empty table, corrupted lines counted, 10k records, zero tokens) |
| 14 | Socratic FAQ "When NOT to use" | PASS | FAQ: single-type workloads; synchronous per-request gating |
| 15 | ≥2 content iterations, ≥20% one dimension | PASS | v0.1.1: added unknown-model honesty behavior + test (15→16), README gained 2 second-order effects + FAQ item, all perf claims reconciled to reproduce commands — honesty/completeness dimension expanded beyond 20% |
| 16 | ≤60-word first paragraph with judgment | PASS | Opening paragraph: 57 words, ends with "you already have it" judgment |

Additional: Second-order effects section — PASS (measured-what's-priced drift; ledger retention risk).
