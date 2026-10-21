# Transaction label reviewer
(Readme and solution wrote in english, for the only reason of that usually prompt in english, most inner documentation in my context is in english
and code is english-based, just in case, a spanish version are also attached)

An LLM reviewer for a legacy keyword engine that labels small-business bank transactions,
plus what its corrections do to a funding offer. Answer to the Fundo AI Engineer take-home.
Design, results and trade-offs are in [SOLUTION.md](SOLUTION.md).

Needs Python 3.10 or newer. Reproducing the results needs nothing else: no packages, no API key.

## Reproduce the results (no API key)

```bash
git clone <this repo> && cd niuro-challenge
python3 run.py            # rewrites output/report.md and output/flags.json from cache/
git diff --stat output/   # empty: same result as committed
python3 -m unittest       # 18 tests; one of them re-runs the pipeline and compares the report
```

`run.py` reads the synthetic data in `data/`, labels it with the keyword engine, takes the model's
answers from `cache/` (one JSON file per call, keyed by a hash of the full request), and writes:

- `output/report.md`: reviewer quality against the ground truth, credit features and offers before
  and after the review, and the mislabel sensitivity tables.
- `output/flags.json`: every flagged transaction with the engine label, the proposed label,
  confidence and reason: the underwriter's queue.

## Call the model again

Only needed for transactions or prompts that are not in the cache. Either way works, and both send
the same request (model, prompt, schema, effort), so they share the cache.

With an Anthropic API key:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python3 run.py
```

Without a key, through a logged-in [Claude Code](https://claude.com/claude-code) (`claude` on PATH).
It runs headless with no tools and no user settings, and uses that account's plan:

```bash
python3 run.py
```

Calls that are already cached are not repeated; to redo them, move `cache/` away first. If the
model is unavailable, the affected businesses keep the engine labels and the report says how many
were not reviewed.

## Run it on other transactions

```bash
python3 run.py path/to/transactions.json /tmp/out
```

The file can be a Plaid `/transactions/get` response (`accounts` + `transactions`) or a bare list
of Plaid transactions. Transactions are grouped into businesses by `account_id`. Without a
`truth.json` next to the file, the quality section is skipped and the rest of the report is
written. New transactions are not in the cache, so this needs an API key or a logged-in Claude Code.

## Regenerate the synthetic data

```bash
python3 generate.py       # deterministic (seed 42): writes data/transactions.json and data/truth.json
```

## Files

| File | What it does |
|---|---|
| `generate.py` | 10 synthetic businesses, 90 days, Plaid format. Ground truth goes to a separate file the model never sees. |
| `labels.py` | The 13 groups and the revenue rule. |
| `engine.py` | The deliberately imperfect keyword engine. |
| `reviewer.py` | Prompt, model call, validation of the answer, cache, applying confident flags. |
| `credit.py` | Credit features, the offer rule, mislabel sensitivity. |
| `run.py` | Runs everything and writes the report. |
| `tests/` | `python3 -m unittest`, standard library only. |
