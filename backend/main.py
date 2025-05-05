from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import boto3
import os
import sys
from dotenv import load_dotenv
import json
import openai
# Add root path to Python path to allow relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import traceback
# Import processing functions
from pdf_processing.mistral import mistral_pdf_to_md
#from pdf_processing.docling_extract import convert_pdf_to_markdown
from chunking.chunks import heading_based_split, semantic_split, recursive_split
from embedding.pinecone import process_and_upload_to_pinecone
from embedding.chromadb import process_and_upload_to_chromadb
from embedding.pinecone import search_chunks
from openai import OpenAI
from fastapi import Request
from embedding.chromadb import search_chunks as search_chroma_chunks
from embedding.manual import search_manual_vectors
import requests
import asyncio
import logging
# Load .env variables
load_dotenv()

# AWS Credentials
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_BUCKET = os.getenv("AWS_BUCKET_NAME")

# FastAPI app setup
app = FastAPI()

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

# ----------------------- ROUTES -----------------------

@app.get("/get_available_years")
def get_available_years():
    response = s3_client.list_objects_v2(Bucket=AWS_BUCKET, Prefix="Raw_PDFs/", Delimiter="/")
    years = [prefix["Prefix"].split("/")[-2] for prefix in response.get("CommonPrefixes", [])]
    return {"years": sorted(years, reverse=True)}

@app.get("/get_available_quarters/{year}")
def get_available_quarters(year: str):
    prefix = f"Raw_PDFs/{year}/"
    response = s3_client.list_objects_v2(Bucket=AWS_BUCKET, Prefix=prefix)
    quarters = [obj["Key"].split("/")[-1].replace(".pdf", "") for obj in response.get("Contents", []) if obj["Key"].endswith(".pdf")]
    return {"quarters": sorted(quarters)}

@app.get("/get_pdf_url/{year}/{quarter}")
def get_pdf_url(year: str, quarter: str):
    s3_key = f"Raw_PDFs/{year}/{quarter}.pdf"
    url = s3_client.generate_presigned_url("get_object", Params={"Bucket": AWS_BUCKET, "Key": s3_key}, ExpiresIn=3600)
    return {"pdf_url": url}

@app.post("/process_pdf_mistral/{year}/{quarter}")
def process_pdf_with_mistral(year: str, quarter: str):
    s3_key = f"Raw_PDFs/{year}/{quarter}.pdf"
    try:
        response = s3_client.get_object(Bucket=AWS_BUCKET, Key=s3_key)
        pdf_bytes = response["Body"].read()
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"PDF not found in S3: {e}")

    result = mistral_pdf_to_md(pdf_bytes, year, quarter)
    return result


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


from fastapi import HTTPException
import requests
import os
import tempfile
import traceback
import logging

logger = logging.getLogger(__name__)

@app.post("/process_pdf_docling/{year}/{quarter}")
def process_pdf_docling(year: str, quarter: str):
    s3_key = f"Raw_PDFs/{year}/{quarter}.pdf"

    try:
        # Step 1: Download PDF from S3
        logger.info(f"📥 Attempting to download PDF from S3: {s3_key}")
        response = s3_client.get_object(Bucket=AWS_BUCKET, Key=s3_key)
        logger.info("✅ Successfully fetched PDF stream from S3")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(response["Body"].read())
            tmp_file_path = tmp_file.name

        file_size = os.path.getsize(tmp_file_path) / 1e6
        logger.info(f"✅ Saved PDF to temp file: {tmp_file_path} ({file_size:.2f} MB)")

    except Exception as e:
        logger.error(f"❌ Failed to fetch PDF from S3: {e}")
        raise HTTPException(status_code=404, detail=f"❌ PDF not found in S3: {e}")

    try:
        # Step 2: Forward to docling_service running on port 8001
        docling_url = f"http://docling_service:8001/convert_docling/{year}/{quarter}"
        logger.info(f"📤 Sending PDF to Docling service at {docling_url}")

        with open(tmp_file_path, "rb") as f:
            files = {"file": (f"{quarter}.pdf", f, "application/pdf")}
            docling_response = requests.post(docling_url, files=files)

        docling_response.raise_for_status()
        logger.info(f"✅ Received successful response from Docling service.")

        return {
            "message": f"✅ Docling conversion successful for {year} {quarter}",
            **docling_response.json()
        }

    except Exception as e:
        logger.error("❌ Exception occurred while sending to Docling:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"❌ Docling service failed: {str(e)}")

    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
                logger.info(f"🧹 Cleaned up temp file: {tmp_file_path}")
        except Exception as cleanup_error:
            logger.warning(f"⚠️ Failed to delete temp file: {tmp_file_path}. Error: {cleanup_error}")


@app.post("/chunk_markdown")
def chunk_markdown(payload: dict):
    year = payload.get("year")
    quarter = payload.get("quarter")
    parser = payload.get("parser", "docling").lower()
    strategy = payload.get("strategy", "heading").lower()

    if not all([year, quarter, strategy]):
        raise HTTPException(status_code=400, detail="Missing one or more required parameters.")

    md_key = f"{parser}_markdown/{year}/{quarter}/{quarter}.md"

    try:
        obj = s3_client.get_object(Bucket=AWS_BUCKET, Key=md_key)
        md_content = obj["Body"].read().decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Markdown file not found in S3: {e}")

    # Apply selected chunking strategy
    if strategy == "heading":
        chunks = heading_based_split(md_content)
    elif strategy == "semantic":
        chunks = semantic_split(md_content)
    elif strategy == "recursive":
        chunks = recursive_split(md_content)
    else:
        raise HTTPException(status_code=400, detail="Invalid chunking strategy.")

    return {"chunks": chunks}

@app.post("/upload_to_pinecone")
def trigger_pinecone(payload: dict):
    year = payload.get("year")
    quarter = payload.get("quarter")
    parser = payload.get("parser", "mistral").lower()
    strategy = payload.get("strategy", "recursive").lower()

    if not all([year, quarter, parser, strategy]):
        raise HTTPException(status_code=400, detail="Missing required parameters.")

    try:
        print(f"🚀 Uploading to Pinecone — {year} {quarter} | {parser} | {strategy}")
        result = process_and_upload_to_pinecone(year, quarter, parser, strategy)
        print(f"✅ Upload completed: {result}")
        return result
    except Exception as e:
        import traceback
        print("❌ Error uploading to Pinecone:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    


@app.post("/upload_to_chromadb")
def trigger_chromadb(payload: dict):
    from embedding.chromadb import process_and_upload_to_chromadb

    year = payload.get("year")
    quarter = payload.get("quarter")
    parser = payload.get("parser", "mistral").lower()
    strategy = payload.get("strategy", "recursive").lower()

    if not all([year, quarter, parser, strategy]):
        raise HTTPException(status_code=400, detail="Missing required parameters.")

    try:
        print(f"🚀 Uploading to ChromaDB: {year} {quarter}, {parser}, {strategy}")
        result = process_and_upload_to_chromadb(year, quarter, parser, strategy)
        return result
    except Exception as e:
        import traceback
        print("❌ ChromaDB upload error:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))






client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


client = OpenAI()

@app.post("/query_pinecone")
def query_pinecone(payload: dict):
    query = payload.get("query")
    year = payload.get("year")
    quarter = payload.get("quarter")
    parser = payload.get("parser")
    strategy = payload.get("strategy")

    if not all([query, year, quarter, parser, strategy]):
        raise HTTPException(status_code=400, detail="Missing query parameters")

    try:
        print(f"📥 Query Received: {query}")
        print(f"📌 Filters — Year: {year}, Quarter: {quarter}, Parser: {parser}, Strategy: {strategy}")
        chunks = search_chunks(parser, strategy, query, year, [quarter])
        print(f"✅ Retrieved {len(chunks)} chunks from Pinecone")

        if not chunks:
            raise ValueError("No relevant chunks retrieved. Check your vector store.")

        context = "\n\n".join(chunks)

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert in financial document analysis."},
                {"role": "user", "content": f"Given this context:\n{context}\n\nAnswer this question:\n{query}"}
            ]
        )

        answer = completion.choices[0].message.content
        return {"answer": answer, "sources": chunks}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate_summary_pinecone")
def generate_summary_pinecone(payload: dict):
    year = payload.get("year")
    quarter = payload.get("quarter")
    parser = payload.get("parser")
    strategy = payload.get("strategy")

    if not all([year, quarter, parser, strategy]):
        raise HTTPException(status_code=400, detail="Missing summary parameters")

    try:
        print(f"📝 Generating Summary — {year} {quarter} | {parser} | {strategy}")
        chunks = search_chunks(parser, strategy, "summary", year, [quarter])
        if not chunks:
            raise ValueError("No chunks found for summary generation.")

        context = "\n\n".join(chunks)

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional financial analyst. Summarize the document."},
                {"role": "user", "content": f"Based on this document, give me a detailed executive summary:\n{context}"}
            ]
        )

        summary = completion.choices[0].message.content
        return {"summary": summary}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))







@app.post("/query_chromadb")
def query_chromadb(payload: dict):
    query = payload.get("query")
    year = payload.get("year")
    quarter = payload.get("quarter")
    parser = payload.get("parser")
    strategy = payload.get("strategy")

    if not all([query, year, quarter, parser, strategy]):
        raise HTTPException(status_code=400, detail="Missing query parameters")

    try:
        print(f"📥 [ChromaDB] Query: {query}")
        from embedding.chromadb import search_chunks as search_chroma_chunks
        chunks = search_chroma_chunks(parser, strategy, query, year, [quarter], top_k=30)

        context = "\n\n".join(chunks)
        max_chars = 15000
        if len(context) > max_chars:
            print(f"⚠️ Context too long ({len(context)} chars), trimming...")
            context = context[:max_chars]

        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial analyst answering questions based on extracted financial reports. Use only the given context."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{query}"}
            ]
        )
        answer = completion.choices[0].message.content
        return {"answer": answer, "sources": chunks}

    except Exception as e:
        print("❌ Error in /query_chromadb:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate_summary_chromadb")
def summarize_chromadb(payload: dict):
    year = payload.get("year")
    quarter = payload.get("quarter")
    parser = payload.get("parser")
    strategy = payload.get("strategy")

    if not all([year, quarter, parser, strategy]):
        raise HTTPException(status_code=400, detail="Missing parameters")

    try:
        from embedding.chromadb import search_chunks as search_chroma_chunks
        chunks = search_chroma_chunks(parser, strategy, "summary", year, [quarter], top_k=30)

        context = "\n\n".join(chunks)
        max_chars = 15000
        if len(context) > max_chars:
            print(f"⚠️ Summary context too long ({len(context)} chars), trimming...")
            context = context[:max_chars]

        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial analyst. Summarize the key points of this financial report accurately and concisely."},
                {"role": "user", "content": f"Please summarize the following report content:\n{context}"}
            ]
        )
        summary = completion.choices[0].message.content
        return {"summary": summary, "source_chunks": chunks}

    except Exception as e:
        print("❌ Error in /generate_summary_chromadb:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

#Manual embedding
@app.post("/upload_to_manual")
def upload_to_manual(payload: dict):
    from embedding.manual import create_manual_vector_index
    from embedding.pinecone import load_markdown  # reusing your loader

    year = payload.get("year")
    quarter = payload.get("quarter")
    parser = payload.get("parser")
    strategy = payload.get("strategy")

    if not all([year, quarter, parser, strategy]):
        raise HTTPException(status_code=400, detail="Missing required parameters")

    try:
        print(f"📤 Uploading manual vectors: {year} {quarter} {parser} {strategy}")
        markdown = load_markdown(year, quarter, parser)
        if not markdown:
            raise HTTPException(status_code=404, detail="Markdown not found in S3")
        result = create_manual_vector_index(markdown, year, quarter, parser, strategy)
        return {"status": "success", "chunks_uploaded": len(result)}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query_manual")
def query_manual(payload: dict):
    from embedding.manual import search_manual_vectors

    query = payload.get("query")
    year = payload.get("year")
    quarter = payload.get("quarter")
    parser = payload.get("parser")
    strategy = payload.get("strategy")

    if not all([query, year, quarter, parser, strategy]):
        raise HTTPException(status_code=400, detail="Missing query parameters")

    try:
        print(f"🔎 Manual RAG query: {query}")
        chunks = search_manual_vectors(query, parser, strategy, year, quarter, top_k=30)

        context = "\n\n".join(chunks)
        if len(context) > 15000:
            context = context[:15000]

        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial analyst using internal document chunks."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{query}"}
            ]
        )
        answer = completion.choices[0].message.content
        return {"answer": answer, "sources": chunks}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate_summary_manual")
def generate_summary_manual(payload: dict):

    year = payload.get("year")
    quarter = payload.get("quarter")
    parser = payload.get("parser")
    strategy = payload.get("strategy")

    if not all([year, quarter, parser, strategy]):
        raise HTTPException(status_code=400, detail="Missing parameters")

    try:
        print(f"📄 Generating summary using manual RAG")
        chunks = search_manual_vectors("summary", parser, strategy, year, quarter, top_k=30)
        context = "\n\n".join(chunks)
        if len(context) > 15000:
            context = context[:15000]

        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial analyst. Generate an executive summary from this content."},
                {"role": "user", "content": context}
            ]
        )
        summary = completion.choices[0].message.content
        return {"summary": summary, "source_chunks": chunks}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
AIRFLOW_DAG_ID = os.getenv("AIRFLOW_DAG_ID_Raw", "dag_rag_pipeline_triggered")
AIRFLOW_BASE_URL = "http://airflow-webserver:8080/api/v1"
AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "airflow")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "airflow")

@app.get("/check_dag_status/{dag_run_id}")
async def check_dag_status(dag_run_id: str):
    """
    Poll the DAG run status from Airflow until it finishes or times out.
    """
    if not dag_run_id:
        raise HTTPException(status_code=400, detail="dag_run_id is required.")

    url = f"{AIRFLOW_BASE_URL}/dags/{AIRFLOW_DAG_ID}/dagRuns/{dag_run_id}"

    max_retries = 50  # Retry for 1 minute (12 * 5s)
    retries = 0

    while retries < max_retries:
        try:
            response = requests.get(url, auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error contacting Airflow: {str(e)}")

        if response.status_code == 200:
            state = response.json().get("state")
            if state in ["success", "failed"]:
                return {"status": state}
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch DAG status")

        retries += 1
        await asyncio.sleep(5)

    raise HTTPException(status_code=408, detail="DAG is still running after timeout.")