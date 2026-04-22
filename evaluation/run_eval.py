import sys
import os
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.loop import run_agent

QUESTIONS = [
    # Single tool - query_data
    ("single_tool", "What was Infosys revenue in FY2023?"),
    ("single_tool", "What was TCS headcount in FY2024?"),
    ("single_tool", "Which company had the highest operating margin in FY2022?"),
    ("single_tool", "What was Wipro EPS in FY2021?"),
    ("single_tool", "Show me net profit for all three companies in FY2024."),
    ("single_tool", "How did TCS revenue grow from FY2021 to FY2024?"),

    # Single tool - search/web
    ("single_tool", "What strategic priorities did Infosys highlight in their annual report?"),
    ("single_tool", "What risks did Wipro disclose in their annual report?"),
    ("single_tool", "What is the current stock price of TCS?"),
    ("single_tool", "Who is the current CEO of Infosys?"),

    # Multi tool
    ("multi_tool", "How did Infosys and TCS operating margins compare in FY2024 and what reason did each give?"),
    ("multi_tool", "What was Wipro revenue growth from FY2021 to FY2024 and what strategy did they highlight?"),
    ("multi_tool", "Compare headcount at all 3 companies in FY2024 and what did each say about talent?"),
    ("multi_tool", "What was TCS net profit in FY2023 and what drove their profitability that year?"),
    ("multi_tool", "How did Infosys EPS grow over 4 years and what growth strategy did they pursue?"),
    ("multi_tool", "Which company had the lowest margin in FY2024 and what challenges did they mention?"),

    # Refusals
    ("refusal", "Which company should I invest in?"),
    ("refusal", "What is the airspeed velocity of an unladen swallow?"),
    ("refusal", "Can you predict Wipro stock price next year?"),
    ("refusal", "Write me a poem about TCS."),

    # Edge cases
    ("edge_case", "What was Infosys revenue in FY2010?"),
    ("edge_case", "How did Tesla perform in FY2024?"),
    ("edge_case", "What was TCS operating margin in FY2024?"),
    ("edge_case", "Compare all financial metrics for all companies across all years."),
]

def run_evaluation():
    results = []
    passed = 0
    failed = 0

    print(f"Running evaluation set — {len(QUESTIONS)} questions\n")
    print("=" * 60)

    for i, (category, question) in enumerate(QUESTIONS, 1):
        print(f"\n[{i}/{len(QUESTIONS)}] Category: {category}")
        
        result = run_agent(question)
        
        entry = {
            "id": i,
            "category": category,
            "question": question,
            "answer": result["answer"],
            "steps_used": result["steps_used"],
            "status": result["status"],
            "tools_called": [t["tool"] for t in result["trace"]]
        }
        
        results.append(entry)
        print(f"Tools called: {entry['tools_called']}")
        print(f"Steps: {entry['steps_used']}/{8}")

    # --- Save results ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"evaluation/eval_results_{timestamp}.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"Evaluation complete. Results saved to: {output_path}")
    print(f"Total questions: {len(results)}")

    # --- Summary by category ---
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)

    print(f"\nSummary by category:")
    for cat, items in categories.items():
        print(f"  {cat}: {len(items)} questions")

if __name__ == "__main__":
    run_evaluation()