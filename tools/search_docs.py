import os
import pdfplumber
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

# --- Setup ---
DOCS_PATH = "data/raw/"
CHROMA_PATH = "data/processed/chroma_db"
COLLECTION_NAME = "annual_reports"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# --- Embedding function (runs locally, no API key needed) ---
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# --- Chroma client ---
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)


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


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
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
    
    # if collection already exists and has data, skip rebuilding
    try:
        collection = chroma_client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_fn
        )
        if collection.count() > 0:
            print(f"Index already exists with {collection.count()} chunks. Skipping rebuild.")
            return collection
    except:
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
        print(f"  Processing: {pdf_file}")

        pages = extract_text_from_pdf(pdf_path)
        print(f"    Extracted {len(pages)} pages with text")

        for page_data in pages:
            chunks = chunk_text(page_data["text"])
            for chunk in chunks:
                collection.add(
                    documents=[chunk],
                    metadatas=[{
                        "source": pdf_file,
                        "page": page_data["page"]
                    }],
                    ids=[f"chunk_{chunk_id}"]
                )
                chunk_id += 1

    print(f"\nDone. Total chunks indexed: {chunk_id}")
    return collection


def search_docs(query: str) -> dict:
    """
    Performs semantic search over annual report PDFs for Infosys, TCS, and Wipro.
    Use this tool when the question asks about qualitative information such as
    management commentary, strategic priorities, reasons behind performance,
    risk factors, or any narrative explanation found in annual reports.
    Do NOT use this for specific numbers or live information.
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
            "error": "Index not built yet. Run build_index() first.",
            "results": []
        }

    try:
        results = collection.query(
            query_texts=[query],
            n_results=3
        )

        output = []
        for i in range(len(results["documents"][0])):
            output.append({
                "chunk": results["documents"][0][i],
                "source": results["metadatas"][0][i]["source"],
                "page": results["metadatas"][0][i]["page"],
                "distance": round(results["distances"][0][i], 4)
            })

        return {
            "query": query,
            "results": output,
            "result_count": len(output)
        }

    except Exception as e:
        return {
            "error": str(e),
            "results": []
        }


if __name__ == "__main__":
    print("=== Building index ===")
    build_index()

    print("\n=== Testing search_docs ===\n")
    tests = [
        "What was Infosys strategy for FY24?",
        "Why did TCS operating margin improve?",
        "What risks did Wipro highlight in their annual report?",
        "What did management say about AI and digital transformation?",
        "Employee training and talent development"
    ]

    for q in tests:
        print(f"Query: {q}")
        result = search_docs(q)
        if "error" in result:
            print(f"  Error: {result['error']}")
        else:
            for r in result["results"]:
                print(f"  Source: {r['source']} | Page: {r['page']} | Distance: {r['distance']}")
                print(f"  Chunk: {r['chunk'][:150]}...")
            print()