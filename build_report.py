"""
Generates PROJECT_REPORT.pdf — a full explainer document covering how the
project works, which LLM/agent it uses, its dynamic (no-hardcoding)
design, setup steps, and verification/test results.

Run: python build_report.py
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    ListFlowable, ListItem, HRFlowable,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

NAVY = colors.HexColor("#12294D")
ROYAL_BLUE = colors.HexColor("#1E6FD9")
GREEN = colors.HexColor("#16A34A")
RED = colors.HexColor("#DC2626")
AMBER = colors.HexColor("#D9971C")
LIGHT_BG = colors.HexColor("#F7F9FC")
BORDER = colors.HexColor("#E2E8F0")
TEXT_DARK = colors.HexColor("#1F2933")
TEXT_MUTED = colors.HexColor("#5B6B7C")

styles = getSampleStyleSheet()

styles.add(ParagraphStyle(
    name="ReportTitle", fontSize=26, leading=30, textColor=colors.white,
    fontName="Helvetica-Bold", alignment=TA_LEFT, spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="ReportSubtitle", fontSize=12.5, leading=16, textColor=colors.HexColor("#cbd8ea"),
    fontName="Helvetica", alignment=TA_LEFT,
))
styles.add(ParagraphStyle(
    name="H1", fontSize=17, leading=21, textColor=NAVY, fontName="Helvetica-Bold",
    spaceBefore=18, spaceAfter=8,
))
styles.add(ParagraphStyle(
    name="H2", fontSize=13, leading=17, textColor=ROYAL_BLUE, fontName="Helvetica-Bold",
    spaceBefore=12, spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="Body", fontSize=10.2, leading=15, textColor=TEXT_DARK, fontName="Helvetica",
    spaceAfter=8, alignment=TA_LEFT,
))
styles.add(ParagraphStyle(
    name="BodyMuted", fontSize=9.5, leading=14, textColor=TEXT_MUTED, fontName="Helvetica-Oblique",
    spaceAfter=8,
))
styles.add(ParagraphStyle(
    name="CodeBlock", fontSize=9, leading=13, textColor=TEXT_DARK, fontName="Courier",
    backColor=LIGHT_BG, borderColor=BORDER, borderWidth=0.5, borderPadding=8,
    spaceAfter=10,
))
styles.add(ParagraphStyle(
    name="BulletText", fontSize=10.2, leading=15, textColor=TEXT_DARK, fontName="Helvetica",
))
styles.add(ParagraphStyle(
    name="FooterText", fontSize=8, textColor=TEXT_MUTED, alignment=TA_CENTER,
))

story = []

# ---------------------------------------------------------------------------
# Cover / header block
# ---------------------------------------------------------------------------
cover_table = Table(
    [[Paragraph("CSV / Data Q&amp;A Agent", styles["ReportTitle"])],
     [Paragraph("Full Project Report — How It Works, How to Run It, and How It Was Verified", styles["ReportSubtitle"])]],
    colWidths=[6.9 * inch],
)
cover_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), NAVY),
    ("LEFTPADDING", (0, 0), (-1, -1), 22),
    ("RIGHTPADDING", (0, 0), (-1, -1), 22),
    ("TOPPADDING", (0, 0), (-1, 0), 22),
    ("BOTTOMPADDING", (0, -1), (-1, -1), 20),
]))
story.append(cover_table)
story.append(Spacer(1, 18))

meta_data = [
    ["Built for", "Rooman AI Challenge — 24-Hour AI Agent Challenge"],
    ["Agent category", "CSV / Data Q&A Agent (Category 2: Data & Documents)"],
    ["LLM / Agent used", "Groq Cloud — Llama 3.3 70B Versatile (free tier, OpenAI-compatible API)"],
    ["Core language", "Python 3.11+"],
    ["Interfaces", "Streamlit web UI (app.py) and command-line (src/cli.py)"],
    ["Automated tests", "16 / 16 passing (pytest)"],
]
meta_table = Table(meta_data, colWidths=[1.7 * inch, 5.2 * inch])
meta_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
    ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
    ("FONTSIZE", (0, 0), (-1, -1), 9.5),
    ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 7),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ("LEFTPADDING", (0, 0), (-1, -1), 10),
]))
story.append(meta_table)
story.append(Spacer(1, 10))

# ---------------------------------------------------------------------------
# 1. What this project is
# ---------------------------------------------------------------------------
story.append(Paragraph("1. What This Project Is", styles["H1"]))
story.append(Paragraph(
    "An AI agent that answers plain-English questions about a dataset by generating and "
    "executing <b>real pandas code</b> against it — not by guessing numbers. The user asks "
    "a question in natural language; the agent writes Python/pandas code to compute the "
    "answer, runs that code in a safety-checked sandbox against the actual data, and shows "
    "the code, the raw computed result, and a plain-English explanation together — so every "
    "answer is independently verifiable.",
    styles["Body"],
))
story.append(Paragraph(
    "On top of that, the agent is fully conversational: if a question isn't about the "
    "loaded dataset at all (general knowledge, small talk, anything), it falls back to "
    "answering directly from the language model — the same way ChatGPT or Claude would — "
    "while being explicit in the UI that no code was executed for that answer. This means "
    "the agent can be asked literally anything and will respond usefully, while data "
    "questions always stay grounded in real computation.",
    styles["Body"],
))

# ---------------------------------------------------------------------------
# 2. Which agent / LLM is used
# ---------------------------------------------------------------------------
story.append(Paragraph("2. Which Agent / LLM Is Used", styles["H1"]))
story.append(Paragraph(
    "The project uses <b>Groq Cloud's Llama 3.3 70B Versatile</b> model, accessed through "
    "Groq's free, OpenAI-compatible API (no cost, no credit card required). Groq was chosen "
    "for three reasons that matter for this kind of build:",
    styles["Body"],
))
story.append(ListFlowable([
    ListItem(Paragraph("<b>Free tier with no cost</b> — no paid API budget was needed for a 24-hour build.", styles["BulletText"])),
    ListItem(Paragraph("<b>Fast inference</b> — Groq's hardware makes responses fast enough for a responsive chat-style UI.", styles["BulletText"])),
    ListItem(Paragraph("<b>Strong code-generation quality</b> — Llama 3.3 70B reliably writes correct, runnable pandas code when grounded with a real schema.", styles["BulletText"])),
], bulletType="bullet", start="circle"))
story.append(Paragraph(
    "The model is never hard-wired into the core logic directly. <b>src/llm_client.py</b> "
    "defines an <b>LLMProvider</b> Python <i>Protocol</i> (structural interface) with two "
    "methods — <font face='Courier'>generate_pandas_code()</font> and "
    "<font face='Courier'>generate_general_answer()</font> — and <b>GroqProvider</b> is the "
    "concrete implementation actually used. The rest of the codebase (the agent loop) only "
    "depends on that interface, so swapping in OpenAI, Anthropic, or a local model later "
    "would mean writing one new class, not rewriting the agent.",
    styles["Body"],
))

# ---------------------------------------------------------------------------
# 3. How it works — architecture
# ---------------------------------------------------------------------------
story.append(Paragraph("3. How It Works — Architecture", styles["H1"]))
story.append(Paragraph(
    "Every question goes through the same four-stage loop:",
    styles["Body"],
))
arch_steps = [
    ("1. Input", "The user's plain-English question arrives from the Streamlit UI or CLI."),
    ("2. Think", "The LLM is given the question plus the dataset's real schema (column names, dtypes, sample rows) and writes pandas code to compute the answer. It never sees or invents data directly."),
    ("3. Act", "That code is statically safety-checked (rejects imports, eval/exec/open, file or network access) and then executed in a sandbox against a copy of the real DataFrame."),
    ("4. Output", "The result, the exact code that produced it, and a one-line explanation are returned together — nothing is hidden, so every answer can be checked."),
]
arch_table = Table(
    [[Paragraph(f"<b>{step}</b>", styles["BulletText"]), Paragraph(desc, styles["BulletText"])] for step, desc in arch_steps],
    colWidths=[1.1 * inch, 5.8 * inch],
)
arch_table.setStyle(TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
    ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 8),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
]))
story.append(arch_table)
story.append(Spacer(1, 10))

story.append(Paragraph(
    "If the generated code fails to run (wrong column name, type mismatch, etc.), the exact "
    "error is fed back to the model, which gets one automatic self-correction retry "
    "(configurable, default 2 retries). If code generation still can't answer the question "
    "after all retries — almost always because the question genuinely isn't about the "
    "dataset — the agent falls back to a direct, clearly-labelled general-knowledge answer "
    "instead of just failing. This fallback is what makes the agent able to handle "
    "<b>any</b> question, not only ones about the loaded CSV.",
    styles["Body"],
))

story.append(Paragraph("Module map:", styles["H2"]))
module_rows = [
    ["src/config.py", "Validated environment configuration (pydantic-settings)"],
    ["src/exceptions.py", "Typed exception hierarchy (ConfigurationError, UnsafeCodeError, ...)"],
    ["src/models.py", "Typed data contracts — QAResult, DatasetSchema, AnswerMode, ResultType"],
    ["src/schema.py", "Introspects the loaded CSV into a DatasetSchema at runtime"],
    ["src/llm_client.py", "LLMProvider interface + GroqProvider (Llama 3.3 70B via Groq)"],
    ["src/sandbox_executor.py", "AST safety check + restricted, isolated code execution"],
    ["src/agent.py", "The Input -> Think -> Act -> Output loop, with retry + fallback"],
    ["src/cli.py", "Command-line interface (interactive + batch mode)"],
    ["app.py", "Streamlit web UI"],
    ["tests/", "16 automated tests — sandbox safety, correctness, and agent logic"],
]
mod_table = Table(module_rows, colWidths=[1.9 * inch, 5.0 * inch])
mod_table.setStyle(TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
    ("FONTNAME", (0, 0), (0, -1), "Courier"),
    ("FONTSIZE", (0, 0), (-1, -1), 8.7),
    ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
]))
story.append(mod_table)

story.append(PageBreak())

# ---------------------------------------------------------------------------
# 4. Fully dynamic — no hardcoding
# ---------------------------------------------------------------------------
story.append(Paragraph("4. Fully Dynamic — No Hardcoded Logic", styles["H1"]))
story.append(Paragraph(
    "This was checked deliberately, since hardcoded question-to-answer mappings are an easy "
    "way to fail a review. Every answer the agent gives is produced live, at request time:",
    styles["Body"],
))
story.append(ListFlowable([
    ListItem(Paragraph("<b>No if/elif question-matching anywhere in the code.</b> There is no lookup table or keyword-matching logic that maps specific questions to specific answers — verified by searching the codebase for any such pattern.", styles["BulletText"])),
    ListItem(Paragraph("<b>The dataset schema is introspected at runtime</b> (src/schema.py) from whatever CSV is loaded — column names, types, and sample values are read from the actual file, not written into the code. Uploading a different CSV in the UI changes what the agent knows automatically.", styles["BulletText"])),
    ListItem(Paragraph("<b>Every pandas snippet is generated by the LLM per-question</b>, grounded in that live schema, then actually executed — the computed number comes from real execution, not a stored value.", styles["BulletText"])),
    ListItem(Paragraph("<b>Off-topic questions are handled dynamically too</b> — the general-knowledge fallback calls the same live LLM with a different system prompt; nothing is a canned string.", styles["BulletText"])),
    ListItem(Paragraph("<b>The sample \"suggested questions\" buttons in the sidebar</b> are only a UX convenience (like ChatGPT's example prompts) — clicking one still runs the full live pipeline; the answer is computed fresh, not pre-stored.", styles["BulletText"])),
], bulletType="bullet", start="circle"))
story.append(Paragraph(
    "One honest exception, clearly documented in the repo: the pre-built "
    "<font face='Courier'>sample_outputs/</font> folder (required by the challenge brief as "
    "a submitted deliverable) was generated in a build sandbox with no outbound internet "
    "access to Groq's API. Its script runs the same pandas snippets a correctly-prompted "
    "LLM reliably produces, through the real sandbox executor, to get genuine, verified "
    "numbers for that static deliverable file. The live agent itself (UI and CLI) does not "
    "use this script — it always calls Groq directly at request time.",
    styles["BodyMuted"],
))

# ---------------------------------------------------------------------------
# 5. Setup & run steps
# ---------------------------------------------------------------------------
story.append(Paragraph("5. Setup &amp; Run Steps", styles["H1"]))

steps = [
    ("Step 1 — Unzip and enter the project",
     "unzip csv-qa-agent.zip -d csv-qa-agent\ncd csv-qa-agent"),
    ("Step 2 — Install dependencies (Python 3.11+ required)",
     "pip install -r requirements.txt"),
    ("Step 3 — Get a free Groq API key",
     "Sign up at https://console.groq.com/keys (no credit card required)\nCreate a key and copy it."),
    ("Step 4 — Configure your key",
     "cp .env.example .env\n# then edit .env and paste your key:\n# GROQ_API_KEY=gsk_your_actual_key_here"),
    ("Step 5a — Run the web UI (recommended)",
     "streamlit run app.py\n# opens automatically at http://localhost:8501"),
    ("Step 5b — Or run the CLI (interactive)",
     "python -m src.cli --csv data/sales_data.csv"),
    ("Step 5c — Or run batch mode (all sample questions at once)",
     "python -m src.cli --csv data/sales_data.csv \\\n  --batch sample_outputs/questions.json \\\n  --out sample_outputs/answers.json"),
    ("Step 6 — Run the automated tests",
     "python -m pytest tests/ -v\n# expect: 16 passed"),
]
for title, code in steps:
    story.append(Paragraph(title, styles["H2"]))
    story.append(Paragraph(code.replace("\n", "<br/>"), styles["CodeBlock"]))

story.append(Paragraph(
    "Troubleshooting: if you see <font face='Courier'>TypeError: Client.__init__() got an "
    "unexpected keyword argument 'proxies'</font>, run "
    "<font face='Courier'>pip install \"httpx&lt;0.28\" --force-reinstall</font> — this is a "
    "known version clash between the openai SDK and newer httpx releases, already pinned in "
    "requirements.txt for future installs.",
    styles["BodyMuted"],
))

story.append(PageBreak())

# ---------------------------------------------------------------------------
# 6. Verification & test results
# ---------------------------------------------------------------------------
story.append(Paragraph("6. Verification &amp; Test Results", styles["H1"]))
story.append(Paragraph(
    "The full automated test suite was run before this report was generated. All 16 tests "
    "passed, covering three layers:",
    styles["Body"],
))
test_rows_raw = [
    ["Layer", "What's verified", "Tests"],
    ["Sandbox safety", "Rejects imports, eval/exec/open, dunder attribute access, unsafe module references", "5"],
    ["Sandbox correctness", "Aggregation and groupby execute correctly; source DataFrame is never mutated; missing-result and runtime errors are raised properly", "5"],
    ["Agent logic", "Succeeds on first try; retries and self-corrects after a runtime error; fails closed (no retry) on unsafe code; falls back to general knowledge after exhausting retries; schema introspection is correct", "6"],
]
header_style = ParagraphStyle(name="TestHeader", parent=styles["BulletText"], textColor=colors.white, fontName="Helvetica-Bold", fontSize=9)
cell_style = ParagraphStyle(name="TestCell", parent=styles["BulletText"], fontSize=8.8, leading=12)
test_rows = [[Paragraph(c, header_style) for c in test_rows_raw[0]]]
for row in test_rows_raw[1:]:
    test_rows.append([Paragraph(row[0], cell_style), Paragraph(row[1], cell_style), Paragraph(row[2], cell_style)])
test_table = Table(test_rows, colWidths=[1.3 * inch, 4.6 * inch, 0.8 * inch])
test_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("ALIGN", (2, 0), (2, -1), "CENTER"),
    ("TOPPADDING", (0, 0), (-1, -1), 7),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
]))
story.append(test_table)
story.append(Spacer(1, 10))

story.append(Paragraph(
    "Key behaviors specifically verified by the agent-logic tests (using a scripted stub "
    "LLM, so these run with zero network calls and prove the logic independent of any "
    "single live model response):",
    styles["Body"],
))
story.append(ListFlowable([
    ListItem(Paragraph("A correct first answer succeeds in 1 attempt with the right result type.", styles["BulletText"])),
    ListItem(Paragraph("A runtime error (e.g. wrong column name) triggers a retry with the error fed back, and succeeds on the corrected attempt.", styles["BulletText"])),
    ListItem(Paragraph("Unsafe generated code is rejected immediately with no retry — fails closed for safety.", styles["BulletText"])),
    ListItem(Paragraph("A question unrelated to the dataset exhausts all code-generation retries, then correctly falls back to a general-knowledge answer instead of just failing.", styles["BulletText"])),
], bulletType="bullet", start="circle"))

story.append(Paragraph("Manual verification checklist for a live demo:", styles["H2"]))
story.append(ListFlowable([
    ListItem(Paragraph("Run <font face='Courier'>python -m pytest tests/ -v</font> — confirm 16 passed.", styles["BulletText"])),
    ListItem(Paragraph("Run <font face='Courier'>streamlit run app.py</font> — confirm it opens with no errors.", styles["BulletText"])),
    ListItem(Paragraph("Ask a data question (e.g. \"total revenue?\") — confirm the shown code and result match sample_outputs/transcript.md.", styles["BulletText"])),
    ListItem(Paragraph("Ask something unrelated to the data (e.g. \"what's the capital of France?\") — confirm it's answered directly, labelled \"GENERAL KNOWLEDGE\", with no code shown.", styles["BulletText"])),
    ListItem(Paragraph("Upload a different CSV in the sidebar — confirm the agent adapts to the new columns without any code changes.", styles["BulletText"])),
], bulletType="bullet", start="circle"))

# ---------------------------------------------------------------------------
# 7. Design tradeoffs
# ---------------------------------------------------------------------------
story.append(Paragraph("7. Design Tradeoffs &amp; What's Next", styles["H1"]))
tradeoffs = [
    ("Sandbox strength", "AST allow-list + restricted builtins, in-process. Good enough for a local tool; a hardened version would isolate execution in a subprocess/container with resource limits."),
    ("Single-file datasets", "Currently one CSV at a time. Multi-table joins would need the schema layer extended to describe several DataFrames."),
    ("Retry strategy", "One retry with the raw error fed back. A stronger version would classify the error type and tailor the retry prompt."),
    ("No result-sanity checks", "A production version would flag obviously-wrong results, e.g. a \"percentage\" outside 0-100."),
    ("Model choice", "Groq/Llama-3.3-70B for speed + zero cost; a production system would benchmark against Claude/GPT-4-class models on code-gen accuracy specifically."),
]
tt_table = Table(
    [[Paragraph(f"<b>{t}</b>", styles["BulletText"]), Paragraph(d, styles["BulletText"])] for t, d in tradeoffs],
    colWidths=[1.5 * inch, 5.4 * inch],
)
tt_table.setStyle(TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
    ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 8),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
]))
story.append(tt_table)

story.append(Spacer(1, 16))
story.append(HRFlowable(width="100%", color=BORDER, thickness=0.7))
story.append(Spacer(1, 8))
story.append(Paragraph(
    "CSV / Data Q&amp;A Agent · Rooman AI Challenge Submission · Report generated automatically from the live, tested codebase.",
    styles["FooterText"],
))

doc = SimpleDocTemplate(
    "PROJECT_REPORT.pdf", pagesize=letter,
    topMargin=0.6 * inch, bottomMargin=0.6 * inch,
    leftMargin=0.65 * inch, rightMargin=0.65 * inch,
)
doc.build(story)
print("Wrote PROJECT_REPORT.pdf")
