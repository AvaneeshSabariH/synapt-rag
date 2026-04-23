# Design Document — Agentic RAG over Indian IT Company Financials

## Overview

This project is a small LLM agent that answers questions about
Infosys, TCS, and Wipro by reasoning over three data sources:
annual report PDFs, structured financial data, and live web search.
The agent decides which tool to call, retrieves information, and
composes a grounded answer with citations.

---

## Agent Loop

The agent loop is implemented as a plain Python while loop in
`agent/loop.py`. It runs for a maximum of 8 steps. Here is how
it works step by step:

**Step 1 — Receive question**
The user's question is added to a messages list as the first
user turn.

**Step 2 — Call Claude with tools**
Claude receives the question along with the three tool definitions.
It reads the tool descriptions and decides either to call a tool
or to answer directly without calling any tool.

**Step 3 — Check stop reason**
If Claude's stop reason is `tool_use`, it wants to call a tool.
If the stop reason is `end_turn`, it has composed a final answer
and the loop exits.

**Step 4 — Run the tool**
The agent reads which tool Claude selected and what input it
provided. It runs that tool locally and gets back a result.

**Step 5 — Feed result back**
The tool result is added to the messages list as a `tool_result`
block. Claude now sees both its own tool call and the result.

**Step 6 — Repeat**
The loop goes back to Step 2. Claude now has more context and
decides whether to call another tool or compose the final answer.

**Step 7 — Compose final answer**
When Claude is satisfied with the retrieved information, it writes
a final answer citing which tool and source produced each claim.

**Step 8 — Save trace**
Every run saves a JSON trace file recording every tool call made,
the input sent, the output received, and the final answer.

---

## Termination Conditions

The loop has three ways to terminate:

**Normal termination** — Claude returns `end_turn`, meaning it has
enough information to answer. This is the happy path.

**Hard cap** — If the step counter exceeds 8, the loop raises a
structured refusal and returns `status: cap_reached`. This prevents
infinite loops. The cap is enforced in code, not just prompted.

**Consecutive-tool fallback** — If the same tool is called 3 or
more times in a row, the agent stops retrying and composes the
best possible partial answer from what it accumulated. This prevents
search loops on broad qualitative questions. Status returned is
`fallback_composed`.

---

## Tool Schemas

### search_docs

**Purpose:** Semantic search over annual report PDFs.

**When to use:** Questions about qualitative information —
management commentary, strategic priorities, risk factors,
reasons behind performance, or any narrative explanation.

**When not to use:** Specific numbers, live prices, recent news.

**Input:**
```json{
"query": "string — natural language search query"
}
```

**Output:**
```json{
"query": "string",
"results": [
{
"chunk": "string — retrieved text",
"source": "string — PDF filename",
"page": "integer — page number",
"distance": "float — similarity score"
}
],
"result_count": "integer"
}
```

**Implementation:** Text is extracted from PDFs using pdfplumber,
split into 500-word chunks with 50-word overlap, embedded using
the all-MiniLM-L6-v2 sentence transformer model, and stored in
a local ChromaDB vector store. At query time the question is
embedded and the 3 nearest chunks are returned by cosine similarity.

---

### query_data

**Purpose:** Query structured financial data for Infosys, TCS,
and Wipro from FY2021 to FY2024.

**When to use:** Questions asking for specific numbers, trends,
comparisons, or calculations — revenue, margin, profit, EPS,
headcount.

**When not to use:** Qualitative questions, strategy, or recent news.

**Input:**
```json{
"question": "string — natural language question about financial data"
}
```

**Output:**
```json{
"question": "string",
"columns": ["array of column names"],
"data": [{"company": "...", "fiscal_year": "...", "metric": "..."}],
"row_count": "integer"
}
```

**Implementation:** A 12-row CSV (3 companies × 4 years) is loaded
into a pandas DataFrame at startup. The tool parses the question
for company names, fiscal years, and metric keywords, then filters
and returns the relevant rows.

---

### web_search

**Purpose:** Live web search for current information.

**When to use:** Current stock prices, recent news, analyst ratings,
or anything not found in static documents.

**When not to use:** Historical financials or document content.

**Input:**
```json{
"query": "string — short search query under 10 words"
}
```

**Output:**
```json{
"query": "string",
"results": [
{
"title": "string",
"snippet": "string",
"url": "string",
"date": "string"
}
],
"result_count": "integer"
}
```

**Implementation:** Calls the Tavily API with max_results=3 and
include_published_date=True. Returns title, snippet, URL, and
publication date for each result. Queries longer than 10 words
are silently trimmed.

---

## How Infinite Loops Are Prevented

Three mechanisms work together:

**1. Hard cap at 8 steps** — enforced by a step counter in the
while loop condition. If step exceeds MAX_STEPS, the loop
immediately returns a structured refusal without calling Claude
again.

**2. Consecutive-tool fallback at 3 repeats** — a separate counter
tracks how many times the same tool has been called in a row.
At 3 consecutive calls, the agent stops and composes a partial
answer from accumulated results rather than retrying.

**3. Clear tool descriptions with negative examples** — each tool
description tells Claude both when to use it and when not to.
This reduces the chance of Claude calling the wrong tool or
making unnecessary calls in the first place.

---

## Trace Format

Every agent run produces a JSON trace saved to the `traces/`
directory. Example:

```json{
"question": "What was Infosys revenue in FY2023?",
"answer": "Infosys revenue in FY2023 was ₹146,767 crores.",
"trace": [
{
"step": 1,
"tool": "query_data",
"input": {"question": "What was Infosys revenue in FY2023?"},
"output_preview": "{"data": [{"revenue_cr": 146767}]}"
}
],
"steps_used": 1,
"status": "success"
}
```

---

## Known Limitations

**Chunk retrieval is imprecise for year-specific qualitative
questions** — chunk metadata does not tag fiscal year, so
retrieval for "Infosys FY2024 margin explanation" may return
chunks from FY2022 or FY2023 reports instead.

**query_data uses keyword matching, not SQL** — the tool parses
questions with simple keyword detection. Complex or ambiguous
phrasings may match the wrong columns or miss the intended filter.

**web_search has no date filter** — results are ranked by
relevance, not recency. For very recent events, the top result
may not be the most current.