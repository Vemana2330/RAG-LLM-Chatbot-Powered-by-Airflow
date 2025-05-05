# RAG-LLM-Chatbot-Powered-by-Airflow

## Live Application Links
[![codelab](https://img.shields.io/badge/codelabs-4285F4?style=for-the-badge&logo=codelabs&logoColor=white)](https://codelabs-preview.appspot.com/?file_id=1BpU-AyUBABAziM_lYuxOj-JaInIaaq86dNB_8TkBjqg#0)
* Streamlit(not live): http://198.211.105.31:8501
* Fastapi(not live): http://198.211.105.31:8000/docs
* Airflow(not live): http://198.211.105.31:8082

## Technologies Used
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io/)
[![FastAPI](https://img.shields.io/badge/fastapi-109989?style=for-the-badge&logo=FASTAPI&logoColor=white)](https://fastapi.tiangolo.com/)
[![Amazon AWS](https://img.shields.io/badge/Amazon_AWS-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com/)
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/)
[![Python](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)](https://www.python.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)
[![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Chromadb](https://img.shields.io/badge/Chromadb-000000?style=for-the-badge&logo=chromadb&logoColor=white)](https://www.chromadb.com/)
[![Pinecone](https://img.shields.io/badge/Pinecone-6A4CBB?style=for-the-badge&logo=pinecone&logoColor=white)](https://www.pinecone.io/)
[![Docling](https://img.shields.io/badge/Docling-0E4C8B?style=for-the-badge&logo=docling&logoColor=white)](https://www.docling.com/)
[![MistralAI](https://img.shields.io/badge/MistralAI-4C75A3?style=for-the-badge&logo=mistralai&logoColor=white)](https://www.mistral.ai/)
[![Selenium](https://img.shields.io/badge/Selenium-43B02A?style=for-the-badge&logo=selenium&logoColor=white)](https://www.selenium.dev/)
[![Pickle](https://img.shields.io/badge/Pickle-0A71A4?style=for-the-badge&logo=python&logoColor=white)](https://pypi.org/project/pickle/)
[![DigitalOcean](https://img.shields.io/badge/DigitalOcean-0080FF?style=for-the-badge&logo=digitalocean&logoColor=white)](https://www.digitalocean.com/)

## Overview

This project scales and automates a document analysis pipeline by integrating Apache Airflow with Large Language Models (LLMs) for real-time question answering on quarterly reports. It includes a Streamlit frontend, FastAPI backend, and supports multi-parser OCR, chunking, and retrieval strategies. The system is fully containerized using Docker and deployed on DigitalOcean for production-level performance.

## Problem Statement

Manual extraction of insights from complex quarterly reports is inefficient and lacks scalability. There is a need for a flexible, automated system that can parse, chunk, retrieve, and answer questions from such documents using LLMs.

## Project Goals

* Automate document parsing with support for multiple OCR parsers (Docling, Mistral)
* Implement Retrieval-Augmented Generation (RAG) with real-time Q&A over quarterly reports
* Support multiple chunking strategies and retrieval options (manual, Pinecone, ChromaDB)
* Orchestrate the end-to-end pipeline with Apache Airflow for modular, scalable workflows
* Containerize components with Docker and deploy to DigitalOcean for production-readiness
* Deliver a user-friendly interface via Streamlit and a robust API with FastAPI

## Architecture Diagram

![Assignment4_Part2](https://github.com/user-attachments/assets/3e0b0cd9-f473-4609-8e1d-ab0f4cfdad52)

## Directory Structure

```
Big\_Data\_Assignment4\_Part2-main/  
├── .gitignore  
├── README.md  
├── docker-compose.yaml  
├── requirements.txt  
├── selenium\_scrape.py  
│  
├── airflow/  
│   ├── Dockerfile  
│   ├── docker-compose.yaml  
│   ├── requirements.txt  
│   └── dags/  
│       └── dag\_main\_rag\_pipeline.py  
│  
├── backend/  
│   ├── Dockerfile  
│   ├── main.py  
│   ├── requirements.txt  
│   └── chromadb\_store/  
│       ├── chroma.sqlite3  
│       ├── chromadb\_chunks\_export.xlsx  
│       ├── test.py  
│       └── \[UUID folders with ChromaDB binary files\]  
│  
├── chunking/  
│   ├── Q1 (1).md  
│   ├── \_\_init\_\_.py  
│   └── chunks.py  
│  
├── docling\_service/  
│   ├── Dockerfile  
│   ├── docling\_extract.py  
│   ├── main.py  
│   └── requirements.txt  
│  
├── embedding/  
│   ├── chromadb.py  
│   ├── manual.py  
│   └── pinecone.py  
│  
├── frontend/  
│   ├── Dockerfile  
│   ├── app.py  
│   ├── requirements.txt  
│   └── .streamlit/  
│       └── config.toml  
│  
├── pdf\_processing/  
│   ├── \_\_init\_\_.py  
│   ├── mistral.py  
│   ├── test\_docling.py  
│   └── test\_mistral.py
```

## Application UI
![rag](https://github.com/user-attachments/assets/3290139a-770a-4e4a-9a91-1599a479fa1c)


## Application Workflow

1. **User Uploads Selects Year and Quarter**: The frontend allows the user to select year and quarter
2. **Select PDF Parser**: The user chooses between PyMuPDF, Docling, or Mistral OCR depending on the quality and type of the PDF.
3. **Parse the Document**: The selected parser extracts text from the PDF and converts it into markdown format.

4. **Choose Chunking Strategy**: The markdown text is split into chunks using one of the three strategies:  
     * Heading 
     * Semantic
     * Recursive

5. **Generate Embeddings**: Each chunk is embedded using OpenAI’s embedding model
6. **Select RAG Method**: The user picks a retrieval strategy:  
     * Manual cosine similarity (no DB)  
     * Pinecone  
     * ChromaDB
7. **Ask a Question / Request a Summary**: The user submits a query through the Streamlit UI.
8. **Retrieve Relevant Chunks**: Based on the selected retrieval method, the backend fetches the top relevant chunks.

## Prerequisites

- **Python**: Ensure Python is installed on your system. Python 3.8+ is recommended.
- **Docker**: Ensure Docker-desktop is installed on your system and running.
- Docker Resources: Allocate sufficient Docker resources (at least 4 CPUs and 8 GB RAM recommended) for smooth operation of Airflow and multiple containers.
- API Keys: Add your OpenAI / Pinecone / MistralAI keys to .env
- Streamlit Knowledge: Familiarity with Streamlit will help in understanding the chatbot interface and customizing the frontend.
- FastAPI Knowledge: Understanding FastAPI will assist in extending or debugging the backend API endpoints.
- Apache Airflow: Basic knowledge of DAGs, tasks, and scheduling in Airflow is necessary to monitor and manage the document pipeline.
- Vector Database Concepts: Understanding vector similarity, cosine distance, and embedding-based retrieval will help in choosing and optimizing between ChromaDB, Pinecone, and manual strategies.
- OCR and Parsing Tools: Familiarity with document parsing tools like Docling, and Mistral will assist in selecting the best parser based on PDF quality.
- Git: Required for cloning the repository and version control.
- Open Ports:
  - 8501 for Streamlit UI
  - 8000 for FastAPI backend
  - 8082 for Airflow webserver
 
## How to run this Application locally

1. Clone the Repository
```
git clone https://github.com/your-username/RAG-LLM-Chatbot-Powered-by-Airflow.git
cd RAG-LLM-Chatbot-Powered-by-Airflow
```

2. Set Up Environment Configuration:
```
AWS_BUCKET_NAME=your_bucket
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=your_region
AIRFLOW_USERNAME=your_airflow_username
AIRFLOW_PASSWORD=your_airflow_password
AIRFLOW_URL=http://localhost:8082/api/v1
PINECONE_API_KEY=your_key
PINECONE_INDEX=your_index
OPENAI_API_KEY=your_openai_key
MISTRAL_API_KEY=ypur_mistral_key
```

3. Create and Activate a Virtual Environment
```
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows
```

4. Install Required Packages Locally
```
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
pip install -r airflow/requirements.txt
pip install -r docling_service/requirements.txt
```

5. Build and Start All Services: Make sure Docker is running, then execute:
```
docker-compose up --build
```
This starts:
  - Streamlit Frontend → http://localhost:8501
  - FastAPI Backend → http://localhost:8000/docs
  - Airflow Webserver → http://localhost:8082

6. Use the Application
  - Access the Streamlit UI.
  - Choose a quarterly report, OCR parser, and chunking strategy.
  - Select a retrieval method (manual, Pinecone, or ChromaDB).
  - Trigger the DAG
  - Ask questions or request summaries in natural language.

## REFERENCES
- http://airflow.apache.org/docs/
- https://docs.streamlit.io/
- https://fastapi.tiangolo.com/
- https://fastapi.tiangolo.com/tutorial/body/
- https://platform.openai.com/docs/guides/embeddings
- https://docs.pinecone.io/
- https://docs.trychroma.com/
- https://github.com/docling/docling
- https://mistral.ai/news/mistral-ocr
- https://docs.aws.amazon.com/s3/
- https://docs.docker.com/
