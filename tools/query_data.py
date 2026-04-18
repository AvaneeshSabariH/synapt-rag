import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = "data/processed/financials.csv"

df = pd.read_csv(DATA_PATH)

def query_data(question: str) -> dict:
    """
    Queries the structured financial data table containing revenue, operating margin,
    net profit, EPS, and headcount for Infosys, TCS, and Wipro from FY2021 to FY2024.
    Use this tool when the question asks for specific numbers, comparisons, trends,
    or calculations from the financial data. Do NOT use this for qualitative questions
    about strategy, management commentary, or recent news.
    """

    if not question or len(question.strip()) == 0:
        return {"error": "Question cannot be empty", "data": None}

    question_lower = question.lower()

    try:
        # --- Company filter ---
        companies = []
        if "infosys" in question_lower:
            companies.append("Infosys")
        if "tcs" in question_lower:
            companies.append("TCS")
        if "wipro" in question_lower:
            companies.append("Wipro")

        # --- Year filter ---
        years = []
        for year in ["FY2021", "FY2022", "FY2023", "FY2024"]:
            if year.lower() in question_lower or year[-2:] in question_lower:
                years.append(year)

        # --- Apply filters ---
        filtered = df.copy()
        if companies:
            filtered = filtered[filtered["company"].isin(companies)]
        if years:
            filtered = filtered[filtered["fiscal_year"].isin(years)]

        # --- Column selection ---
        columns = ["company", "fiscal_year"]

        if any(word in question_lower for word in ["revenue", "sales", "turnover"]):
            columns.append("revenue_cr")
        if any(word in question_lower for word in ["operating margin", "margin"]):
            columns.append("operating_margin_pct")
        if any(word in question_lower for word in ["net profit", "profit", "earnings"]):
            columns.append("net_profit_cr")
        if any(word in question_lower for word in ["eps", "earnings per share"]):
            columns.append("eps")
        if any(word in question_lower for word in ["headcount", "employees", "staff", "people"]):
            columns.append("headcount")

        # if no specific column matched, return all
        if columns == ["company", "fiscal_year"]:
            columns = list(df.columns)

        filtered = filtered[columns]

        if filtered.empty:
            return {
                "question": question,
                "data": None,
                "row_count": 0,
                "message": "No data found matching your query."
            }

        return {
            "question": question,
            "columns": list(filtered.columns),
            "data": filtered.to_dict(orient="records"),
            "row_count": len(filtered)
        }

    except Exception as e:
        return {
            "error": str(e),
            "data": None
        }


if __name__ == "__main__":
    tests = [
        "What was Infosys revenue in FY2023?",
        "Compare operating margin for all companies in FY2024",
        "What was TCS headcount over all years?",
        "Show me Wipro net profit in FY2022",
    ]

    for q in tests:
        print(f"Question: {q}")
        result = query_data(q)
        if "error" in result:
            print(f"  Error: {result['error']}")
        else:
            print(f"  Rows returned: {result['row_count']}")
            for row in result["data"]:
                print(f"  {row}")
        print()