import os
import json
import anthropic
from dotenv import load_dotenv

from tools.search_docs import search_docs
from tools.query_data import query_data
from tools.web_search import web_search

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MAX_STEPS = 8

# --- Tool definitions (Claude reads these to decide which tool to call) ---
TOOLS = [
    {
        "name": "search_docs",
        "description": (
            "Performs semantic search over annual report PDFs for Infosys, TCS, and Wipro. "
            "Use this tool when the question asks about qualitative information such as "
            "management commentary, strategic priorities, reasons behind performance, "
            "risk factors, or any narrative explanation found in annual reports. "
            "Do NOT use this for specific numbers, live prices, or recent news."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query"
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
- If you cannot find the answer after using tools, say so honestly
"""


def run_tool(tool_name: str, tool_input: dict) -> str:
    """Run the appropriate tool and return result as a string."""
    if tool_name == "search_docs":
        result = search_docs(tool_input["query"])
    elif tool_name == "query_data":
        result = query_data(tool_input["question"])
    elif tool_name == "web_search":
        result = web_search(tool_input["query"])
    else:
        result = {"error": f"Unknown tool: {tool_name}"}
    
    return json.dumps(result)


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

    while step < MAX_STEPS:
        # --- Call Claude ---
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        # --- Check if Claude wants to use a tool ---
        if response.stop_reason == "tool_use":
            # Add Claude's response to message history
            messages.append({
                "role": "assistant",
                "content": response.content
            })

            # Process each tool call Claude requested
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    step += 1
                    tool_name = block.name
                    tool_input = block.input

                    print(f"\nStep {step}: tool={tool_name} input={tool_input}")

                    # Run the tool
                    result = run_tool(tool_name, tool_input)

                    print(f"Result preview: {result[:200]}...")

                    # Log to trace
                    trace.append({
                        "step": step,
                        "tool": tool_name,
                        "input": tool_input,
                        "output_preview": result[:300]
                    })

                    # Check hard cap
                    if step >= MAX_STEPS:
                        print(f"\n⚠️  Hard cap of {MAX_STEPS} tool calls reached.")
                        return {
                            "question": question,
                            "answer": f"I was unable to fully answer this question within the {MAX_STEPS} tool call limit. Partial trace is available.",
                            "trace": trace,
                            "steps_used": step,
                            "status": "cap_reached"
                        }

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            # Feed tool results back to Claude
            messages.append({
                "role": "user",
                "content": tool_results
            })

        # --- Claude is done, return final answer ---
        elif response.stop_reason == "end_turn":
            final_answer = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_answer = block.text
                    break

            print(f"\nFinal Answer: {final_answer}")
            print(f"Steps used: {step} / {MAX_STEPS}")

            return {
                "question": question,
                "answer": final_answer,
                "trace": trace,
                "steps_used": step,
                "status": "success"
            }

        else:
            break

    return {
        "question": question,
        "answer": "Agent terminated unexpectedly.",
        "trace": trace,
        "steps_used": step,
        "status": "error"
    }


if __name__ == "__main__":
    test_questions = [
    "How did Infosys and TCS operating margins compare in FY2024, and what reason did each company give for their margin performance?",
    "What was Wipro's revenue growth over FY2021 to FY2024, and what strategic priorities did Wipro highlight to drive future growth?",
    ]

    for question in test_questions:
        result = run_agent(question)
        print(f"\nStatus: {result['status']}")
        print(f"Steps used: {result['steps_used']}/{MAX_STEPS}")
        print("-" * 60)