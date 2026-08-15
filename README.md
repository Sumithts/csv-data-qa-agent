# QueryIQ — CSV / Data Q&A Agent
QueryIQ is a Python-based AI agent that lets you ask questions about a CSV or Excel dataset using plain English.
Instead of manually writing pandas code for every question, QueryIQ understands the question, generates the required data-analysis code, executes it against the dataset, and uses the result to answer the question.
The main goal of this project is simple: **ask questions about your data and get answers backed by real, executed computation.**
**---**
## Table of Contents**
- [What It Does]\(#what-it-does)
- [Why This Approach]\(#why-this-approach)
- [Features]\(#features)
- [Quick Start]\(#quick-start)
- [Web UI]\(#web-ui)
- [CLI]\(#cli)
- [Project Structure]\(#project-structure)
- [Sample Questions and Answers]\(#sample-questions-and-answers)
- [Running Tests]\(#running-tests)
- [Design Tradeoffs]\(#design-tradeoffs)
- [Tech Stack]\(#tech-stack)
- [Troubleshooting]\(#troubleshooting)
- [Project Notes]\(#project-notes)
- [Challenge Submission]\(#challenge-submission)
**---**
## What It Does**
QueryIQ takes a CSV or Excel file and provides a conversational interface for data analysis.
For example, with a sales dataset, you can ask:
- What is the total revenue?
- Which region generated the highest revenue?
- Which product has the highest profit?
- What is the average order value?
- Show me the monthly sales trend.
- How many orders were placed?
- Which category performed best?
- What are the top 5 products by revenue?
The agent converts the question into executable pandas code, runs the code against the dataset, and uses the result to produce the final answer.
This means the numerical answer comes from the actual dataset rather than from the language model trying to guess it.
**---**
## Why This Approach**
A normal chatbot can describe a dataset, but it can also make mistakes when answering numerical questions.
QueryIQ uses a different flow:
```text
User Question
↓
Understand the question
↓
Generate pandas code
↓
Validate the generated code
↓
Execute code against the dataset
↓
Collect the computed result
↓
Generate a natural-language explanation
↓
Return answer + computation details
```
**---**
## Features**
**### Data Analysis**
- CSV dataset support
- Excel dataset support
- Automatic schema inspection
- Row and column information
- Pandas-based computation
- Aggregation and grouping
- Filtering and sorting
- Trend analysis
- Statistical calculations
**### AI Agent**
- Natural-language questions
- LLM-generated pandas code
- Runtime execution
- Retry when generated code fails
- Error feedback to the model
- Short-circuit handling for greetings and simple messages
- General-knowledge fallback for questions that are not related to the dataset
**### Safety**
Generated code is checked before execution.
The sandbox rejects dangerous operations such as:
- Imports
- File access
- Network access
- Dangerous built-ins
- Dunder attributes
- Restricted modules
- Unsafe expressions
The source DataFrame is also protected from accidental modification during execution.
**### Application**
- Streamlit web interface
- Command-line interface
- Persistent chat/session history
- Query history storage
- Query caching
- Session analytics
- JSON-safe storage of pandas/NumPy results
**---**
## Quick Start**
**### 1. Clone the repository**
```bash
git clone https://github.com/Sumithts/csv-data-qa-agent.git
cd csv-data-qa-agent
```
**### 2. Create a virtual environment**
On Windows:
```bash
python -m venv venv
```
Activate it in Git Bash:
```bash
source venv/Scripts/activate
```
Or in Windows Command Prompt:
```cmd
venv\Scripts\activate
```
**### 3. Install dependencies**
```bash
pip install -r requirements.txt
```
**### 4. Configure the API key**
Create a local `.env` file:
```text
GROQ_API_KEY=your_api_key_here
```
The repository contains `.env.example` as a template.
Do not commit your real `.env` file to GitHub.
**### 5. Start the application**
```bash
streamlit run app.py
```
Then open:
```text
http://localhost:8501
```
**---**
## Web UI**
The Streamlit interface allows you to:
1. Load a CSV or Excel dataset.
2. Inspect the dataset.
3. Ask questions in plain English.
4. Let the agent generate the required pandas computation.
5. Execute the computation.
6. View the final answer.
7. Inspect the generated analysis/code.
8. Continue the conversation using the stored session history.
The application currently works with one CSV or Excel dataset at a time.
**---**
## CLI**
QueryIQ can also be used from the command line.
Run:
```bash
python -m src.cli
```
Follow the prompts to load the dataset and ask questions.
Example:
```text
> What is the total revenue?
Total revenue is 987999.41.
```
**---**
## Project Structure**
```text
csv-data-qa-agent/
│
├── app.py
├── build_report.py
├── README.md
├── PROJECT_EXPLAINER.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── data/
│ ├── generate_data.py
│ ├── sales_data.csv
│ └── history.db
│
├── sample_outputs/
│ ├── answers.json
│ ├── questions.json
│ ├── build_sample_outputs.py
│ └── transcript.md
│
├── src/
│ ├── agent.py
│ ├── cli.py
│ ├── config.py
│ ├── exceptions.py
│ ├── history_store.py
│ ├── llm_client.py
│ ├── logging_config.py
│ ├── models.py
│ ├── query_cache.py
│ ├── sandbox_executor.py
│ └── schema.py
│
└── tests/
├── test_agent.py
└── test_sandbox.py
```
**### Important files**
****`app.py`****
Main Streamlit application.
****`src/agent.py`****
Controls the main agent workflow:
- understands the question
- generates analysis code
- executes the code
- retries failed computations
- formats the final answer
****`src/llm_client.py`****
Handles communication with the configured LLM provider.
****`src/sandbox_executor.py`****
Validates and executes generated pandas code in a restricted environment.
****`src/schema.py`****
Handles dataset/schema information provided to the agent.
****`src/history_store.py`****
Stores query and session history.
****`src/query_cache.py`****
Provides query caching to avoid unnecessary repeated work.
****`tests/`****
Contains automated tests for the agent and sandbox.
**---**
## Sample Questions and Answers**
The included sample dataset contains sales records that can be queried using natural language.
Some example questions tested with the application are:
**### 1. What is the total revenue?**
```text
987999.41
```
**### 2. Which region generated the highest revenue?**
```text
North
```
**### 3. Which product has the highest profit?**
```text
4K Monitor
```
**### 4. What is the average order value?**
```text
493.999705
```
The exact answer depends on the dataset being queried.
The important part is that these answers are produced by executing pandas computations against the dataset.
**---**
## Running Tests**
The project includes automated tests for the main agent and sandbox behavior.
Run:
```bash
pytest -q
```
Current test result:
```text
17 passed
```
The tests cover areas including:
- Dataset schema handling
- Successful first-attempt queries
- Retry after runtime errors
- Unsafe code rejection
- General-knowledge fallback
- Greeting handling
- Pandas aggregation
- Groupby operations
- Import rejection
- File access rejection
- Dunder access rejection
- Forbidden module handling
- Missing result handling
- Runtime error handling
- Syntax error handling
- Source DataFrame immutability
**---**
## Design Tradeoffs**
**### LLM-generated pandas code**
The main advantage is flexibility.
Instead of manually implementing every possible question, the agent can generate analysis code for many different types of questions.
The tradeoff is that generated code can sometimes be incorrect.
To handle this, QueryIQ validates the generated code and retries failed computations using the runtime error as feedback.
**---**
**### Restricted execution environment**
Generated code is executed through a restricted sandbox.
The sandbox prevents operations such as imports, file access, network access, and other unsafe operations.
This improves safety compared with directly executing unrestricted LLM-generated Python.
The current implementation is intended for a local challenge/demo environment rather than a production-grade security boundary.
**---**
**### Pandas instead of a separate SQL database**
Pandas was chosen because the main input is CSV/Excel data and many questions can be answered naturally through DataFrame operations.
This keeps the implementation relatively simple while still supporting filtering, grouping, aggregation, sorting, and trend analysis.
**---**
**### Persistent history**
SQLite is used for storing session and query history.
This keeps the application lightweight and avoids requiring another database service.
The included:
```text
data/history.db
```
is part of the project because the application uses it for persistent history.
**---**
## Tech Stack**
| Component | Technology |
|---|---|
| Language | Python |
| Web UI | Streamlit |
| Data Processing | Pandas |
| Numerical Processing | NumPy |
| Validation | Pydantic |
| LLM Integration | OpenAI-compatible client / Groq |
| Database | SQLite |
| Testing | Pytest |
| Environment Variables | python-dotenv |
| Excel Support | openpyxl |
| Version Control | Git / GitHub |
**---**
## Troubleshooting**
**### `ModuleNotFoundError`**
Make sure the virtual environment is active:
```bash
source venv/Scripts/activate
```
Then install dependencies:
```bash
pip install -r requirements.txt
```
**---**
**### Streamlit does not start**
Run:
```bash
python -m streamlit run app.py
```
instead of:
```bash
streamlit run app.py
```
**---**
**### API key error**
Check that your local `.env` file contains:
```text
GROQ_API_KEY=your_api_key_here
```
Do not add `.env` to GitHub.
Only `.env.example` should be committed.
**---**
**### Excel file error**
Make sure `openpyxl` is installed:
```bash
pip install openpyxl
```
The project already includes it in `requirements.txt`.
**---**
**### Port 8501 already in use**
Run Streamlit on another port:
```bash
streamlit run app.py --server.port 8502
```
Then open:
```text
http://localhost:8502
```
**---**
## Project Notes**
This project was built as an AI-agent implementation for a practical data-question-answering task.
The application is not hard-coded to answer only the sample questions. The LLM generates the pandas analysis needed for the user's question, and Python/Pandas performs the actual calculation.
This separation is intentional:
```text
LLM
↓
Understands the question
↓
Writes analysis logic
↓
Python / Pandas
↓
Performs the actual calculation
↓
LLM
↓
Explains the result
```
This makes the system more useful than a simple chatbot that only generates text.
**---**
## Challenge Submission**
This project was developed for the ****ROOMAN AI Challenge — The 24-Hour AI Agent Challenge****.
The selected agent category is:
****CSV / Data Q&A Agent****
The implementation focuses on:
- Loading structured datasets
- Understanding natural-language questions
- Generating executable pandas analysis
- Running real computations
- Returning data-backed answers
- Showing the computation behind the answer
- Maintaining session history
- Testing the agent and sandbox behavior
**### GitHub Repository**
https://github.com/Sumithts/csv-data-qa-agent
**---**
## Final Run**
After cloning the repository, the basic workflow is:
```bash
cd csv-data-qa-agent
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```
Create `.env`:
```text
GROQ_API_KEY=your_api_key_here
```
Then run:
```bash
streamlit run app.py
```
For testing:
```bash
pytest -q
```
Expected result:
```text
17 passed
```
**---**
## License**ls -l README.md