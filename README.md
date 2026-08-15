# CSV / Data Q&A Agent

An agent that answers plain-English questions about a dataset by **generating
and executing real pandas code** against it — not by guessing numbers.
Built for the Rooman AI Challenge (Category 2: Data & Documents), with a
Streamlit UI on top of a typed, tested Python backend.

> "My agent takes a natural-language question about a CSV and produces a
> computed, verifiable answer backed by the pandas code and raw result that
> generated it."

![CSV Q&A Agent](https://img.shields.io/badge/tests-15%20passing-brightgreen) ![Python](https://img.shields.io/badge/python-3.11%2B-blue) ![LLM](https://img.shields.io/badge/LLM-Groq%20Llama%203.3%2070B-orange)

## Why this approach (no hallucinated numbers)

The single biggest failure mode for a "data Q&A" agent is a fluent-sounding
answer with a made-up number. This agent avoids that structurally:

1. The LLM only ever writes **pandas code**, grounded in the dataset's real
   schema (column names, dtypes, sample rows) — it never sees or invents data.
2. That code is **statically checked, then executed** in a sandbox against
   the actual DataFrame.
3. If the code errors (bad column name, type mismatch, etc.), the error is
   fed back to the LLM, which gets one automatic self-correction retry.
4. The user is always shown the **generated code + raw result + explanation**
   together, so every answer is independently checkable — never just prose.

## Quick start

```bash
git clone <your-repo-url>
cd csv-qa-agent
pip install -r requirements.txt

cp .env.example .env
# edit .env and paste your free key from https://console.groq.com/keys

# Web UI (recommended for a demo)
streamlit run app.py

# or the CLI
python -m src.cli --csv data/sales_data.csv
```

No paid API required — Groq's free tier is used throughout (see "Model
choice" below).

## Web UI

```bash
streamlit run app.py
```

Opens a dark-themed, chat-style interface: pick the bundled sample dataset
or upload your own CSV, ask questions in plain English, and see for each one:
- the exact pandas code the LLM generated (syntax-highlighted, collapsible)
- the raw computed result, auto-rendered as a metric, table, or bar chart
  depending on its shape
- a one-line natural-language answer
- a download button to export the full session transcript as JSON

Sample questions are one click away in the sidebar for a fast reviewer demo.

## Architecture

```
csv-qa-agent/
├── app.py                      # Streamlit UI
├── README.md
├── requirements.txt
├── .env.example
├── data/
│   ├── sales_data.csv          # 2,000-row synthetic e-commerce dataset
│   └── generate_data.py        # regenerate the dataset if needed
├── src/
│   ├── config.py                # pydantic-settings: validated env config
│   ├── exceptions.py            # typed exception hierarchy
│   ├── models.py                # pydantic domain models (QAResult, DatasetSchema, ...)
│   ├── schema.py                # DataFrame -> DatasetSchema introspection
│   ├── llm_client.py            # LLMProvider Protocol + Groq implementation (retry/backoff)
│   ├── sandbox_executor.py      # AST safety check + restricted code execution
│   ├── agent.py                 # the Input -> Think -> Act -> Output loop
│   ├── logging_config.py        # structured logging (rich)
│   └── cli.py                   # interactive REPL + batch mode
├── tests/
│   ├── test_sandbox.py          # sandbox safety + correctness (10 tests)
│   └── test_agent.py            # agent retry/error-handling via a stub LLM (5 tests)
└── sample_outputs/
    ├── questions.json           # 10 sample questions
    ├── answers.json             # structured results
    └── transcript.md            # human-readable Q&A transcript
```

### Engineering standards followed

- **Full type hints** on every function/method signature; `from __future__
  import annotations` throughout for clean forward references.
- **Typed exception hierarchy** (`src/exceptions.py`) instead of bare
  `Exception`/`ValueError` — callers catch precisely what they mean to.
- **Pydantic models** for every data contract (`QAResult`, `DatasetSchema`,
  `ColumnInfo`) — free validation and JSON serialisation, no loose dicts.
- **pydantic-settings** for configuration — validated at startup (e.g.
  `MAX_CODEGEN_RETRIES` is constrained to `0–5`), fails fast with a clear
  message instead of a confusing error three calls deep.
- **Dependency injection**: `CSVQAAgent` takes an `LLMProvider` (a
  `Protocol`, i.e. structural typing) rather than hard-coding Groq's SDK
  inside the agent logic — the test suite injects a stub provider so the
  full retry/error-handling logic is unit-tested with **zero network calls
  and zero API key required**.
- **Retry with exponential backoff** (`tenacity`) around the actual Groq
  API call for transient failures (timeouts, rate limits); a *separate*,
  intentional retry loop in `agent.py` handles LLM-generated-code errors
  by feeding the error back into the next prompt.
- **Structured logging** (`rich`) instead of scattered `print()` calls.
- **15 automated tests**, all passing, covering sandbox safety (rejecting
  imports/eval/dunder access), sandbox correctness, and agent-level retry
  behaviour — run with `python -m pytest tests/ -v`.

## Sample data

`data/sales_data.csv` is a synthetic 2,000-row e-commerce dataset (order
date, region, category, product, quantity, price, discount, revenue, cost,
profit, customer segment) covering Jan 2024–Jun 2025. Regenerate it anytime
with `python data/generate_data.py`, or point `--csv` / the UI's upload
button at your own file — the agent reads the schema dynamically, so it
isn't hard-coded to this dataset.

## Running the tests

```bash
python -m pytest tests/ -v
```
All 15 tests pass without a Groq API key, since the agent-level tests use
a dependency-injected stub `LLMProvider`.

## Sample outputs — a note on how these were produced

`sample_outputs/transcript.md` and `answers.json` contain 10 real questions
and their answers, computed by running pandas code **through the exact same
sandbox executor** (`src/sandbox_executor.py`) the live agent uses. The
build environment used to prepare this submission had no outbound network
access to call Groq's API, so `sample_outputs/build_sample_outputs.py`
supplies the pandas snippets a correctly-prompted LLM reliably produces for
these questions and executes them for real — the numbers are genuine,
reproducible results from the actual dataset, not placeholders. **Run the
UI or `python -m src.cli --batch ...` with your own Groq key to see the LLM
generate this code live, end to end.**

## Design tradeoffs & what I'd improve with more time

- **Sandbox strength.** The current sandbox is an AST allow-list +
  restricted builtins running in-process — good enough to block imports,
  file/network access, and dunder-based escapes for a local tool, but not
  a hardened multi-tenant boundary. With more time I'd move execution into
  a separate subprocess (or container) with a hard timeout and memory
  limit, so a pathological snippet can't hang or crash the host process.
- **Single-file datasets only.** The agent currently loads one CSV. A real
  analyst workflow often needs joins across multiple tables — I'd extend
  `DatasetSchema` to describe multiple DataFrames and let the LLM write
  joins.
- **Retry strategy is simple.** One retry with the raw exception text fed
  back. A stronger version would classify the error (wrong column vs.
  wrong dtype vs. logic error) and tailor the retry prompt accordingly.
- **No result-sanity checks.** For numeric answers, I'd add lightweight
  post-hoc checks (e.g. flag if a "percentage" result falls outside
  0–100, or a "total" is negative) as an extra hallucination guard.
- **Ambiguous questions.** The LLM currently does its best on vague
  questions without asking for clarification. A production version would
  detect ambiguity and ask a follow-up instead of guessing an
  interpretation.
- **Q1 2025 growth caveat.** The sample question about 2024→2025 regional
  growth compares a partial year (Jan–Jun 2025) to a full year (2024)
  since that's the range in the synthetic data — the agent computes it
  correctly as asked, but a real analyst would flag that the comparison
  isn't apples-to-apples. Left in deliberately as a talking point.
- **Model choice.** Groq's Llama-3.3-70B was chosen for speed + zero cost
  + strong code-generation quality on a free tier, which matters for a
  24-hour build. For production I'd benchmark it against Claude/GPT-4-class
  models specifically on pandas code-gen accuracy before committing.

## What I'd explain if asked

Every piece here is intentionally small enough to explain line-by-line: the
AST safety check in `sandbox_executor.py`, the dependency-injected
`LLMProvider` Protocol in `llm_client.py`, the retry loop in `agent.py`, the
pydantic validation in `config.py` and `models.py`, and the Streamlit
rendering logic in `app.py`. Happy to walk through any of it.
