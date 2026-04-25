# Agentic RAG over Indian IT Company Financials

An LLM agent that answers questions about Infosys, TCS, and Wipro
by reasoning over three data sources: annual report PDFs, structured
financial data, and live web search.

Built as part of an internship selection assignment. The agent
decides which tool to call, retrieves information, and composes
a grounded answer with citations. It handles single-tool questions,
multi-tool reasoning, graceful refusals, and partial answers when
retrieval is incomplete.

---

## What it does

- Routes questions to the right tool automatically
- Combines data from multiple tools for complex questions
- Cites exactly which source each claim came from
- Refuses investment advice and out-of-scope questions
- Stops gracefully when it cannot find a complete answer
- Saves a structured trace for every run

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Anthropic Claude Haiku (tool use API) |
| Vector Store | ChromaDB (local, persistent) |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 |
| PDF Extraction | pdfplumber |
| Structured Data | pandas + CSV |
| Web Search | Tavily API |
| Language | Python 3.12 |

---

## Corpus

- **Companies:** Infosys, TCS, Wipro
- **Years:** FY2021 to FY2024
- **Unstructured:** 9 annual report PDFs — 5,413 indexed chunks
- **Structured:** 12-row financials CSV
- **Live:** Web search via Tavily API

---

## Project Structure
synapt-rag/
├── data/
│   ├── raw/               # Annual report PDFs (not committed)
│   └── processed/         # ChromaDB index + financials CSV
├── tools/
│   ├── search_docs.py     # Semantic search over PDFs
│   ├── query_data.py      # Structured financial queries
│   └── web_search.py      # Live web search via Tavily
├── agent/
│   └── loop.py            # Agent loop
├── evaluation/
│   ├── run_eval.py        # Evaluation runner
│   └── eval_results_*.json
├── docs/
│   ├── DESIGN.md          # Agent design document
│   └── EVALUATION.md      # Evaluation report
├── traces/                # Per-run JSON traces (not committed)
├── .env.example
├── requirements.txt
└── README.md

---

## Setup

```bash
git clone https://github.com/AvaneeshSabariH/synapt-rag.git
cd synapt-rag

python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

cp .env.example .env
# Add your real API keys to .env
```

Add your annual report PDFs to `data/raw/` then build the index:

```bash
py -m tools.search_docs
```

---

## Running the Agent

Single question:

```python
from agent.loop import run_agent
result = run_agent("What was TCS revenue in FY2024?")
print(result["answer"])
```

Run full evaluation set:

```bash
py -m evaluation.run_eval
```

---

## Evaluation Results

24 questions across 4 categories. Overall accuracy: 23/24 (95.8%)

| Category | Pass | Fail |
|---|---|---|
| Single-tool | 9/10 | 1 |
| Multi-tool | 6/6 | 0 |
| Refusals | 4/4 | 0 |
| Edge cases | 4/4 | 0 |

---

## Demo

Screen recording showing a single-tool query, a multi-tool trace,
and a graceful refusal.

[Watch demo on YouTube](https://youtu.be/ZLqaTym_ruw)

---

## Known Failure Modes

**Search loops on broad qualitative questions** — fixed with a
consecutive-tool fallback that composes a partial answer after
3 repeated calls instead of hitting the hard cap.

**Year-specific retrieval is imprecise** — chunk metadata does
not tag fiscal year, so qualitative queries for a specific year
may retrieve chunks from adjacent years.

**Keyword matching in query_data** — complex or ambiguous
phrasings may miss the intended filter. SQL would be more robust.

---

## AI Assistance Disclosure

Claude and GitHub Copilot were used during development for code
suggestions and debugging. All design decisions, tool schemas,
agent loop logic, and evaluation analysis are my own.