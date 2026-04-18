# Agentic RAG over Indian IT Company Financials

An LLM agent that answers questions over a mixed corpus of annual report 
PDFs, structured financial data, and live web search. Built as part of 
an internship selection assignment.

## What it does
Given a natural language question, the agent decides which tool to call,
retrieves the relevant information, and composes a grounded answer with
citations. It handles single-tool questions, multi-tool reasoning, and
graceful refusals.

## Tech Stack

LLM -> Anthropic Claude (tool use API) 
Vector Store -> ChromaDB (local, persistent) 
Embeddings -> sentence-transformers (all-MiniLM-L6-v2) 
PDF Extraction -> pdfplumber 
Structured Data -> pandas + CSV 
Web Search -> Tavily API 
Language -> Python 3.12 

## Corpus
- **Companies:** Infosys, TCS, Wipro
- **Years:** FY2021 – FY2024
- **Unstructured:** 9 annual report PDFs (~5,413 indexed chunks)
- **Structured:** 12-row financials CSV (revenue, margin, profit, EPS, headcount)
- **Live:** Web search via Tavily API

## Project Structure

synapt-rag/
├── data/
│   ├── raw/          # Annual report PDFs
│   └── processed/    # ChromaDB index + financials CSV
├── tools/
│   ├── search_docs.py   # Semantic search over PDFs
│   ├── query_data.py    # Structured financial queries
│   └── web_search.py    # Live web search via Tavily
├── agent/
│   └── loop.py          # Agent loop (in progress)
├── docs/
│   ├── DESIGN.md        # Agent design document (to be implemented)
│   └── EVALUATION.md    # Evaluation report (to be implemented)
├── .env.example
├── requirements.txt
└── README.md

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/synapt-rag.git
cd synapt-rag
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env
# Add your real API keys to .env
```

## Current Status

web_search tool -> Complete 
query_data tool -> Complete 
search_docs tool -> Complete — 5,413 chunks indexed 
Agent loop -> In progress 
Evaluation set -> Pending 

## Known Failures
TBD — will be updated during evaluation phase.