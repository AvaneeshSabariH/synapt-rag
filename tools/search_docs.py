import os
import re
import pdfplumber
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

DOCS_PATH = "data/raw/"
CHROMA_PATH = "data/processed/chroma_db"
COLLECTION_NAME = "annual_reports_v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)


def extract_fiscal_year(filename: str) -> str:
    """
    Extract fiscal year from PDF filename.
    Examples:
      infosys-ar-25.pdf        -> FY2025
      tcs-annual-report-2023-2024.pdf  -> FY2024
      wipro-integrated-annual-report-2022-23.pdf -> FY2023
    """
    # Match patterns like 2024-2025 or 2024-25
    match = re.search(r'20(\d{2})[-_](?:20)?(\d{2})', filename)
    if match:
        end_year = match.group(2)
        if len(end_year) == 2:
            return f"FY20{end_year}"
        return f"FY{end_year}"

    # Match patterns like -ar-25 or -ar-22
    match = re.search(r'-ar-(\d{2})', filename)
    if match:
        return f"FY20{match.group(1)}"

    return "FY_UNKNOWN"


def extract_company(filename: str) -> str:
    """Extract company name from PDF filename."""
    filename_lower = filename.lower()
    if "infosys" in filename_lower:
        return "Infosys"
    elif "tcs" in filename_lower:
        return "TCS"
    elif "wipro" in filename_lower:
        return "Wipro"
    return "Unknown"


def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """Extract text page by page from a PDF."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text and len(text.strip()) > 50:
                pages.append({
                    "text": text.strip(),
                    "page": page_num
                })
    return pages


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by word count."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def build_index():
    """Extract, chunk, embed and store all PDFs into Chroma."""
    try:
        collection = chroma_client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_fn
        )
        if collection.count() > 0:
            print(f"Index already exists with {collection.count()} chunks.")
            return collection
    except Exception:
        pass

    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn
    )

    pdf_files = [f for f in os.listdir(DOCS_PATH) if f.endswith(".pdf")]
    print(f"Found {len(pdf_files)} PDFs to index...")

    chunk_id = 0
    for pdf_file in pdf_files:
        pdf_path = os.path.join(DOCS_PATH, pdf_file)

        # Extract metadata from filename
        fiscal_year = extract_fiscal_year(pdf_file)
        company = extract_company(pdf_file)

        print(f"  Processing: {pdf_file} → {company} {fiscal_year}")

        pages = extract_text_from_pdf(pdf_path)
        print(f"    Extracted {len(pages)} pages")

        for page_data in pages:
            chunks = chunk_text(page_data["text"])
            for chunk in chunks:
                collection.add(
                    documents=[chunk],
                    metadatas=[{
                        "source": pdf_file,
                        "page": page_data["page"],
                        "company": company,
                        "fiscal_year": fiscal_year
                    }],
                    ids=[f"chunk_{chunk_id}"]
                )
                chunk_id += 1

    print(f"\nDone. Total chunks indexed: {chunk_id}")
    return collection


def search_docs(query: str, company: str = None,
                fiscal_year: str = None) -> dict:
    """
    Performs semantic search over annual report PDFs for Infosys,
    TCS, and Wipro. Use this tool when the question asks about
    qualitative information such as management commentary, strategic
    priorities, reasons behind performance, risk factors, or any
    narrative explanation found in annual reports.
    Do NOT use this for specific numbers, live prices, or recent news.

    Optional filters:
    - company: "Infosys", "TCS", or "Wipro"
    - fiscal_year: "FY2021", "FY2022", "FY2023", or "FY2024"
    """

    if not query or len(query.strip()) == 0:
        return {"error": "Query cannot be empty", "results": []}

    try:
        collection = chroma_client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_fn
        )
    except Exception:
        return {
            "error": "Index not built. Run build_index() first.",
            "results": []
        }

    try:
        # Build metadata filter if company or year specified
        where_filter = None
        if company and fiscal_year:
            where_filter = {
                "$and": [
                    {"company": {"$eq": company}},
                    {"fiscal_year": {"$eq": fiscal_year}}
                ]
            }
        elif company:
            where_filter = {"company": {"$eq": company}}
        elif fiscal_year:
            where_filter = {"fiscal_year": {"$eq": fiscal_year}}

        results = collection.query(
            query_texts=[query],
            n_results=3,
            where=where_filter if where_filter else None
        )

        output = []
        for i in range(len(results["documents"][0])):
            output.append({
                "chunk": results["documents"][0][i],
                "source": results["metadatas"][0][i]["source"],
                "page": results["metadatas"][0][i]["page"],
                "company": results["metadatas"][0][i]["company"],
                "fiscal_year": results["metadatas"][0][i]["fiscal_year"],
                "distance": round(results["distances"][0][i], 4)
            })

        return {
            "query": query,
            "filters": {
                "company": company,
                "fiscal_year": fiscal_year
            },
            "results": output,
            "result_count": len(output)
        }

    except Exception as e:
        return {"error": str(e), "results": []}


if __name__ == "__main__":
    print("=== Building index ===")
    build_index()

    print("\n=== Testing with filters ===\n")

    # Test with year filter
    print("Query: Infosys margin explanation — filtered to FY2025")
    result = search_docs(
        "operating margin performance reasons",
        company="Infosys",
        fiscal_year="FY2025"
    )
    for r in result["results"]:
        print(f"  {r['company']} {r['fiscal_year']} | "
              f"Page {r['page']} | Distance {r['distance']}")
        print(f"  {r['chunk'][:150]}...")
    print()

    # Test without filter
    print("Query: TCS margin explanation — no filter")
    result = search_docs("TCS operating margin improvement reasons")
    for r in result["results"]:
        print(f"  {r['company']} {r['fiscal_year']} | "
              f"Page {r['page']} | Distance {r['distance']}")
        print(f"  {r['chunk'][:150]}...")