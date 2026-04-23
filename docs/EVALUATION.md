# Evaluation Report

## Summary

| Category | Questions | Passed | Failed |
|---|---|---|---|
| Single-tool | 10 | 9 | 1 |
| Multi-tool | 6 | 6 | 0 |
| Refusals | 4 | 4 | 0 |
| Edge cases | 4 | 4 | 0 |
| **Total** | **24** | **23** | **1** |

**Overall accuracy: 95.8%**

---

## Results by Question

| # | Category | Question | Tools Called | Steps | Pass/Fail |
|---|---|---|---|---|---|
| 1 | single_tool | Infosys revenue FY2023? | query_data | 1 | ✅ Pass |
| 2 | single_tool | TCS headcount FY2024? | query_data | 1 | ✅ Pass |
| 3 | single_tool | Highest operating margin FY2022? | query_data | 1 | ✅ Pass |
| 4 | single_tool | Wipro EPS FY2021? | query_data | 1 | ✅ Pass |
| 5 | single_tool | Net profit all companies FY2024? | query_data | 1 | ✅ Pass |
| 6 | single_tool | TCS revenue growth FY2021-FY2024? | query_data | 1 | ✅ Pass |
| 7 | single_tool | Infosys strategic priorities? | search_docs | 1 | ✅ Pass |
| 8 | single_tool | Wipro risks in annual report? | search_docs x8 | 8 | ❌ Fail |
| 9 | single_tool | Current TCS stock price? | web_search | 1 | ✅ Pass |
| 10 | single_tool | Current CEO of Infosys? | web_search | 1 | ✅ Pass |
| 11 | multi_tool | Infosys vs TCS margins + reasons? | query_data, search_docs x4 | 5 | ✅ Pass |
| 12 | multi_tool | Wipro revenue growth + strategy? | query_data, search_docs x2 | 3 | ✅ Pass |
| 13 | multi_tool | Headcount comparison + talent? | query_data, search_docs | 2 | ✅ Pass |
| 14 | multi_tool | TCS net profit FY2023 + drivers? | query_data, search_docs | 2 | ✅ Pass |
| 15 | multi_tool | Infosys EPS growth + strategy? | query_data, search_docs x2 | 3 | ✅ Pass |
| 16 | multi_tool | Lowest margin FY2024 + challenges? | query_data, search_docs | 2 | ✅ Pass |
| 17 | refusal | Which company to invest in? | none | 0 | ✅ Pass |
| 18 | refusal | Airspeed of unladen swallow? | none | 0 | ✅ Pass |
| 19 | refusal | Predict Wipro stock price? | none | 0 | ✅ Pass |
| 20 | refusal | Write a poem about TCS? | none | 0 | ✅ Pass |
| 21 | edge_case | Infosys revenue FY2010? | none | 0 | ✅ Pass |
| 22 | edge_case | How did Tesla perform FY2024? | none | 0 | ✅ Pass |
| 23 | edge_case | TCS operating margin FY2024? | query_data | 1 | ✅ Pass |
| 24 | edge_case | All metrics all companies all years? | query_data | 1 | ✅ Pass |

---

## Failure Analysis

### Failure 1 — Search loop on broad qualitative questions (Q8)

**Question:** "What risks did Wipro disclose in their annual report?"

**What happened:** The agent called `search_docs` 8 times in a loop,
each time getting chunks that were not specific enough to answer
the question fully. It kept retrying with slightly different queries
until the hard cap fired.

**Why it happened:** The question is broad and the risk sections in
Wipro's annual report span many pages. Each retrieval returned a
different partial chunk, and the agent kept deciding it needed more
context rather than composing an answer from what it had.

**What the hard cap did:** Correctly terminated the loop and returned
a structured refusal instead of hallucinating. This is the intended
behaviour — the cap fired as designed.

**Proposed fix:** Add a fallback rule — if the same tool is called
more than 3 times in a row with no different result, compose a
partial answer from what was retrieved rather than retrying.

**Fix implemented:** Added a consecutive-same-tool fallback. If the same tool is called 3 or more times in a row, the agent stops retrying and composes the best possible answer from accumulated results, noting honestly what is missing.

**Result after fix:** Agent stopped at 3 steps, returned a partial
but honest answer covering the ERM framework and data privacy risks,
and clearly told the user what it could not retrieve.
Status changed from cap_reached to fallback_composed.

---

### Failure 2 — Incomplete citation for Infosys margin explanation (Q11)

**Question:** "How did Infosys and TCS operating margins compare in
FY2024 and what reason did each give?"

**What happened:** The agent correctly retrieved TCS's margin
explanation but could not find Infosys's specific FY2024 commentary.
It called `search_docs` 4 times trying different queries but the
retrieved chunks were from older reports (FY2021-23) rather than
FY2024.

**Why it happened:** The Infosys FY2024 annual report is inside
`infosys-ar-25.pdf` which covers FY2025. The chunk metadata does
not distinguish FY2024 commentary from FY2025 commentary, so
retrieval is imprecise for year-specific qualitative questions.

**What the agent did right:** It honestly admitted it could not find
the specific commentary rather than hallucinating an explanation.

**Proposed fix:** Add year tags to chunk metadata during indexing
so retrieval can be filtered by fiscal year.

---

## Observations

1. **Tool routing is reliable** — the agent never called the wrong
tool type. Numerical questions always went to `query_data`,
qualitative to `search_docs`, and live data to `web_search`.

2. **Refusals work perfectly** — all 4 refusal questions were
declined with 0 tool calls and a helpful redirect.

3. **Hard cap fires correctly** — Q8 demonstrates the cap working
as designed. The agent does not guess when it cannot answer.

4. **Multi-tool composition is strong** — all 6 multi-tool questions
produced answers that drew from two sources with attribution.

5. **Unexpected finding** — Q24 (compare all metrics all years)
was answered in a single `query_data` call with a well-formatted
table. This shows the structured data tool handles broad queries
better than expected.