import os
import pickle
import openai
import boto3
import numpy as np
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity

from chunking.chunks import heading_based_split, semantic_split, recursive_split

# Load credentials from .env
load_dotenv()
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize S3 client
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

# ========== EMBEDDING ==========
def generate_embeddings(texts):
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    return [item.embedding for item in response.data]

# ========== VECTOR CREATION ==========
def create_manual_vector_index(markdown, year, quarter, parser, strategy):
    # Choose chunking strategy
    if strategy == "heading":
        chunks = heading_based_split(markdown)
    elif strategy == "semantic":
        chunks = semantic_split(markdown)
    elif strategy == "recursive":
        chunks = recursive_split(markdown)
    else:
        raise ValueError("Unsupported chunking strategy.")

    print(f"🧩 Total chunks generated: {len(chunks)}")
    vectors = generate_embeddings(chunks)

    data = []
    for idx, vector in enumerate(vectors):
        data.append({
            "id": f"{year}_{quarter}_{parser}_{strategy}_chunk_{idx}",
            "embedding": vector,
            "meta": {
                "year": year,
                "quarter": quarter,
                "parser": parser,
                "strategy": strategy,
                "content": chunks[idx]
            }
        })

    upload_pickle_to_s3(data, year, quarter)
    return data

# ========== S3 UPLOAD ==========
def upload_pickle_to_s3(data, year, quarter):
    pickle_path = f"manual_embedding/{year}/Q{quarter[-1]}/manual_vectors.pkl"
    serialized = pickle.dumps(data)

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=pickle_path,
        Body=serialized
    )
    print(f"✅ Uploaded manual vectors to S3: s3://{BUCKET_NAME}/{pickle_path}")

# ========== S3 DOWNLOAD ==========
def download_pickle_from_s3(year, quarter):
    pickle_path = f"manual_embedding/{year}/Q{quarter[-1]}/manual_vectors.pkl"

    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=pickle_path)
        content = response['Body'].read()
        return pickle.loads(content)
    except s3.exceptions.NoSuchKey:
        raise FileNotFoundError("❌ No vector file found for given year/quarter.")
    except Exception as e:
        raise RuntimeError(f"Failed to load vectors from S3: {str(e)}")

# ========== COSINE SIMILARITY SEARCH ==========
def search_manual_vectors(query, parser, strategy, year, quarter, top_k=5):
    query_vector = generate_embeddings([query])[0]
    all_data = download_pickle_from_s3(year, quarter)

    # Filter vectors by metadata
    filtered = [
        entry for entry in all_data
        if entry['meta']['parser'] == parser and
           entry['meta']['strategy'] == strategy and
           entry['meta']['year'] == year and
           entry['meta']['quarter'] == quarter
    ]

    if not filtered:
        print("⚠️ No matching vectors found.")
        return []

    # Compute cosine similarities
    stored_vectors = [entry["embedding"] for entry in filtered]
    scores = cosine_similarity([query_vector], stored_vectors)[0]

    # Rank and return top chunks
    top_indices = np.argsort(scores)[-top_k:][::-1]
    return [filtered[i]["meta"]["content"] for i in top_indices]

# ========== SUMMARY FROM CHUNKS ==========
def summarize_manual_chunks(parser, strategy, year, quarter, top_k=30):
    all_data = download_pickle_from_s3(year, quarter)
    filtered = [
        entry for entry in all_data
        if entry['meta']['parser'] == parser and
           entry['meta']['strategy'] == strategy and
           entry['meta']['year'] == year and
           entry['meta']['quarter'] == quarter
    ]

    if not filtered:
        print("⚠️ No matching data found for summary generation.")
        return []

    chunks = [entry['meta']['content'] for entry in filtered[:top_k]]
    return chunks
