from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import requests

FASTAPI_URL = "http://fastapi_service:8000"

default_args = {
    "owner": "airflow",
    "start_date": datetime(2024, 1, 1),
    "retries": 1
}

def process_pdf(**kwargs):
    config = kwargs["dag_run"].conf
    year = config["year"]
    quarter = config["quarter"]
    parser = config["parser"]

    endpoint = f"/process_pdf_{parser}/{year}/{quarter}"
    response = requests.post(f"{FASTAPI_URL}{endpoint}")
    response.raise_for_status()

def chunk_markdown(**kwargs):
    config = kwargs["dag_run"].conf
    payload = {
        "year": config["year"],
        "quarter": config["quarter"],
        "parser": config["parser"],
        "strategy": config["strategy"]
    }

    response = requests.post(f"{FASTAPI_URL}/chunk_markdown", json=payload)
    response.raise_for_status()

def upload_to_vector_db(**kwargs):
    config = kwargs["dag_run"].conf
    store = config["vector_store"].lower()
    
    endpoint_map = {
        "pinecone": "/upload_to_pinecone",
        "chromadb": "/upload_to_chromadb",
        "manual": "/upload_to_manual"
    }

    payload = {
        "year": config["year"],
        "quarter": config["quarter"],
        "parser": config["parser"],
        "strategy": config["strategy"]
    }

    response = requests.post(f"{FASTAPI_URL}{endpoint_map[store]}", json=payload)
    response.raise_for_status()

with DAG(
    "dag_rag_pipeline_triggered",
    default_args=default_args,
    schedule_interval=None,
    catchup=False
) as dag:

    task_process_pdf = PythonOperator(
        task_id="process_pdf",
        python_callable=process_pdf,
        provide_context=True
    )

    task_chunk_md = PythonOperator(
        task_id="chunk_markdown",
        python_callable=chunk_markdown,
        provide_context=True
    )

    task_vector_upload = PythonOperator(
        task_id="upload_to_vector_db",
        python_callable=upload_to_vector_db,
        provide_context=True
    )

    task_process_pdf >> task_chunk_md >> task_vector_upload
