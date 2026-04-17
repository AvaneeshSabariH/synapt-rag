import os
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def web_search(query: str) -> dict:
    """
    Searches the live web for recent information.
    Use this tool when the question asks about current events, recent news,
    live stock prices, or anything that would not be found in a static document.
    Do NOT use this for questions about historical financials or document content.
    """
    
    if not query or len(query.strip()) == 0:
        return {"error": "Query cannot be empty", "results": []}
    
    if len(query.split()) > 10:
        query = " ".join(query.split()[:10])
    
    try:
        response = client.search(
            query=query,
            max_results=3,
            include_published_date=True
        )
        
        results = []
        for item in response.get("results", []):
            results.append({
                "title":   item.get("title", "No title"),
                "snippet": item.get("content", "No content"),
                "url":     item.get("url", "No URL"),
                "date":    item.get("published_date", "Date unknown")
            })
        
        return {
            "query": query,
            "results": results,
            "result_count": len(results)
        }
    
    except Exception as e:
        return {
            "error": str(e),
            "results": []
        }


if __name__ == "__main__":
    test_query = "Infosys stock price today"
    print(f"Testing web_search with query: '{test_query}'\n")
    
    output = web_search(test_query)
    
    if "error" in output:
        print(f"Error: {output['error']}")
    else:
        print(f"Found {output['result_count']} results:\n")
        for i, result in enumerate(output["results"], 1):
            print(f"Result {i}:")
            print(f"  Title:   {result['title']}")
            print(f"  Snippet: {result['snippet'][:150]}...")
            print(f"  URL:     {result['url']}")
            print(f"  Date:    {result['date']}")
            print()