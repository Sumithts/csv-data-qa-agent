# CSV / Data Q&A Agent — Project Explainer

Use this document to walk a reviewer through the project, or to prep
yourself before an interview/review call. It's organised the way a
reviewer will actually probe: what it does, how it works, why you built
it this way, and what you'd change.

---

## 1. One-sentence description

**"It takes a plain-English question about a CSV, has an LLM write real
pandas code to answer it, executes that code in a sandbox, and shows the
computed result — so the answer is never a guessed number."**

---

## 2. The problem this solves

Most "chat with your data" demos quietly let the LLM either:
- guess a number that sounds plausible but isn't computed from the data, or
- hallucinate a column or value that doesn't exist.

This agent structurally prevents both failure modes by never asking the
model for an answer directly — only for **code**, which is then run for
real against the actual data.

---

## 3. Architecture (what to draw on a whiteboard if asked)

```
 User question
      │
      ▼
┌─────────────────┐        ┌──────────────────────┐
│  Streamlit UI /  │──────▶│   CSVQAAgent.ask()    │
│  CLI             │        │  (src/agent.py)       │
└─────────────────┘        └──────────┬────────────┘
                                       │
                     ┌─────────────────┼──────────────────┐
                     ▼                                     ▼
          ┌────────────────────┐              ┌─────────────────────────┐
          │  GroqProvider       │             │  DatasetSchema           │
          │  (src/llm_client.py)│◀────────────│  (src/schema.py)         │
          │  → generates pandas │  schema as   │  column names, dtypes,   │
          │    code + a 1-line  │  grounding   │  sample rows             │
          │    explanation      │  context     └─────────────────────────┘
          └──────────┬──────────┘
                     │ generated code
                     ▼
          ┌─────────────────────────┐
          │  sandbox_executor.py     │
          │  1. AST safety check     │
          │  2. restricted builtins  │
          │  3. exec() on a COPY     │
          │     of the DataFrame     │
          └──────────┬───────────────┘
                     │
        success ─────┤───── runtime error
                     │              │
                     ▼              ▼
              QAResult      feed error back to
              (answer)      GroqProvider, retry
                             (max 2 retries)
```

**The one thing to emphasize if asked "what's the core idea":** the LLM
never touches the data directly. It only ever sees a *description* of the
schema and writes code; a separate, restricted execution layer is what
actually touches the DataFrame. That separation is the whole safety and
correctness story.

---

## 4. Walking through one request, step by step

Question: *"Which region generated the highest total revenue?"*

1. **Schema grounding** (`schema.py`) — the agent has already introspected
   the CSV once at startup: column names (`region`, `revenue`, ...),
   dtypes, and 3 sample rows. This gets attached to every prompt so the
   model can't invent a column that doesn't exist.
2. **Code generation** (`llm_client.py`) — the question + schema go to
   Groq's Llama-3.3-70B with a system prompt that says, in effect: *"write
   pandas code, assign the answer to `result`, don't guess."* The model
   returns:
   ```python
   result = df.groupby('region')['revenue'].sum().idxmax()
   ```
3. **Safety check** (`sandbox_executor.py::validate_code`) — the code is
   parsed into an AST and walked node by node. No imports, no dunder
   attribute access (`__class__`, `__globals__`, etc.), no dangerous names
   (`eval`, `exec`, `open`, `os`, ...). This happens *before* anything runs.
4. **Execution** — the code runs with only `df` (a **copy**, so it can't
   mutate your real data), `pd`, and `np` in scope, and a restricted set of
   builtins. Result: `"North"`.
5. **Output** — the agent returns a `QAResult` with the question, the
   exact code, the raw result, a one-line explanation, and whether it
   succeeded — all of which the UI displays together so nothing is hidden.

If step 3 or 4 fails (bad column name, wrong type, etc.), the exception
text is fed back into a second prompt asking the model to fix its own
code — up to `MAX_CODEGEN_RETRIES` (default 2) times before giving up and
reporting the failure honestly.

---

## 5. Design decisions — the "why", not just the "what"

| Decision | Why |
|---|---|
| Generate **code**, not answers | Structurally prevents hallucinated numbers — the only way to get an answer is to actually compute it. |
| **AST allow-list** before execution | Static analysis catches unsafe code before it ever runs, rather than trying to sandbox a running process. |
| Execute on a **copy** of the DataFrame | Prevents a bad snippet (accidental or adversarial) from corrupting the loaded dataset across questions. |
| **Retry with the error fed back**, not a blind retry | Gives the model the actual traceback so its second attempt is informed, not just a re-roll. |
| **Dependency-injected LLM provider** (`Protocol`, not a hard import) | Lets the entire agent be unit-tested with a scripted stub — 15 tests run with zero API calls and zero network dependency. |
| **Pydantic models everywhere** | Free validation + JSON serialization; a malformed LLM response or bad config fails loudly at the boundary instead of silently propagating. |
| **Groq / Llama-3.3-70B** | Free tier, fast enough for a responsive UI, good enough at pandas code generation — the right tradeoff for a 24-hour build with zero budget. |

---

## 6. How to verify the project actually works

Do these in order — each one builds confidence for the next:

1. **Run the automated tests (no API key needed):**
   ```bash
   python -m pytest tests/ -v
   ```
   Expect `15 passed`. These cover sandbox safety (rejects imports/eval/
   dunder access), sandbox correctness (aggregation, groupby, doesn't
   mutate source data), and the agent's retry logic using a scripted stub
   LLM — so this step alone proves the *logic* is correct independent of
   any live model call.

2. **Boot the UI:**
   ```bash
   streamlit run app.py
   ```
   Confirm it opens at `http://localhost:8501` with no traceback in the
   terminal.

3. **Run a sample question and check the math yourself:**
   Click "What is the total revenue across all orders?" in the sidebar.
   Compare the displayed result against `sample_outputs/transcript.md`
   (which has the pre-verified answer: `987999.41`). If your live run
   matches, the LLM → sandbox → result pipeline is working end to end.

4. **Deliberately try to break it** (good for interview credibility):
   Ask a nonsense question like *"what is the meaning of life in this
   data?"* — a good run shows the agent either answering sensibly from
   the data or failing cleanly with a shown error, never crashing the app.

5. **Check the batch reproducibility:**
   ```bash
   python -m src.cli --csv data/sales_data.csv --batch sample_outputs/questions.json --out /tmp/answers_check.json
   diff sample_outputs/answers.json /tmp/answers_check.json
   ```
   Minor differences are expected (LLM phrasing/explanation varies run to
   run), but the **numeric `result` values should match** — that's the
   real correctness signal, since they come from executed code, not the
   model's prose.

---

## 7. Anticipated questions (and how to answer them)

**"What stops the LLM from writing malicious code?"**
→ Two layers: a static AST check that rejects imports, `eval`/`exec`/
`open`, and dunder attribute access before anything runs; then execution
happens against a restricted builtins list and a *copy* of the data, so
even code that passes the check can't reach the filesystem, network, or
your original DataFrame.

**"What if the LLM writes code that's syntactically fine but wrong?"**
→ That's the one gap this design doesn't fully close — a query that
*runs* but computes something subtly different from what was asked. I've
noted this in the README's tradeoffs section: a production version would
add result-sanity checks (e.g., percentages should be 0–100) as an extra
guard.

**"Why Groq instead of OpenAI or Anthropic?"**
→ Free tier with no card required, fast inference, and good enough
code-generation quality for pandas — the right cost/speed tradeoff for a
zero-budget 24-hour build. The `LLMProvider` abstraction means swapping
providers later is a one-class change, not a rewrite.

**"How did you test this without burning API calls?"**
→ `CSVQAAgent` takes its LLM provider as a constructor argument (dependency
injection via a `Protocol`). The test suite passes in a stub that returns
scripted code strings, so the retry logic, safety checks, and result
handling are all verified without ever calling Groq.

**"What would you do differently with more time?"**
→ Point to the README's "Design tradeoffs" section directly: subprocess-
isolated execution with resource limits, multi-file joins, smarter retry
classification, and result-sanity checks.

---

## 8. Quick demo script (for a live walkthrough)

1. Show the file tree — point out the layered structure (`config`,
   `exceptions`, `models`, `schema`, `llm_client`, `sandbox_executor`,
   `agent`, `cli`, `app.py`) and mention this separation is what made unit
   testing possible without live API calls.
2. Run `python -m pytest tests/ -v` live — 15 green tests in ~1–2 seconds.
3. Open the Streamlit UI, ask 2–3 questions live (including one that
   forces a retry, e.g. deliberately vague phrasing).
4. Expand "View generated pandas code" on one answer — show that the
   number displayed literally came from that code, not from the model's
   text.
5. Close by naming one concrete tradeoff you'd fix next (subprocess
   sandboxing is the strongest one to lead with).

---

## 9. Colour system (for consistency across README/README screenshots/slides)

Matched to the SupplyIQ reference dashboard you shared, in case you reuse
this for a slide or a written summary:

| Role | Hex | Used for |
|---|---|---|
| Navy (primary) | `#12294D` | Header background, headings |
| Navy (dark) | `#0E2038` | Header gradient end |
| Royal blue (accent) | `#1E6FD9` | Buttons, active states, chart bars |
| Background | `#F7F9FC` | App background |
| Card background | `#FFFFFF` | Cards, sidebar |
| Border | `#E2E8F0` | Card/sidebar borders |
| Text (primary) | `#1F2933` | Body text |
| Green (success) | `#16A34A` | Positive deltas, success badges |
| Red (failure/risk) | `#DC2626` | Failure badges, error states |
| Amber (warning) | `#D9971C` | Warning indicators |
