import os
import json
import anthropic
from datetime import datetime
from dotenv import load_dotenv

from tools.search_docs import search_docs
from tools.query_data import query_data
from tools.web_search import web_search

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MAX_STEPS = 8
TRACE_DIR = "traces"

os.makedirs(TRACE_DIR, exist_ok=True)

# --- Tool definitions ---
TOOLS = [
    {
    "name": "search_docs",
    "description": (
        "Performs semantic search over annual report PDFs for Infosys, TCS, and Wipro. "
        "Use this tool when the question asks about qualitative information such as "
        "management commentary, strategic priorities, reasons behind performance, "
        "risk factors, or any narrative explanation found in annual reports. "
        "Do NOT use this for specific numbers, live prices, or recent news. "
        "Use the company and fiscal_year filters when the question targets a specific "
        "company or year to improve retrieval precision."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language search query"
            },
            "company": {
                "type": "string",
                "enum": ["Infosys", "TCS", "Wipro"],
                "description": "Filter results to a specific company"
            },
            "fiscal_year": {
                "type": "string",
                "enum": ["FY2021", "FY2022", "FY2023", "FY2024", "FY2025"],
                "description": "Filter results to a specific fiscal year"
            }
        },
        "required": ["query"]
    }
    },
    {
        "name": "query_data",
        "description": (
            "Queries the structured financial data table containing revenue, operating margin, "
            "net profit, EPS, and headcount for Infosys, TCS, and Wipro from FY2021 to FY2024. "
            "Use this tool when the question asks for specific numbers, comparisons, trends, "
            "or calculations from the financial data. "
            "Do NOT use this for qualitative questions about strategy or recent news."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Natural language question about the financial data"
                }
            },
            "required": ["question"]
        }
    },
    {
        "name": "web_search",
        "description": (
            "Searches the live web for recent information. "
            "Use this tool when the question asks about current events, recent news, "
            "live stock prices, analyst ratings, or anything that would not be found "
            "in a static document or historical financial table. "
            "Do NOT use this for historical financials or document content."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Short search query, under 10 words"
                }
            },
            "required": ["query"]
        }
    }
]

SYSTEM_PROMPT = """You are a financial research agent with access to three tools:
1. search_docs - searches annual report PDFs for qualitative information
2. query_data - queries structured financial data for numbers and trends
3. web_search - searches the live web for recent news and current information

Your job is to answer questions about Infosys, TCS, and Wipro accurately and honestly.

Rules:
- Always use the most appropriate tool for the question
- For questions needing both numbers AND explanations, call both query_data and search_docs
- Never guess or hallucinate - only state what the tools return
- Always cite exactly which tool and source produced each piece of information
- If a question is about investment advice, refuse politely without calling any tool
- If a question is completely unrelated to Infosys, TCS, Wipro, or Indian IT, refuse politely
- If you cannot find the answer after using tools, say so honestly
"""


def run_tool(tool_name: str, tool_input: dict) -> str:
    """Run the appropriate tool and return result as a string."""
    if tool_name == "search_docs":
        result = search_docs(
            tool_input["query"],
            company=tool_input.get("company"),
            fiscal_year=tool_input.get("fiscal_year")
        )
    elif tool_name == "query_data":
        result = query_data(tool_input["question"])
    elif tool_name == "web_search":
        result = web_search(tool_input["query"])
    else:
        result = {"error": f"Unknown tool: {tool_name}"}
    return json.dumps(result)


def save_trace(trace_data: dict):
    """Save trace to a JSON file in the traces directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_question = trace_data["question"][:40].replace(" ", "_").replace("?", "")
    filename = f"{TRACE_DIR}/{timestamp}_{safe_question}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, indent=2, ensure_ascii=False)
    print(f"Trace saved: {filename}")


def run_agent(question: str) -> dict:
    """
    Main agent loop. Takes a question, calls tools as needed,
    and returns a final answer with citations and trace.
    """

    print(f"\n{'='*60}")
    print(f"Question: {question}")
    print(f"{'='*60}")

    messages = [{"role": "user", "content": question}]
    trace = []
    step = 0

    # --- Fallback tracking ---
    consecutive_same_tool = 0
    last_tool_called = None
    accumulated_results = []

    while step < MAX_STEPS:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        if response.stop_reason == "tool_use":
            messages.append({
                "role": "assistant",
                "content": response.content
            })

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    step += 1
                    tool_name = block.name
                    tool_input = block.input

                    # --- TRACK CONSECUTIVE SAME TOOL CALLS ---
                    if tool_name == last_tool_called:
                        consecutive_same_tool += 1
                    else:
                        consecutive_same_tool = 1
                        last_tool_called = tool_name

                    print(f"\nStep {step}: tool={tool_name} input={tool_input}")
                    print(f"  (consecutive same tool: {consecutive_same_tool})")

                    # --- FALLBACK: same tool called 3+ times in a row ---
                    if consecutive_same_tool >= 3:
                        print(f"\n! Fallback triggered: {tool_name} called {consecutive_same_tool} times in a row.")
                        print("Composing answer from accumulated results...")

                        # Build a summary of everything retrieved so far
                        accumulated_text = "\n\n".join([
                            f"Result {i+1}:\n{r}" 
                            for i, r in enumerate(accumulated_results)
                        ])

                        # Ask Claude to compose the best answer from what it has
                        fallback_prompt = f"""You were trying to answer this question:
"{question}"

You searched for information {consecutive_same_tool} times but could not find a complete answer.
Here is everything you retrieved so far:

{accumulated_text}

Please compose the best possible answer from this information.
Be honest about what you found and what is missing.
Clearly note if the answer is incomplete.
Do not make up information that isn't in the retrieved results."""

                        fallback_response = client.messages.create(
                            model="claude-haiku-4-5-20251001",
                            max_tokens=1024,
                            system=SYSTEM_PROMPT,
                            messages=[{"role": "user", "content": fallback_prompt}]
                        )

                        final_answer = ""
                        for b in fallback_response.content:
                            if hasattr(b, "text"):
                                final_answer = b.text
                                break

                        print(f"\nFallback Answer: {final_answer}")
                        print(f"Steps used: {step} / {MAX_STEPS}")

                        result = {
                            "question": question,
                            "answer": final_answer,
                            "trace": trace,
                            "steps_used": step,
                            "status": "fallback_composed"
                        }
                        save_trace(result)
                        return result

                    # --- HARD CAP CHECK ---
                    if step > MAX_STEPS:
                        print(f"\n! Hard cap of {MAX_STEPS} tool calls reached.")
                        result = {
                            "question": question,
                            "answer": (
                                f"I reached the maximum limit of {MAX_STEPS} tool calls "
                                f"without finding a complete answer. "
                                f"Please try rephrasing your question."
                            ),
                            "trace": trace,
                            "steps_used": step,
                            "status": "cap_reached"
                        }
                        save_trace(result)
                        return result

                    result_str = run_tool(tool_name, tool_input)
                    print(f"Result preview: {result_str[:200]}...")

                    # Accumulate results for fallback
                    accumulated_results.append(result_str[:500])

                    trace.append({
                        "step": step,
                        "tool": tool_name,
                        "input": tool_input,
                        "output_preview": result_str[:300]
                    })

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str
                    })

            messages.append({
                "role": "user",
                "content": tool_results
            })

        elif response.stop_reason == "end_turn":
            final_answer = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_answer = block.text
                    break

            print(f"\nFinal Answer: {final_answer}")
            print(f"Steps used: {step} / {MAX_STEPS}")

            result = {
                "question": question,
                "answer": final_answer,
                "trace": trace,
                "steps_used": step,
                "status": "success"
            }
            save_trace(result)
            return result

        else:
            break

    # --- HARD CAP FALLBACK ---
    result = {
        "question": question,
        "answer": (
            f"I was unable to answer this question within "
            f"the {MAX_STEPS} tool call limit."
        ),
        "trace": trace,
        "steps_used": step,
        "status": "cap_reached"
    }
    save_trace(result)
    return result


if __name__ == "__main__":
    test_questions = [
        "What risks did Wipro disclose in their annual report?",
    ]

    for question in test_questions:
        result = run_agent(question)
        print(f"\nStatus: {result['status']}")
        print(f"Steps used: {result['steps_used']}/{MAX_STEPS}")
        print("-" * 60)