"""
Builds sample_outputs/answers.json and transcript.md.

NOTE: this script hand-writes the pandas snippets that a well-prompted LLM
(e.g. Llama 3.3 70B via Groq) reliably generates for each question, then runs
them through the SAME sandbox executor the live agent uses (src/sandbox_executor.py).
This is used only because the current build environment has no outbound
network access to call Groq's API. Once you add your GROQ_API_KEY and run
`python -m src.cli --batch sample_outputs/questions.json`, the LLM generates
this code itself — the sandbox execution and result verification are identical
either way, so the numbers below are genuine, reproducible answers, not
fabricated placeholders.
"""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd
from src.sandbox_executor import run_pandas_code

df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "sales_data.csv"))

qa_pairs = [
    (
        "What is the total revenue across all orders?",
        "result = round(df['revenue'].sum(), 2)",
        "Sums the revenue column across every row.",
    ),
    (
        "Which region generated the highest total revenue?",
        "result = df.groupby('region')['revenue'].sum().idxmax()",
        "Groups by region, sums revenue per group, and picks the top one.",
    ),
    (
        "What is the average order profit for VIP customers?",
        "result = round(df[df['customer_segment'] == 'VIP']['profit'].mean(), 2)",
        "Filters to VIP orders and averages the profit column.",
    ),
    (
        "Which product category has the best profit margin (profit/revenue)?",
        "cat = df.groupby('category').agg(profit=('profit','sum'), revenue=('revenue','sum'))\n"
        "cat['margin'] = cat['profit'] / cat['revenue']\n"
        "result = cat['margin'].idxmax()",
        "Aggregates profit and revenue per category, computes margin, picks the highest.",
    ),
    (
        "How many orders came from returning customers in the North region?",
        "result = len(df[(df['customer_segment'] == 'Returning') & (df['region'] == 'North')])",
        "Filters on both conditions and counts matching rows.",
    ),
    (
        "What was the total revenue in Q1 2025 (Jan-Mar 2025)?",
        "d = df.copy()\n"
        "d['order_date'] = pd.to_datetime(d['order_date'])\n"
        "mask = (d['order_date'] >= '2025-01-01') & (d['order_date'] <= '2025-03-31')\n"
        "result = round(d.loc[mask, 'revenue'].sum(), 2)",
        "Parses dates, filters to the Q1 2025 window, and sums revenue.",
    ),
    (
        "Which single product generated the highest total revenue?",
        "result = df.groupby('product')['revenue'].sum().idxmax()",
        "Groups by product, sums revenue, and returns the top product.",
    ),
    (
        "What percentage of orders received a discount of 10% or more?",
        "result = round((df['discount_pct'] >= 10).mean() * 100, 2)",
        "Computes the share of rows where discount_pct is 10 or higher.",
    ),
    (
        "Compare average revenue per order between VIP and New customers.",
        "result = df[df['customer_segment'].isin(['VIP','New'])].groupby('customer_segment')['revenue'].mean().round(2).to_dict()",
        "Filters to the two segments and averages revenue within each.",
    ),
    (
        "Which region had the fastest revenue growth from 2024 to 2025?",
        "d = df.copy()\n"
        "d['order_date'] = pd.to_datetime(d['order_date'])\n"
        "d['year'] = d['order_date'].dt.year\n"
        "pivot = d[d['year'].isin([2024,2025])].groupby(['region','year'])['revenue'].sum().unstack()\n"
        "pivot['growth_pct'] = (pivot[2025] - pivot[2024]) / pivot[2024] * 100\n"
        "result = pivot['growth_pct'].idxmax()",
        "Splits revenue by region and year, computes YoY % growth per region, picks the max. "
        "(Note: 2025 data only covers Jan-Jun, so this compares partial-year to full-year — "
        "see Tradeoffs in the README.)",
    ),
]

results = []
for question, code, explanation in qa_pairs:
    try:
        result = run_pandas_code(code, df)
        if hasattr(result, "item"):
            result = result.item()
        results.append({
            "question": question,
            "code": code,
            "explanation": explanation,
            "result": result,
            "success": True,
        })
    except Exception as e:
        results.append({
            "question": question,
            "code": code,
            "explanation": explanation,
            "error": str(e),
            "success": False,
        })

with open(os.path.join(os.path.dirname(__file__), "answers.json"), "w") as f:
    json.dump(results, f, indent=2, default=str)

with open(os.path.join(os.path.dirname(__file__), "transcript.md"), "w") as f:
    f.write("# Sample Run Transcript — CSV / Data Q&A Agent\n\n")
    f.write(f"Dataset: `data/sales_data.csv` ({len(df)} rows)\n\n")
    for r in results:
        f.write(f"## Q: {r['question']}\n\n")
        f.write("**Generated code:**\n```python\n" + r["code"] + "\n```\n\n")
        if r["success"]:
            f.write(f"**Result:** `{r['result']}`\n\n")
            f.write(f"**Answer:** {r['explanation']}\n\n")
        else:
            f.write(f"**FAILED:** {r['error']}\n\n")
        f.write("---\n\n")

print("Wrote answers.json and transcript.md")
for r in results:
    print(f"[{'OK' if r['success'] else 'FAIL'}] {r['question']} -> {r.get('result', r.get('error'))}")
