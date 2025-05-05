import streamlit as st
import requests
from datetime import datetime
import time

FASTAPI_URL = "http://fastapi_service:8000"
AIRFLOW_URL = "http://airflow-webserver:8080/api/v1/dags/dag_rag_pipeline_triggered/dagRuns"

st.set_page_config(page_title="NVIDIA RAG", layout="centered")
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["🏠 Landing Page", "📄 Chat with LLM"])

if page == "🏠 Landing Page":
    st.title("AI-Powered NVIDIA Report Extraction")
    st.write("""
        Welcome! This app extracts financial reports from NVIDIA's investor portal,
        converts them to Markdown, chunks the content, embeds it into a vector DB, 
        and allows you to query it using an LLM or generate summaries.
    """)

elif page == "📄 Chat with LLM":
    st.title("📄 NVIDIA Financial Reports")

    if "dag_complete" not in st.session_state:
        st.session_state.dag_complete = False

    # Step 1: Selection Form
    with st.form("pipeline_form"):
        response = requests.get(f"{FASTAPI_URL}/get_available_years")
        years = response.json().get("years", []) if response.status_code == 200 else []
        selected_year = st.selectbox("Select Year", years)

        quarters = []
        if selected_year:
            response = requests.get(f"{FASTAPI_URL}/get_available_quarters/{selected_year}")
            quarters = response.json().get("quarters", []) if response.status_code == 200 else []

        selected_quarter = st.selectbox("Select Quarter", quarters)
        parser_choice = st.selectbox("Select Parser", ["Docling", "Mistral"])
        strategy = st.selectbox("Select Chunking Strategy", ["heading", "semantic", "recursive"])
        vector_store = st.selectbox("Select Vector Store", ["Pinecone", "ChromaDB", "Manual"])

        submitted = st.form_submit_button("🚀 Run Full RAG Pipeline")

    # Step 2: Trigger DAG
    if submitted:
        dag_run_id = f"run_{selected_year}_{selected_quarter}_{int(datetime.now().timestamp())}"
        payload = {
            "dag_run_id": dag_run_id,
            "conf": {
                "year": selected_year,
                "quarter": selected_quarter,
                "parser": parser_choice.lower(),
                "strategy": strategy,
                "vector_store": vector_store.lower()
            }
        }

        st.session_state.year = selected_year
        st.session_state.quarter = selected_quarter
        st.session_state.parser = parser_choice
        st.session_state.strategy = strategy
        st.session_state.vector_store = vector_store
        st.session_state.dag_run_id = dag_run_id

        response = requests.post(AIRFLOW_URL, auth=("airflow", "airflow"), json=payload)

        if response.status_code == 200:
            st.success("✅ DAG triggered! Waiting for completion...")

            # Poll FastAPI to check DAG status
            with st.spinner("⏳ Waiting for DAG to complete..."):
                status_url = f"{FASTAPI_URL}/check_dag_status/{dag_run_id}"
                max_retries = 12
                for i in range(max_retries):
                    status_response = requests.get(status_url)
                    if status_response.status_code == 200:
                        dag_status = status_response.json().get("status")
                        if dag_status == "success":
                            st.session_state.dag_complete = True
                            st.success("🎉 DAG completed successfully!")
                            break
                        elif dag_status == "failed":
                            st.error("❌ DAG run failed. Please check Airflow logs.")
                            break
                    time.sleep(5)
                else:
                    st.warning("⏳ DAG is still running. Try again later.")
        else:
            st.error(f"❌ Failed to trigger DAG: {response.text}")

    # Step 3: LLM Interaction UI (shown only after DAG completes)
    if st.session_state.get("dag_complete", False):
        st.markdown("### 💬 Interact with the Document")
        query = st.text_input("Ask a question about the document:")

        if query and st.button("🔍 Ask LLM"):
            route_map = {
                "Pinecone": "/query_pinecone",
                "ChromaDB": "/query_chromadb",
                "Manual": "/query_manual"
            }
            response = requests.post(
                f"{FASTAPI_URL}{route_map[st.session_state.vector_store]}",
                json={
                    "query": query,
                    "year": st.session_state.year,
                    "quarter": st.session_state.quarter,
                    "parser": st.session_state.parser.lower(),
                    "strategy": st.session_state.strategy
                }
            )
            if response.status_code == 200:
                res = response.json()
                st.success("💬 LLM Response:")
                st.markdown(res["answer"])
                with st.expander("📎 Context Used"):
                    for i, chunk in enumerate(res["sources"], 1):
                        st.markdown(f"**Chunk {i}:**\n\n```markdown\n{chunk}\n```")
            else:
                st.error("❌ Failed to get LLM response.")

        if st.button("🧾 Generate Summary"):
            route_map = {
                "Pinecone": "/generate_summary_pinecone",
                "ChromaDB": "/generate_summary_chromadb",
                "Manual": "/generate_summary_manual"
            }
            response = requests.post(
                f"{FASTAPI_URL}{route_map[st.session_state.vector_store]}",
                json={
                    "year": st.session_state.year,
                    "quarter": st.session_state.quarter,
                    "parser": st.session_state.parser.lower(),
                    "strategy": st.session_state.strategy
                }
            )
            if response.status_code == 200:
                summary = response.json().get("summary", "")
                st.success("📘 Summary:")
                st.markdown(summary)
            else:
                st.error("❌ Failed to generate summary.")