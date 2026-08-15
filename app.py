"""Streamlit UI for the CSV / Data Q&A Agent.

Run with:
    streamlit run app.py

A polished, single-page interface: upload/choose a CSV, ask questions in
plain English, and see the generated pandas code + computed result +
answer for each one, with automatic chart rendering where it makes sense.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.agent import CSVQAAgent
from src.exceptions import AgentError, ConfigurationError, DataLoadError
from src.models import AnswerMode, QAResult, ResultType
from src import history_store

st.set_page_config(
    page_title="QueryIQ — Data Q&A Agent",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Styling — matched to the SupplyIQ dashboard palette:
#   navy header (#12294D), royal-blue accents (#1E6FD9), light background
#   (#F7F9FC), green for positive/success (#16A34A), red for risk/failure
#   (#DC2626), amber for warnings (#D9971C).
# --------------------------------------------------------------------------
NAVY = "#12294D"
NAVY_DARK = "#0E2038"
ROYAL_BLUE = "#1E6FD9"
BG = "#F7F9FC"
CARD_BG = "#FFFFFF"
BORDER = "#E2E8F0"
TEXT_DARK = "#1F2933"
TEXT_MUTED = "#5B6B7C"
GREEN = "#16A34A"
RED = "#DC2626"
AMBER = "#D9971C"

st.markdown(
    f"""
    <style>
    .stApp {{ background: {BG}; }}
    section[data-testid="stSidebar"] {{ background: {CARD_BG}; border-right: 1px solid {BORDER}; }}
    h1, h2, h3 {{ color: {NAVY} !important; }}
    p, li, span, label {{ color: {TEXT_DARK}; }}
    .app-header {{
        background: linear-gradient(90deg, {NAVY} 0%, {NAVY_DARK} 100%);
        border-radius: 14px;
        padding: 1.1rem 1.5rem;
        margin-bottom: 1.2rem;
        color: white;
    }}
    .app-header h1 {{ color: white !important; margin: 0; font-size: 1.5rem; }}
    .app-header p {{ color: #cbd8ea; margin: 0.2rem 0 0 0; }}
    .qa-card {{
        background: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(18, 41, 77, 0.06);
    }}
    .qa-question {{
        font-size: 1.05rem;
        font-weight: 700;
        color: {NAVY};
        margin-bottom: 0.4rem;
    }}
    .qa-answer {{
        font-size: 1.05rem;
        font-weight: 600;
        color: {GREEN};
        margin-top: 0.6rem;
    }}
    .badge {{
        display: inline-block;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.03em;
    }}
    .badge-ok {{ background: #DCFCE7; color: {GREEN}; }}
    .badge-fail {{ background: #FEE2E2; color: {RED}; }}
    .metric-card {{
        background: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 0.9rem 1rem;
        text-align: center;
        color: {NAVY};
    }}
    /* Sample-question buttons styled like SupplyIQ's filter pills */
    .stButton > button {{
        background: {ROYAL_BLUE} !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }}
    .stButton > button:hover {{ background: {NAVY} !important; }}
    .stButton > button {{ transition: background 0.2s ease, transform 0.1s ease; }}
    .stButton > button:active {{ transform: scale(0.97); }}
    [data-testid="stChatInput"] {{ border-color: {ROYAL_BLUE} !important; }}

    /* Animations — subtle fade/slide-in for each new chat card, soft hover lift */
    @keyframes fadeInUp {{
        from {{ opacity: 0; transform: translateY(14px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    .qa-card {{ animation: fadeInUp 0.35s ease-out; transition: box-shadow 0.2s ease, transform 0.2s ease; }}
    .qa-card:hover {{ box-shadow: 0 6px 16px rgba(18, 41, 77, 0.10); transform: translateY(-1px); }}
    .badge {{ transition: transform 0.15s ease; }}
    .badge:hover {{ transform: scale(1.05); }}
    @keyframes shimmer {{
        0% {{ background-position: -200px 0; }}
        100% {{ background-position: 200px 0; }}
    }}
    .app-header {{ animation: fadeInUp 0.4s ease-out; }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "<div class='app-header'><h1>🧮 QueryIQ</h1>"
    "<p>Ask questions in plain English about your CSV or Excel data — every answer is backed by real, executed pandas code.</p></div>",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history: list[QAResult] = []
if "agent" not in st.session_state:
    st.session_state.agent: CSVQAAgent | None = None
if "csv_source" not in st.session_state:
    st.session_state.csv_source = None
if "session_id" not in st.session_state:
    st.session_state.session_id: int | None = None


def load_agent(csv_path: Path) -> None:
    try:
        st.session_state.agent = CSVQAAgent(csv_path)
        st.session_state.csv_source = str(csv_path)
        # Open the most recent chat for this dataset, or start a fresh one
        # if none exists yet — same as opening a chat app for the first time.
        sessions = history_store.list_sessions(str(csv_path))
        if sessions:
            st.session_state.session_id = sessions[0]["id"]
            st.session_state.history = history_store.load_session(st.session_state.session_id)
        else:
            st.session_state.session_id = history_store.create_session(str(csv_path))
            st.session_state.history = []
    except ConfigurationError as exc:
        st.session_state.agent = None
        st.error(f"⚠️ Configuration error: {exc}")
    except DataLoadError as exc:
        st.session_state.agent = None
        st.error(f"⚠️ Could not load file: {exc}")


# --------------------------------------------------------------------------
# Sidebar — dataset selection + stats
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"### <span style='color:{NAVY}'>⚙️ Controls</span>", unsafe_allow_html=True)
    st.divider()

    default_csv = Path("data/sales_data.csv")
    source = st.radio("Dataset", ["Use sample dataset", "Upload my own CSV"], index=0)

    if source == "Use sample dataset":
        if st.session_state.csv_source != str(default_csv):
            load_agent(default_csv)
    else:
        uploaded = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx", "xls"])
        if uploaded is not None:
            suffix = Path(uploaded.name).suffix or ".csv"
            tmp_path = Path(f"data/_uploaded{suffix}")
            tmp_path.write_bytes(uploaded.getvalue())
            if st.session_state.csv_source != str(tmp_path):
                load_agent(tmp_path)

    if st.session_state.agent:
        agent = st.session_state.agent
        st.divider()
        st.markdown("### Dataset overview")
        c1, c2 = st.columns(2)
        c1.markdown(f"<div class='metric-card'><b>{len(agent.df):,}</b><br>rows</div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'><b>{len(agent.df.columns)}</b><br>columns</div>", unsafe_allow_html=True)
        with st.expander("Columns"):
            for col in agent.schema.columns:
                st.markdown(f"**{col.name}** · `{col.dtype}`")

        st.divider()
        st.markdown("### Try a sample question")
        sample_questions = [
            "What is the total revenue across all orders?",
            "Which region generated the highest total revenue?",
            "Compare average revenue per order between VIP and New customers.",
        ]
        for q in sample_questions:
            if st.button(q, use_container_width=True, key=f"sample_{q}"):
                st.session_state["pending_question"] = q

        st.divider()
        st.markdown("### 💬 Chats")
        if st.button("➕ New chat", use_container_width=True):
            st.session_state.session_id = history_store.create_session(st.session_state.csv_source)
            st.session_state.history = []
            st.rerun()

        for sess in history_store.list_sessions(st.session_state.csv_source):
            is_active = sess["id"] == st.session_state.session_id
            created = datetime.fromisoformat(sess["created_at"]).strftime("%b %d, %Y · %I:%M %p UTC")

            row = st.columns([5, 1])
            label = ("🟢 " if is_active else "") + sess["name"]
            if row[0].button(label, key=f"open_{sess['id']}", use_container_width=True):
                st.session_state.session_id = sess["id"]
                st.session_state.history = history_store.load_session(sess["id"])
                st.rerun()
            if row[1].button("🗑️", key=f"del_{sess['id']}", help="Delete this chat"):
                history_store.delete_session(sess["id"])
                if is_active:
                    st.session_state.session_id = None
                    st.session_state.history = []
                st.rerun()

            st.caption(f"{created} · {sess['message_count']} message(s)")
            with st.expander("✏️ Rename", expanded=False):
                new_name = st.text_input(
                    "New name", value=sess["name"], key=f"rename_input_{sess['id']}", label_visibility="collapsed"
                )
                if st.button("Save name", key=f"rename_btn_{sess['id']}", use_container_width=True):
                    history_store.rename_session(sess["id"], new_name)
                    st.rerun()

        if st.session_state.history:
            st.divider()
            transcript = json.dumps([r.to_json_dict() for r in st.session_state.history], indent=2)
            st.download_button(
                "⬇️ Download transcript (JSON)",
                data=transcript,
                file_name="qa_transcript.json",
                mime="application/json",
                use_container_width=True,
            )

# --------------------------------------------------------------------------
# Main panel
# --------------------------------------------------------------------------
st.caption("QueryIQ · Powered by Groq (Llama 3.3 70B) · Answers are computed via sandboxed pandas execution, never guessed.")

if not st.session_state.agent:
    st.info("⬅️ Choose or upload a CSV or Excel dataset in the sidebar to get started. Make sure `GROQ_API_KEY` is set in `.env`.")
    st.stop()

agent = st.session_state.agent

if st.session_state.session_id is None:
    # The active chat was just deleted — start a new one so the user always
    # has somewhere to type, rather than hitting a dead end.
    st.session_state.session_id = history_store.create_session(st.session_state.csv_source)
    st.session_state.history = []

if st.session_state.history:
    with st.expander(f"📊 History analytics ({len(st.session_state.history)} questions asked)", expanded=False):
        hist_df = pd.DataFrame(
            [
                {
                    "success": qa.success,
                    "mode": "General knowledge" if qa.mode == AnswerMode.GENERAL_KNOWLEDGE else "Code execution",
                    "from_cache": qa.from_cache,
                }
                for qa in st.session_state.history
            ]
        )
        total = len(hist_df)
        success_rate = hist_df["success"].mean() * 100
        cache_rate = hist_df["from_cache"].mean() * 100

        m1, m2, m3 = st.columns(3)
        m1.markdown(f"<div class='metric-card'><b>{total}</b><br>questions asked</div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-card'><b>{success_rate:.0f}%</b><br>success rate</div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-card'><b>{cache_rate:.0f}%</b><br>answered from cache</div>", unsafe_allow_html=True)

        mode_counts = hist_df["mode"].value_counts().reset_index()
        mode_counts.columns = ["mode", "count"]
        fig = px.bar(
            mode_counts, x="mode", y="count", color="mode",
            color_discrete_sequence=[ROYAL_BLUE, AMBER],
        )
        fig.update_layout(
            template="plotly_white", height=240, margin=dict(l=10, r=10, t=20, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, font=dict(color=TEXT_DARK), xaxis_title="", yaxis_title="questions",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            f"Cache hits mean the LLM codegen call was skipped for a paraphrase of an earlier "
            f"question — {cache_rate:.0f}% of questions in this session didn't need a fresh LLM call."
        )

question = st.chat_input("Ask a question about your data…")
if "pending_question" in st.session_state:
    question = st.session_state.pop("pending_question")

if question:
    with st.spinner("Thinking in pandas…"):
        try:
            qa = agent.ask(question)
        except AgentError as exc:
            st.error(f"Agent error: {exc}")
            qa = None
    if qa is not None:
        st.session_state.history.append(qa)
        history_store.save(st.session_state.session_id, qa)

# --------------------------------------------------------------------------
# Render history (oldest first, newest at the bottom — like a normal chat)
# --------------------------------------------------------------------------
for qa in st.session_state.history:
    if qa.mode == AnswerMode.GENERAL_KNOWLEDGE:
        badge = f"<span class='badge' style='background:#FEF3C7;color:{AMBER}'>GENERAL KNOWLEDGE</span>"
    elif qa.success and qa.from_cache:
        badge = f"<span class='badge badge-ok' style='background:#DBEAFE;color:{ROYAL_BLUE}'>⚡ CACHED</span>"
    elif qa.success:
        badge = "<span class='badge badge-ok'>SUCCESS</span>"
    else:
        badge = "<span class='badge badge-fail'>FAILED</span>"
    st.markdown(
        f"<div class='qa-card'><div class='qa-question'>❓ {qa.question}  {badge}</div>"
        f"<div style='font-size:0.75rem;color:{TEXT_MUTED};margin-bottom:0.4rem;'>"
        f"{qa.timestamp.strftime('%b %d, %Y · %I:%M %p UTC')}</div>",
        unsafe_allow_html=True,
    )

    if qa.mode == AnswerMode.GENERAL_KNOWLEDGE:
        st.caption(
            "This question wasn't about your dataset, so no code was executed — "
            "answered directly from the model's general knowledge instead."
        )
        st.markdown(f"<div class='qa-answer'>💡 {qa.explanation}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        continue

    with st.expander("View generated pandas code", expanded=False):
        st.code(qa.code, language="python")
        st.caption(f"Attempts: {qa.attempts}")

    if qa.success:
        # Smart rendering based on result shape
        if qa.result_type == ResultType.TABLE and isinstance(qa.result, list):
            st.dataframe(pd.DataFrame(qa.result), use_container_width=True)
        elif qa.result_type == ResultType.DICT and isinstance(qa.result, dict):
            cols = st.columns(len(qa.result) or 1)
            for col, (k, v) in zip(cols, qa.result.items()):
                col.metric(str(k), v)
            if len(qa.result) > 1 and all(isinstance(v, (int, float)) for v in qa.result.values()):
                fig = px.bar(
                    x=list(qa.result.keys()), y=list(qa.result.values()), labels={"x": "", "y": ""},
                    color_discrete_sequence=[ROYAL_BLUE],
                )
                fig.update_layout(
                    template="plotly_white", height=280, margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color=TEXT_DARK),
                )
                st.plotly_chart(fig, use_container_width=True)
        elif qa.result_type == ResultType.SCALAR:
            st.metric(label="Result", value=qa.result)
        else:
            st.write(qa.result)

        st.markdown(f"<div class='qa-answer'>💡 {qa.explanation}</div>", unsafe_allow_html=True)
    else:
        st.error(f"Failed after {qa.attempts} attempt(s): {qa.error}")

    st.markdown("</div>", unsafe_allow_html=True)

if not st.session_state.history:
    st.markdown(
        "<div class='qa-card'>👋 Ask a question above, or click a sample question in the sidebar to get started.</div>",
        unsafe_allow_html=True,
    )

# Auto-scroll to the newest message at the bottom, like a normal chat UI.
if st.session_state.history:
    st.markdown("<div id='bottom-anchor'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <script>
        var anchor = window.parent.document.getElementById('bottom-anchor');
        if (anchor) { anchor.scrollIntoView({behavior: 'smooth', block: 'end'}); }
        </script>
        """,
        unsafe_allow_html=True,
    )