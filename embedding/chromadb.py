# embedding/chromadb.py

import os
from dotenv import load_dotenv
import chromadb
from chromadb import PersistentClient
import chromadb.utils.embedding_functions as embedding_functions

from chunking.chunks import heading_based_split, semantic_split, recursive_split
from embedding.pinecone import load_markdown  # Reuse markdown loader from Pinecone

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize persistent ChromaDB client
chroma_client = PersistentClient(path="chromadb_store")

# Initialize OpenAI embedding function (Chroma-native wrapper)
openai_embedder = embedding_functions.OpenAIEmbeddingFunction(
    api_key=OPENAI_API_KEY,
    model_name="text-embedding-3-small"
)
#Save to chromadb
def save_chunks_to_chromadb(parser, strategy, year, quarter, chunks):
    collection_name = f"{parser}_{strategy}".lower()
    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        embedding_function=openai_embedder
    )

    print(f"📦 Preparing to upload {len(chunks)} chunks...")

    # Trim long chunks to avoid OpenAI token limit
    MAX_CHARS = 30000
    trimmed_chunks = [chunk[:MAX_CHARS] for chunk in chunks]

    documents = trimmed_chunks
    ids = [f"{year}_{quarter}_{parser}_{strategy}_{i}" for i in range(len(documents))]
    metadatas = [{
        "year": year,
        "quarter": quarter,
        "parser": parser,
        "strategy": strategy,
        "period": f"{year}_Q{quarter[-1]}"
    } for _ in documents]

    collection.add(documents=documents, metadatas=metadatas, ids=ids)

    print(f"✅ Uploaded {len(documents)} chunks to ChromaDB in collection: {collection_name}")
    return {"status": "success", "chunks_uploaded": len(documents)}


# === Convert Markdown → Chunks → Upload to ChromaDB ===
def process_and_upload_to_chromadb(year, quarter, parser, strategy):
    print(f"📥 Loading markdown from S3 for: {parser.upper()} - {year} {quarter}")
    markdown = load_markdown(year, quarter, parser)
    
    if not markdown:
        raise ValueError("❌ Markdown file could not be loaded from S3.")

    print(f"✂️ Chunking strategy: {strategy}")
    if strategy == "heading":
        chunks = heading_based_split(markdown)
    elif strategy == "semantic":
        chunks = semantic_split(markdown)
    elif strategy == "recursive":
        chunks = recursive_split(markdown)
    else:
        raise ValueError("❌ Invalid chunking strategy.")
    
    print(f"📦 Total chunks generated: {len(chunks)}")
    return save_chunks_to_chromadb(parser, strategy, year, quarter, chunks)


# === Query ChromaDB Collection ===
def search_chunks(parser, strategy, query, year, quarters, top_k=30):
    if len(quarters) != 1:
        raise ValueError("ChromaDB only supports filtering by a single quarter (period).")

    collection_name = f"{parser}_{strategy}".lower()

    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        embedding_function=openai_embedder
    )

    period_key = f"{year}_Q{quarters[0][-1]}"

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where={"period": period_key},
        include=["documents", "metadatas"]
    )

    documents = results.get("documents", [[]])[0]
    return documents
