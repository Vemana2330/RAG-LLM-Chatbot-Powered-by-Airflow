import sqlite3
import pandas as pd

# === Step 1: Connect to the ChromaDB SQLite ===
db_path = "chroma.sqlite3"  # If you're in chromadb_store/
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# === Step 2: Fetch Chunk Text from FTS Table ===
cursor.execute("SELECT rowid, c0 FROM embedding_fulltext_search_content")
chunks = cursor.fetchall()
chunk_df = pd.DataFrame(chunks, columns=["embedding_id", "chunk_text"])

# === Step 3: Fetch Metadata (fixing column to string_value) ===
cursor.execute("SELECT id AS embedding_id, key, string_value FROM embedding_metadata")
metadata = cursor.fetchall()
meta_df = pd.DataFrame(metadata, columns=["embedding_id", "key", "value"])

# === Step 4: Pivot metadata from rows → columns ===
pivoted_meta = meta_df.pivot(index="embedding_id", columns="key", values="value").reset_index()

# === Step 5: Merge chunks with metadata ===
final_df = pd.merge(chunk_df, pivoted_meta, on="embedding_id", how="left")

# === Step 6: Save to Excel ===
output_path = "chromadb_chunks_export.xlsx"
final_df.to_excel(output_path, index=False)

print(f"✅ Export complete. Saved to: {output_path}")

# === Step 7: Close connection ===
conn.close()
