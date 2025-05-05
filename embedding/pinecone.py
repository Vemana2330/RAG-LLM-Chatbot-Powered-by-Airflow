import os
import openai
import boto3
from dotenv import load_dotenv
from pinecone import Pinecone
from chunking.chunks import heading_based_split, semantic_split, recursive_split

# Load environment variables
load_dotenv()

# API Keys and Config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX")
AWS_BUCKET = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")

# Set OpenAI API Key
openai.api_key = OPENAI_API_KEY

# Initialize S3 Client
s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

# Step 1: Connect to Existing Pinecone Index
def connect_pinecone_index():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    try:
        return pc.Index(PINECONE_INDEX_NAME)
    except Exception as e:
        print(f"❌ Could not connect to Pinecone index '{PINECONE_INDEX_NAME}': {e}")
        raise

# Step 2: Get .md content from S3
def load_markdown(year: str, quarter: str, parser: str) -> str:
    key = f"{parser}_markdown/{year}/{quarter}/{quarter}.md"
    try:
        response = s3_client.get_object(Bucket=AWS_BUCKET, Key=key)
        return response["Body"].read().decode("utf-8")
    except Exception as e:
        print(f"❌ Could not load {key} from S3: {e}")
        return None

# Step 3: Embed text using OpenAI
def get_openai_embedding(text: str) -> list:
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

# Step 4: Upload to Pinecone
def upload_to_pinecone(parser, strategy, year, quarter, chunks):
    index = connect_pinecone_index()
    namespace = f"{parser}_{strategy}"
    batch = []

    for i, chunk in enumerate(chunks):
        vector_id = f"{year}_{quarter}_{parser}_{strategy}_{i}"
        embedding = get_openai_embedding(chunk)
        metadata = {"year": year, "quarter": quarter, "text": chunk}
        batch.append((vector_id, embedding, metadata))

        if len(batch) >= 20:
            index.upsert(vectors=batch, namespace=namespace)
            print(f"🔼 Uploaded {len(batch)} chunks.")
            batch.clear()

    if batch:
        index.upsert(vectors=batch, namespace=namespace)
        print(f"🔼 Uploaded final {len(batch)} chunks.")

# Step 5: Query Pinecone
def search_chunks(parser, strategy, query, year, quarters, top_k=5):
    index = connect_pinecone_index()
    embedded_query = get_openai_embedding(query)
    results = index.query(
        namespace=f"{parser}_{strategy}",
        vector=embedded_query,
        top_k=top_k,
        include_metadata=True,
        filter={"year": {"$eq": year}, "quarter": {"$in": quarters}},
    )
    return [match["metadata"]["text"] for match in results["matches"]]


def process_and_upload_to_pinecone(year, quarter, parser, strategy):
    print(f"📥 Loading markdown for: {year}/{quarter} | Parser: {parser}, Strategy: {strategy}")

    # Step 1: Load Markdown
    markdown = load_markdown(year, quarter, parser)
    if not markdown:
        raise ValueError("❌ Markdown file could not be loaded from S3.")

    # Step 2: Chunk Markdown
    try:
        if strategy == "heading":
            chunks = heading_based_split(markdown)
        elif strategy == "semantic":
            chunks = semantic_split(markdown)
        elif strategy == "recursive":
            chunks = recursive_split(markdown)
        else:
            raise ValueError("❌ Invalid chunking strategy.")
    except Exception as e:
        print("❌ Error while chunking:", e)
        raise ValueError(f"Error during chunking: {e}")

    print(f"✅ Total chunks created: {len(chunks)}")

    
    max_chars = 15000
    chunks = [chunk[:max_chars] for chunk in chunks]

    # Step 3: Upload to Pinecone
    try:
        print("🚀 Uploading chunks to Pinecone...")
        upload_to_pinecone(parser, strategy, year, quarter, chunks)
        print("✅ Upload to Pinecone successful.")
    except Exception as e:
        print("❌ Pinecone upload failed:")
        import traceback
        traceback.print_exc()
        raise ValueError(f"Pinecone upload error: {e}")

    return {"status": "success", "chunks_uploaded": len(chunks)}




if __name__ == "__main__":
    pass